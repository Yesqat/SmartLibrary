import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("QR verification preserves RESERVED until the Librarian explicitly confirms Issue", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD is required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const created = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `QR беру тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(created.status()).toBe(201);
  const book = await created.json();
  const copyResponse = await request.post(`/api/v1/books/${book.id}/copies`, {
    headers: staff,
    data: { inventory_number: `ISSUE-${randomUUID()}` },
  });
  expect(copyResponse.status()).toBe(201);
  const copy = await copyResponse.json();
  const reader = await apiReader(request);
  const reserved = await request.post("/api/v1/reservations", {
    headers: reader.headers,
    data: { book_id: book.id },
  });
  expect(reserved.status()).toBe(201);
  const reservation = await reserved.json();
  const credential = await (
    await request.get(`/api/v1/reservations/${reservation.id}/qr`, {
      headers: reader.headers,
    })
  ).json();
  await pageLogin(
    page,
    "librarian@smartlibrary.example",
    password,
    /\/librarian$/,
  );
  await page
    .getByRole("link", { name: "Броньді тексеру", exact: true })
    .click();
  await expect(page).toHaveURL(/\/librarian\/qr$/);
  let issueRequests = 0;
  page.on("request", (call) => {
    if (
      call.method() === "POST" &&
      call.url().endsWith(`/reservations/${reservation.id}/issue`)
    )
      issueRequests++;
  });
  await page.getByRole("textbox", { name: "QR мәтіні" }).fill(credential.token);
  await page
    .getByRole("button", { name: "Броньді тексеру", exact: true })
    .click();
  await expect(
    page.getByText("Бронь тексерілді. Кітап әлі берілген жоқ."),
  ).toBeVisible();
  expect(issueRequests).toBe(0);
  expect(
    (
      await (
        await request.get(`/api/v1/reservations/${reservation.id}`, {
          headers: reader.headers,
        })
      ).json()
    ).status,
  ).toBe("READY");
  const copies = await (
    await request.get(`/api/v1/books/${book.id}/copies`, { headers: staff })
  ).json();
  expect(
    copies.items.find((value: { id: string }) => value.id === copy.id).status,
  ).toBe("RESERVED");
  page.once("dialog", (dialog) => dialog.accept());
  const issued = page.waitForResponse(
    (value) =>
      value.request().method() === "POST" &&
      value.url().endsWith(`/reservations/${reservation.id}/issue`),
  );
  await page.getByRole("button", { name: "Кітапты беру", exact: true }).click();
  const response = await issued;
  expect(response.status()).toBe(200);
  expect((await response.json()).status).toBe("BORROWED");
  await expect(page.getByText("Кітап сәтті берілді.")).toBeVisible();
  expect(issueRequests).toBe(1);
  expect(
    await page
      .getByRole("button", { name: "Кітапты беру", exact: true })
      .count(),
  ).toBe(0);
  expect(
    (
      await (
        await request.get(`/api/v1/reservations/${reservation.id}`, {
          headers: reader.headers,
        })
      ).json()
    ).status,
  ).toBe("COMPLETED");
  expect(
    (
      await request.get(`/api/v1/reservations/${reservation.id}/qr`, {
        headers: reader.headers,
      })
    ).status(),
  ).toBe(409);
  const after = await (
    await request.get(`/api/v1/books/${book.id}/copies`, { headers: staff })
  ).json();
  expect(
    after.items.find((value: { id: string }) => value.id === copy.id).status,
  ).toBe("BORROWED");
  await page.goto("/librarian");
  await page.getByRole("button", { name: "Шығу", exact: true }).click();
  await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
  await page.goto("/my-books");
  await expect(
    page.getByRole("link", { name: book.title, exact: true }),
  ).toBeVisible();
  expect(await page.getByRole("button", { name: /қайтару/i }).count()).toBe(0);
});
