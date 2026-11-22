import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";

test.use({ trace: "off", video: "off", screenshot: "off" });

test("public catalog and physical book details", async ({ page }) => {
  await page.goto("/catalog");
  await expect(
    page.getByRole("heading", { name: "Кітаптар каталогы", exact: true }),
  ).toBeVisible();
  const card = page.locator("article").first();
  await expect(card).toBeVisible();
  const title = await card.getByRole("heading").innerText();
  await card.getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(
    page.getByText("Кітапты кітапханадан алуға болады."),
  ).toBeVisible();
  expect(await page.getByRole("button", { name: /қайтару/i }).count()).toBe(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("librarian creates a title, manages a copy and archives safely", async ({
  page,
}) => {
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD is required");
  const title = "Каталог тексеруі " + randomUUID();
  const inventory = "E2E-" + randomUUID();
  await page.goto("/login");
  await page
    .getByLabel("Email *", { exact: true })
    .fill("librarian@smartlibrary.example");
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page).toHaveURL(/\/librarian$/);
  await page
    .getByRole("link", { name: "Каталогты басқару", exact: true })
    .click();
  await page.getByRole("link", { name: "Кітап қосу", exact: true }).click();
  await page.getByLabel("Кітап атауы *", { exact: true }).fill(title);
  await page
    .getByLabel("Сипаттама", { exact: true })
    .fill("Физикалық кітапты каталогта тексеру.");
  await page.getByRole("button", { name: "Сақтау", exact: true }).click();
  await expect(page).toHaveURL(/\/librarian\/books\/[a-f0-9-]+$/);
  const editor = page.url();
  await page
    .getByRole("link", { name: "Физикалық даналар", exact: true })
    .click();
  await page.getByRole("button", { name: "Дана қосу", exact: true }).click();
  await page.getByLabel("Түгендеу нөмірі", { exact: true }).fill(inventory);
  await page.getByLabel("Сөре", { exact: true }).fill("E2E-A1");
  await page.getByRole("button", { name: "Сақтау", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: inventory });
  await expect(row).toContainText("Қолжетімді");
  await page.goto(editor.replace("/librarian", ""));
  const stock = page
    .getByText("Кітапты кітапханадан алуға болады.", { exact: true })
    .locator("..");
  await expect(
    stock.getByText("Қолжетімді: 1 / 1", { exact: true }),
  ).toBeVisible();
  await page.goto(editor + "/copies");
  await page
    .getByRole("row")
    .filter({ hasText: inventory })
    .getByRole("button", { name: "Өңдеу", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Жағдайы", exact: true })
    .selectOption("DAMAGED");
  await page
    .getByRole("combobox", { name: "Күйі", exact: true })
    .selectOption("DAMAGED");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Сақтау", exact: true }).click();
  await expect(
    page.getByRole("row").filter({ hasText: inventory }),
  ).toContainText("Зақымдалған");
  await page.goto(editor.replace("/librarian", ""));
  await expect(
    stock.getByText("Қолжетімді: 0 / 1", { exact: true }),
  ).toBeVisible();
  await page.goto(editor);
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Мұрағаттау", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Қалпына келтіру", exact: true }),
  ).toBeVisible();
  await page.goto(editor.replace("/librarian", ""));
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Кітап табылмады.",
  );
});
