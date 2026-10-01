import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("Librarian direct issue and physical return allocate to FIFO waiters", async ({
  page,
  request,
}) => {
  test.setTimeout(90_000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD is required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const created = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `Қайтару тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(created.status()).toBe(201);
  const book = await created.json(),
    number = `RETURN-${randomUUID()}`;
  expect(
    (
      await request.post(`/api/v1/books/${book.id}/copies`, {
        headers: staff,
        data: { inventory_number: number },
      })
    ).status(),
  ).toBe(201);
  const borrower = await apiReader(request),
    first = await apiReader(request),
    second = await apiReader(request);
  await pageLogin(
    page,
    "librarian@smartlibrary.example",
    password,
    /\/librarian$/,
  );
  await page.goto("/librarian/issue");
  await page.getByRole("textbox", { name: "Түгендеу нөмірі" }).fill(number);
  await page.getByRole("button", { name: "Дананы табу" }).click();
  await page
    .getByRole("textbox", { name: "Оқырманның аты немесе email" })
    .fill(borrower.email);
  await page.getByRole("button", { name: "Оқырманды іздеу" }).click();
  await page
    .getByRole("group", { name: "Оқырманды таңдаңыз" })
    .getByRole("button")
    .filter({ hasText: borrower.email })
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  const issued = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      r.url().endsWith("/librarian/borrowings"),
  );
  await page.getByRole("button", { name: "Кітапты беру", exact: true }).click();
  const response = await issued;
  expect(response.status()).toBe(200);
  const loan = await response.json();
  await expect(page.getByText("Кітап сәтті берілді.")).toBeVisible();
  const waiters = [];
  for (const reader of [first, second]) {
    const result = await request.post("/api/v1/reservations", {
      headers: reader.headers,
      data: { book_id: book.id },
    });
    expect(result.status()).toBe(201);
    const reservation = await result.json();
    expect(reservation.status).toBe("WAITING");
    waiters.push({ reader, reservation });
  }
  await page.goto("/librarian/return");
  await page.getByRole("textbox", { name: "Түгендеу нөмірі" }).fill(number);
  await page.getByRole("button", { name: "Дананы табу" }).click();
  await page
    .getByRole("combobox", { name: "Қайтарылған кітаптың жағдайы" })
    .selectOption("GOOD");
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Қайтаруды тіркеу", exact: true })
    .click();
  await expect(page.getByText("Кітаптың қайтарылуы тіркелді.")).toBeVisible();
  const history = await (
    await request.get("/api/v1/borrowings/me/history", {
      headers: borrower.headers,
    })
  ).json();
  expect(
    history.items.find((row: { id: string }) => row.id === loan.id).status,
  ).toBe("RETURNED");
  for (let i = 0; i < waiters.length; i++) {
    const { reader, reservation } = waiters[i];
    const result = await (
      await request.get(`/api/v1/reservations/${reservation.id}`, {
        headers: reader.headers,
      })
    ).json();
    expect(result.status).toBe(i === 0 ? "READY" : "WAITING");
  }
  const lookup = await (
    await request.get(`/api/v1/librarian/borrowings/by-inventory/${number}`, {
      headers: staff,
    })
  ).json();
  expect(lookup.physical_copy.status).toBe("RESERVED");
  expect(lookup.active_borrowing).toBeNull();
  for (const [index, { reader, reservation }] of waiters.entries()) {
    expect(
      (
        await request.post(`/api/v1/reservations/${reservation.id}/cancel`, {
          headers: reader.headers,
        })
      ).status(),
    ).toBe(200);
    if (index === 0) {
      const next = await request.get(
        `/api/v1/reservations/${waiters[1].reservation.id}`,
        {
          headers: waiters[1].reader.headers,
        },
      );
      expect((await next.json()).status).toBe("READY");
    }
  }
  await page.goto("/librarian");
  await page.getByRole("button", { name: "Шығу", exact: true }).click();
  await pageLogin(page, borrower.email, borrower.password, /\/dashboard$/);
  await page.goto("/my-books");
  await expect(
    page.getByText("Әзірге жазбалар жоқ.", { exact: true }),
  ).toBeVisible();
  expect(
    await page.getByRole("link", { name: book.title, exact: true }).count(),
  ).toBe(0);
  await page.goto("/history");
  await expect(
    page.getByRole("link", { name: book.title, exact: true }),
  ).toBeVisible();
  expect(
    (
      await request.patch(`/api/v1/books/${book.id}/archive`, {
        headers: staff,
        data: { archived: true },
      })
    ).status(),
  ).toBe(200);
});
