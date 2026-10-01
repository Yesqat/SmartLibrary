import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Admin generates and downloads real PDF and XLSX reports", async ({
  page,
}) => {
  test.setTimeout(90000);
  page.setDefaultTimeout(15000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  await pageLogin(page, "admin@smartlibrary.example", password, /\/admin$/);
  await page.goto("/admin/reports");
  const directory = path.resolve(process.cwd(), "../work/report-verification");
  await mkdir(directory, { recursive: true });
  for (const format of ["pdf", "xlsx"]) {
    await page
      .getByRole("combobox", { name: "Формат", exact: true })
      .selectOption(format);
    await page.getByRole("button", { name: "Есеп жасау", exact: true }).click();
    const link = page.getByRole("link", { name: "Есепті жүктеу", exact: true });
    await expect(link).toBeVisible();
    const downloading = page.waitForEvent("download");
    await link.click();
    const download = await downloading;
    expect(download.suggestedFilename()).toMatch(
      new RegExp(`^smartlibrary_inventory_.*\\.${format}$`),
    );
    const target = path.join(directory, `inventory.${format}`);
    await download.saveAs(target);
    const bytes = await readFile(target);
    expect(bytes.length).toBeGreaterThan(1000);
    expect(bytes.subarray(0, format === "pdf" ? 4 : 2).toString()).toBe(
      format === "pdf" ? "%PDF" : "PK",
    );
  }
});
