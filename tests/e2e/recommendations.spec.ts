import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("Reader recommendations show real copies and rendered cards have attributable clicks", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const categoryResponse = await request.post("/api/v1/categories", {
    headers: staff,
    data: { name: `E2E recommendations ${randomUUID()}` },
  });
  expect(categoryResponse.status()).toBe(201);
  const category = await categoryResponse.json();
  const bookResponse = await request.post("/api/v1/books", {
    headers: staff,
    data: {
      title: `Бағдарламалау ұсынысы ${randomUUID().slice(0, 8)}`,
      language: "kk",
      description: "Python тіліндегі функциялар мен бағдарламалау негіздері.",
      category_ids: [category.id],
    },
  });
  expect(bookResponse.status()).toBe(201);
  const book = await bookResponse.json();
  const reader = await apiReader(request);
  try {
    expect(
      (
        await request.post(`/api/v1/books/${book.id}/copies`, {
          headers: staff,
          data: { inventory_number: `E2E-${randomUUID()}` },
        })
      ).status(),
    ).toBe(201);
    expect(
      (
        await request.patch("/api/v1/users/me/preferences", {
          headers: reader.headers,
          data: { category_ids: [category.id] },
        })
      ).status(),
    ).toBe(200);
    expect(
      (
        await request.post(`/api/v1/favorites/${book.id}`, {
          headers: reader.headers,
        })
      ).status(),
    ).toBe(204);
    await expect
      .poll(
        async () =>
          (await (await request.get(`/api/v1/books/${book.id}/similar`)).json())
            .content_available,
        { timeout: 90000, intervals: [1000, 2000, 5000] },
      )
      .toBe(true);
    await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
    const section = page.getByRole("region", {
      name: "Сізге арналған ұсыныстар",
    });
    const card = section.getByRole("link", { name: book.title, exact: true });
    const shown = page.waitForResponse(
      (response) =>
        response.url().endsWith("/recommendations/impressions") &&
        response.request().postDataJSON()?.book_id === book.id,
    );
    await card.scrollIntoViewIfNeeded();
    expect((await shown).status()).toBe(200);
    await expect(
      section.getByText("Қолжетімді: 1 / 1", { exact: true }).first(),
    ).toBeVisible();
    const clicked = page.waitForResponse((response) =>
      /recommendations\/impressions\/[^/]+\/click$/.test(response.url()),
    );
    await card.click();
    expect((await clicked).status()).toBe(204);
    await expect(
      page.getByRole("heading", { level: 1, name: book.title }),
    ).toBeVisible();
    const similar = page.getByRole("region", { name: "Осы кітапқа ұқсас" });
    await expect(similar.getByRole("article").first()).toBeVisible();
    await expect(
      similar.getByRole("link", { name: book.title, exact: true }),
    ).toHaveCount(0);
    await page.goto("/");
    await expect(
      page
        .getByRole("region", { name: "Танымал кітаптар" })
        .getByRole("article")
        .first(),
    ).toBeVisible();
  } finally {
    expect(
      (
        await request.delete(`/api/v1/favorites/${book.id}`, {
          headers: reader.headers,
        })
      ).status(),
    ).toBe(204);
    expect(
      (
        await request.patch(`/api/v1/books/${book.id}/archive`, {
          headers: staff,
          data: { archived: true },
        })
      ).status(),
    ).toBe(200);
    expect(
      (
        await request.patch(`/api/v1/categories/${category.id}/archive`, {
          headers: staff,
          data: { archived: true },
        })
      ).status(),
    ).toBe(200);
  }
});
