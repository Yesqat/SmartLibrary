import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { randomUUID } from "node:crypto";
import { apiLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("Kazakh fuzzy search, filters, sort and persistent URL", async ({
  page,
  request,
}) => {
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  // Circulation tests may legitimately borrow every seeded copy. Own this fixture.
  const categoryResponse = await request.post("/api/v1/categories", {
    headers: staff,
    data: { name: `E2E lexical ${randomUUID()}` },
  });
  expect(categoryResponse.status()).toBe(201);
  const category = await categoryResponse.json();
  const bookResponse = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: "Абай жолы", language: "kk", category_ids: [category.id] },
  });
  expect(bookResponse.status()).toBe(201);
  const book = await bookResponse.json();
  try {
    expect(
      (
        await request.post(`/api/v1/books/${book.id}/copies`, {
          headers: staff,
          data: { inventory_number: `E2E-${randomUUID()}` },
        })
      ).status(),
    ).toBe(201);
    await page.goto(
      "/catalog?category=" +
        category.id +
        "&q=" +
        encodeURIComponent("Абай жоли"),
    );
    await expect(
      page.locator("article").filter({ hasText: "Абай жолы" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Сүзгілерді ашу", exact: true })
      .click();
    await page
      .getByRole("combobox", { name: "Қолжетімділік", exact: true })
      .selectOption("true");
    await page.getByRole("checkbox", { name: "Қазақша", exact: true }).check();
    await page.getByRole("button", { name: "Қолдану", exact: true }).click();
    await expect(page).toHaveURL(/available=true/);
    await expect(
      page.locator("article").filter({ hasText: "Абай жолы" }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Сұрыптау", exact: true })
      .selectOption("year_desc");
    await expect(page).toHaveURL(/sort=year_desc/);
    await page.reload();
    await expect(
      page.getByRole("combobox", { name: "Сұрыптау", exact: true }),
    ).toHaveValue("year_desc");
    await expect(
      page.locator("article").filter({ hasText: "Абай жолы" }),
    ).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  } finally {
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

test("autocomplete loads backend results and empty search is safe", async ({
  page,
}) => {
  await page.goto("/catalog");
  const input = page.getByRole("searchbox", {
    name: "Кітап, автор, ISBN немесе тақырып",
    exact: true,
  });
  await input.fill("Clean");
  const suggestions = page.getByRole("list", { name: "Іздеу ұсыныстары" });
  await expect(
    suggestions.getByRole("link", { name: /Clean Code/ }),
  ).toBeVisible();
  expect(await suggestions.getByRole("link").count()).toBeLessThanOrEqual(8);
  await input.fill("zzzzzz-not-a-real-title-74938");
  await page.getByRole("button", { name: "Іздеу", exact: true }).click();
  await expect(
    page.getByText("Табылған кітаптар: 0", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Жазбалар табылмады.", { exact: true }),
  ).toBeVisible();
});
