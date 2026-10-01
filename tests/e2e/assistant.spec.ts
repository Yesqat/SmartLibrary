import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Reader conversation persists and an unconfigured external provider leaves the catalog operational", async ({
  page,
  request,
}) => {
  const reader = await apiReader(request);
  await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
  await page.getByRole("link", { name: "AI кітапханашы", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant$/);
  await page.getByRole("button", { name: "Жаңа әңгіме", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Сұрағыңыз" })
    .fill("Кітапты қанша күнге аламын?");
  const response = page.waitForResponse((result) =>
    /\/ai\/conversations\/[^/]+\/messages$/.test(result.url()),
  );
  await page.getByRole("button", { name: "Жіберу", exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(503);
  expect((await result.json()).error.code).toBe("AI_SERVICE_UNAVAILABLE");
  await expect(page.getByRole("alert").first()).toContainText(
    "AI көмекшісі уақытша қолжетімсіз",
  );
  await page.reload();
  await page
    .getByRole("button", { name: "Кітапты қанша күнге аламын?", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Сіз", exact: true }),
  ).toContainText("Кітапты қанша күнге аламын?");
  await page.goto("/catalog");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Кітаптар каталогы",
  );
  await expect(page.getByRole("article").first()).toBeVisible();
});
