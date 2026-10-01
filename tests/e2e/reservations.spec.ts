import { randomUUID } from "node:crypto";
import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "../../frontend/node_modules/@playwright/test";

test.use({ trace: "off", video: "off", screenshot: "off" });
async function credentials(
  api: APIRequestContext,
  email: string,
  password: string,
) {
  const csrf = await (await api.get("/api/v1/auth/csrf")).json();
  const response = await api.post("/api/v1/auth/login", {
    headers: {
      Origin: process.env.E2E_BASE_URL ?? "http://localhost:8080",
      "X-CSRF-Token": csrf.csrf_token,
    },
    data: { email, password },
  });
  expect(response.status()).toBe(200);
  return {
    Authorization: `Bearer ${(await response.json()).access_token}`,
    Origin: process.env.E2E_BASE_URL ?? "http://localhost:8080",
  };
}
async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}
test("Reader reservation, private QR and FIFO cancellation through real services", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(90_000);
  const seed = process.env.E2E_SEED_PASSWORD;
  if (!seed) throw new Error("E2E_SEED_PASSWORD is required");
  const staff = await credentials(
    request,
    "librarian@smartlibrary.example",
    seed,
  );
  const created = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `Бронь тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(created.status()).toBe(201);
  const book = await created.json();
  expect(
    (
      await request.post(`/api/v1/books/${book.id}/copies`, {
        headers: staff,
        data: { inventory_number: `QR-E2E-${randomUUID()}` },
      })
    ).status(),
  ).toBe(201);
  const accounts = [];
  for (let index = 0; index < 2; index++) {
    const email = `reservation-${randomUUID()}@example.com`,
      password = `Reader ${randomUUID()}!`;
    const csrf = await (await request.get("/api/v1/auth/csrf")).json();
    const registered = await request.post("/api/v1/auth/register", {
      headers: {
        Origin: process.env.E2E_BASE_URL ?? "http://localhost:8080",
        "X-CSRF-Token": csrf.csrf_token,
      },
      data: { first_name: "Бронь", last_name: "Тексеру", email, password },
    });
    expect(registered.status()).toBe(201);
    accounts.push({
      email,
      password,
      headers: await credentials(request, email, password),
    });
  }
  const secondContext = await browser.newContext();
  const second = await secondContext.newPage();
  const createdReservations: { id: string; headers: Record<string, string> }[] =
    [];
  try {
    await login(page, accounts[0].email, accounts[0].password);
    await page.goto("/catalog");
    await page
      .getByRole("searchbox", {
        name: "Кітап, автор, ISBN немесе тақырып",
        exact: true,
      })
      .fill(book.title);
    await page.getByRole("button", { name: "Іздеу", exact: true }).click();
    await page
      .locator("article")
      .getByRole("link", { name: book.title, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/books/${book.id}$`));
    await page
      .getByRole("button", { name: "Кітапты брондау", exact: true })
      .click();
    await expect(page).toHaveURL(/\/reservations\/[a-f0-9-]+$/);
    const firstId = page.url().split("/").pop()!;
    createdReservations.push({ id: firstId, headers: accounts[0].headers });
    await expect(page.getByText("Алуға дайын", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "QR кодты көрсету" }).click();
    await expect(page.getByAltText("Броньдің QR коды")).toBeVisible();
    expect((await request.get(`/api/v1/books/${book.id}`)).status()).toBe(200);
    expect(
      (await (await request.get(`/api/v1/books/${book.id}`)).json())
        .available_copies,
    ).toBe(0);
    await login(second, accounts[1].email, accounts[1].password);
    await second.goto(`/books/${book.id}`);
    await second
      .getByRole("button", { name: "Кезекке тұру", exact: true })
      .click();
    await expect(second).toHaveURL(/\/reservations\/[a-f0-9-]+$/);
    const secondId = second.url().split("/").pop()!;
    createdReservations.push({ id: secondId, headers: accounts[1].headers });
    await expect(second.getByText("Кезекте", { exact: true })).toBeVisible();
    expect(await second.getByAltText("Броньдің QR коды").count()).toBe(0);
    expect(
      (
        await request.get(`/api/v1/reservations/${firstId}/qr`, {
          headers: accounts[1].headers,
        })
      ).status(),
    ).toBe(404);
    page.once("dialog", (dialog) => dialog.accept());
    await page
      .getByRole("button", { name: "Броньнан бас тарту", exact: true })
      .click();
    await expect(
      page.getByText("Бас тартылған", { exact: true }),
    ).toBeVisible();
    expect(await page.getByAltText("Броньдің QR коды").count()).toBe(0);
    await second.reload();
    await expect(
      second.getByText("Алуға дайын", { exact: true }),
    ).toBeVisible();
    await second.getByRole("button", { name: "QR кодты көрсету" }).click();
    await expect(second.getByAltText("Броньдің QR коды")).toBeVisible();
    await second.setViewportSize({ width: 390, height: 844 });
    expect(
      await second.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  } finally {
    for (const row of createdReservations)
      await request.post(`/api/v1/reservations/${row.id}/cancel`, {
        headers: row.headers,
      });
    await request.patch(`/api/v1/books/${book.id}/archive`, {
      headers: staff,
      data: { archived: true },
    });
    await secondContext.close();
  }
});
