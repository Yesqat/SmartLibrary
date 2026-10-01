import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Reader favorites, notifications, profile, owned loans and reservation history", async ({
  page,
  request,
}) => {
  test.setTimeout(100000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const response = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `Оқырман тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(response.status()).toBe(201);
  const book = await response.json();
  expect(
    (
      await request.post(`/api/v1/books/${book.id}/copies`, {
        headers: staff,
        data: { inventory_number: `READER-${randomUUID()}` },
      })
    ).status(),
  ).toBe(201);
  const reader = await apiReader(request);
  let reservationId: string | undefined;
  try {
    await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
    await page.goto(`/books/${book.id}`);
    await page
      .getByRole("button", { name: "Таңдаулыға қосу", exact: true })
      .click();
    await expect(
      page.getByText("Таңдаулыға қосылды", { exact: true }),
    ).toBeVisible();
    await page.goto("/favorites");
    await expect(
      page.getByRole("link", { name: book.title, exact: true }),
    ).toBeVisible();
    const reserved = await request.post("/api/v1/reservations", {
      headers: reader.headers,
      data: { book_id: book.id },
    });
    expect(reserved.status()).toBe(201);
    reservationId = (await reserved.json()).id;
    await page.goto("/notifications");
    await expect(
      page.getByRole("button", { name: "Оқылды деп белгілеу", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: "Барлығын оқылды деп белгілеу",
        exact: true,
      })
      .click();
    await expect(page.getByText("Хабарламалар жаңартылды")).toBeVisible();
    expect(
      (
        await (
          await request.get("/api/v1/notifications?unread=true", {
            headers: reader.headers,
          })
        ).json()
      ).total,
    ).toBe(0);
    await page.goto("/account/profile");
    await page.getByLabel("Аты", { exact: true }).fill("Айдана");
    await page
      .locator("form")
      .filter({ has: page.getByLabel("Аты", { exact: true }) })
      .getByRole("button", { name: "Сақтау", exact: true })
      .click();
    await expect(
      page.getByRole("status").filter({ hasText: "Сақталды" }),
    ).toBeVisible();
    const me = await (
      await request.get("/api/v1/users/me", { headers: reader.headers })
    ).json();
    expect(me.first_name).toBe("Айдана");
    expect(me.role).toBe("READER");
    await page.goto("/my-books");
    await expect(
      page.getByText(
        "Кітапты кітапханаға әкеліңіз. Физикалық қайтаруды кітапханашы тіркейді.",
      ),
    ).toBeVisible();
    expect(
      await page.getByRole("button", { name: /Қайтаруды тіркеу/ }).count(),
    ).toBe(0);
    expect(
      (
        await request.post(`/api/v1/reservations/${reservationId}/cancel`, {
          headers: reader.headers,
        })
      ).status(),
    ).toBe(200);
    await page.goto("/reservations");
    await page.getByRole("button", { name: "Оқу тарихы", exact: true }).click();
    await expect(
      page.getByRole("link", { name: book.title, exact: true }),
    ).toBeVisible();
    await page.goto("/history");
    await expect(
      page.getByRole("heading", { name: "Оқу тарихы", exact: true }),
    ).toBeVisible();
  } finally {
    if (reservationId)
      await request.post(`/api/v1/reservations/${reservationId}/cancel`, {
        headers: reader.headers,
      });
    await request.delete(`/api/v1/favorites/${book.id}`, {
      headers: reader.headers,
    });
    expect(
      (
        await request.patch(`/api/v1/books/${book.id}/archive`, {
          headers: staff,
          data: { archived: true },
        })
      ).status(),
    ).toBe(200);
  }
});
