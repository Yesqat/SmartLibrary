import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("real worker indexes new metadata and semantic/hybrid catalog uses current copies", async ({
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
    data: { name: `E2E semantic ${randomUUID()}` },
  });
  expect(categoryResponse.status()).toBe(201);
  const category = await categoryResponse.json();
  const title = `Ғарышқа саяхат ${randomUUID().slice(0, 8)}`;
  const bookResponse = await request.post("/api/v1/books", {
    headers: staff,
    data: {
      title,
      language: "kk",
      description:
        "Ғарыш, жұлдыздар және қара құрдымдар туралы астрономиялық кітап.",
      category_ids: [category.id],
    },
  });
  expect(bookResponse.status()).toBe(201);
  const book = await bookResponse.json();
  try {
    const copyResponse = await request.post(`/api/v1/books/${book.id}/copies`, {
      headers: staff,
      data: { inventory_number: `E2E-${randomUUID()}` },
    });
    expect(copyResponse.status()).toBe(201);
    const copy = await copyResponse.json();
    const params = new URLSearchParams({
      q: "Аспан мен қара құрдымдар",
      mode: "semantic",
      category: category.id,
      available: "true",
    });
    await expect
      .poll(
        async () => {
          const response = await request.get(`/api/v1/search?${params}`);
          if (response.status() !== 200) return false;
          const data = await response.json();
          return (
            data.items.some((row: { id: string }) => row.id === book.id) &&
            !data.indexing_pending
          );
        },
        { timeout: 90000, intervals: [1000, 2000, 5000] },
      )
      .toBe(true);
    await page.goto(`/catalog?${params}`);
    await expect(
      page.getByRole("link", { name: title, exact: true }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Іздеу түрі", exact: true })
      .selectOption("hybrid");
    await expect(page).toHaveURL(/mode=hybrid/);
    await expect(
      page.getByRole("link", { name: title, exact: true }),
    ).toBeVisible();
    expect(
      (
        await request.patch(`/api/v1/copies/${copy.id}`, {
          headers: staff,
          data: { status: "MAINTENANCE" },
        })
      ).status(),
    ).toBe(200);
    await page.reload();
    await expect(
      page.getByText("Табылған кітаптар: 0", { exact: true }),
    ).toBeVisible();
    expect(
      (
        await request.patch(`/api/v1/books/${book.id}`, {
          headers: staff,
          data: {
            description:
              "Жұлдыздар эволюциясы мен ғарыш телескоптары туралы жаңартылған кітап.",
          },
        })
      ).status(),
    ).toBe(200);
    params.delete("available");
    await expect
      .poll(
        async () => {
          const data = await (
            await request.get(`/api/v1/search?${params}`)
          ).json();
          return data.total === 1 && !data.indexing_pending;
        },
        { timeout: 90000, intervals: [1000, 2000, 5000] },
      )
      .toBe(true);
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
