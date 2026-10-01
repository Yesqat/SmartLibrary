import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });

test("real category suggestions require explicit review and persist the chosen labels", async ({
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
  const response = await request.post("/api/v1/books", {
    headers: staff,
    data: {
      title: `Deep Learning with Python ${randomUUID().slice(0, 8)}`,
      language: "en",
      description:
        "Neural networks, machine learning and artificial intelligence. Practical Python programming for training deep learning models.",
    },
  });
  expect(response.status()).toBe(201);
  const book = await response.json();
  try {
    await pageLogin(
      page,
      "librarian@smartlibrary.example",
      password,
      /\/librarian$/,
    );
    await page.goto(`/librarian/books/${book.id}`);
    await page.getByRole("link", { name: "AI санаттау", exact: true }).click();
    await page
      .getByRole("button", { name: "Санаттарды ұсыну", exact: true })
      .click();
    const card = page.getByRole("article").filter({ hasText: book.title });
    await expect(card.getByRole("checkbox").first()).toBeVisible({
      timeout: 60000,
    });
    expect(
      (await (await request.get(`/api/v1/books/${book.id}`)).json()).categories,
    ).toEqual([]);
    const before = await (
      await request.get(`/api/v1/ai/category-predictions?book_id=${book.id}`, {
        headers: staff,
      })
    ).json();
    expect(before.items[0].predictions.length).toBeGreaterThanOrEqual(2);
    page.once("dialog", (dialog) => dialog.accept());
    await card
      .getByRole("button", {
        name: "Тексерілген санаттарды сақтау",
        exact: true,
      })
      .click();
    await expect(
      card.getByText("Қабылданған", { exact: false }).first(),
    ).toBeVisible();
    await expect(card.getByRole("checkbox")).toHaveCount(0);
    const saved = await (await request.get(`/api/v1/books/${book.id}`)).json();
    expect(
      saved.categories.map((row: { id: string }) => row.id).sort(),
    ).toEqual(
      before.items[0].predictions
        .map((row: { category_id: string }) => row.category_id)
        .sort(),
    );
    await page
      .getByRole("combobox", { name: "Санаттау әдісі", exact: true })
      .selectOption("classical");
    await page
      .getByRole("button", { name: "Санаттарды ұсыну", exact: true })
      .click();
    const classical = page
      .getByRole("article")
      .filter({ hasText: "tfidf-ovr-logistic" });
    await expect(classical).toBeVisible({ timeout: 30000 });
    await classical
      .getByRole("button", { name: "Барлығын алып тастау", exact: true })
      .click();
    page.once("dialog", (dialog) => dialog.accept());
    await classical
      .getByRole("button", {
        name: "Тексерілген санаттарды сақтау",
        exact: true,
      })
      .click();
    await expect(
      classical.getByRole("button", { name: "Тексерілген санаттарды сақтау" }),
    ).toHaveCount(0);
    expect(
      (await (await request.get(`/api/v1/books/${book.id}`)).json()).categories,
    ).toEqual([]);
  } finally {
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
