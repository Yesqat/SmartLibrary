import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";

test.use({ trace: "off", video: "off", screenshot: "off" });

test("production TLS registration, Secure sessions, refresh, nonce hydration and logout", async ({
  page,
  context,
}) => {
  const email = `tls-${randomUUID()}@example.com`;
  const password = `Private ${randomUUID()}!`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await page.goto("/register");
  expect(response?.status()).toBe(200);
  const headers = response!.headers();
  expect(headers["strict-transport-security"]).toContain("max-age=31536000");
  expect(headers["content-security-policy"]).toContain("'nonce-");
  expect(headers["content-security-policy"]).not.toContain("'unsafe-eval'");
  await page.getByLabel("Аты *", { exact: true }).fill("Аян");
  await page.getByLabel("Тегі *", { exact: true }).fill("Тексеру");
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page
    .getByLabel("Құпиясөзді қайталаңыз *", { exact: true })
    .fill(password);
  await page.getByRole("button", { name: "Тіркелу", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Тіркелу сәтті");
  await page.goto("/login");
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const cookies = await context.cookies();
  const refresh = cookies.find(
    (cookie) => cookie.name === "__Secure-sl_refresh",
  );
  expect(refresh).toBeDefined();
  expect(refresh!.secure && refresh!.httpOnly).toBe(true);
  expect(refresh!.sameSite).toBe("Strict");
  expect(refresh!.path).toBe("/api/v1/auth");
  expect(cookies.every((cookie) => cookie.secure)).toBe(true);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Шығу", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Шығу", exact: true }).click();
  await expect(page).toHaveURL((url) => url.pathname === "/login");
  expect(
    (await context.cookies()).filter((cookie) =>
      cookie.name.includes("refresh"),
    ),
  ).toHaveLength(0);
  expect(errors).toEqual([]);
});
