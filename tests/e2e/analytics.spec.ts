import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Admin analytics render real API totals, dated empty results and AI usage", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const headers = await apiLogin(
    request,
    "admin@smartlibrary.example",
    password,
  );
  const response = await request.get("/api/v1/admin/analytics/inventory", {
    headers,
  });
  expect(response.status()).toBe(200);
  const inventory = await response.json();
  await pageLogin(page, "admin@smartlibrary.example", password, /\/admin$/);
  await page.goto("/admin/analytics");
  await page.getByRole("button", { name: "Қор", exact: true }).click();
  const metric = page
    .locator("dl > div")
    .filter({ has: page.getByText("Физикалық даналар", { exact: true }) });
  await expect(metric.locator("dd")).toHaveText(
    new Intl.NumberFormat("kk-KZ").format(inventory.physical_copies),
  );
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.getByLabel("Басталу күні").fill("2080-01-01");
  await page.getByLabel("Аяқталу күні").fill("2080-01-03");
  await page.getByRole("button", { name: "Қолдану", exact: true }).click();
  await page.getByRole("button", { name: "Іздеу", exact: true }).click();
  await expect(page.getByText("Есептелмейді", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Таңдалған кезеңде дерек жоқ.").first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "AI және ұсыныстар", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Ұсыныстарды пайдалану" }),
  ).toBeVisible();
  await page.goto("/admin/ai");
  await expect(
    page.getByRole("heading", { name: "AI қызметтеріне шолу", exact: true }),
  ).toBeVisible();
});
