import { randomUUID } from "node:crypto";
import {
  expect,
  type APIRequestContext,
  type Page,
} from "../../frontend/node_modules/@playwright/test";
const origin = process.env.E2E_BASE_URL ?? "http://localhost:8080";
export async function apiLogin(
  api: APIRequestContext,
  email: string,
  password: string,
) {
  const csrf = await (await api.get("/api/v1/auth/csrf")).json();
  const response = await api.post("/api/v1/auth/login", {
    headers: { Origin: origin, "X-CSRF-Token": csrf.csrf_token },
    data: { email, password },
  });
  expect(response.status()).toBe(200);
  return {
    Authorization: `Bearer ${(await response.json()).access_token}`,
    Origin: origin,
  };
}
export async function apiReader(api: APIRequestContext) {
  const email = `circulation-${randomUUID()}@example.com`,
    password = `Reader ${randomUUID()}!`;
  const csrf = await (await api.get("/api/v1/auth/csrf")).json();
  const response = await api.post("/api/v1/auth/register", {
    headers: { Origin: origin, "X-CSRF-Token": csrf.csrf_token },
    data: { first_name: "Оқырман", last_name: "Тексеру", email, password },
  });
  expect(response.status()).toBe(201);
  return {
    email,
    password,
    user: await response.json(),
    headers: await apiLogin(api, email, password),
  };
}
export async function pageLogin(
  page: Page,
  email: string,
  password: string,
  destination: RegExp,
) {
  await page.goto("/login");
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  const response = page.waitForResponse(
    (result) =>
      result.url().endsWith("/api/v1/auth/login") &&
      result.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await response;
  // Redact before any failing assertion can capture an input-value snapshot.
  await page.locator('input[type="password"]').evaluateAll((fields) => {
    for (const field of fields) (field as HTMLInputElement).value = "";
  });
  try {
    await expect(page).toHaveURL(destination, { timeout: 15000 });
  } finally {
    // Playwright error-context snapshots include input values, even passwords.
    const field = page.getByLabel("Құпиясөз *", { exact: true });
    if (await field.count()) await field.fill("");
  }
}
