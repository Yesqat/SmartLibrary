import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";

// Auth traces can contain cookies/password-bearing network bodies. Do not record them.
test.use({ trace: "off", video: "off", screenshot: "off" });

test("protected pages redirect an anonymous visitor", async ({ page }) => {
  for (const path of [
    "/dashboard",
    "/admin",
    "/librarian",
    "/account/security",
  ]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/login\?next=/);
    await expect(
      page.getByRole("heading", { name: "Қайта қош келдіңіз" }),
    ).toBeVisible();
  }
});

test("reader registration, login, refresh, ownership UI, password change and logout", async ({
  page,
  context,
}) => {
  const email = `phase3-e2e-${randomUUID()}@example.com`;
  const password = `Reader ${randomUUID()}!`;
  const replacement = `Changed ${randomUUID()}!`;
  await page.goto("/register");
  await page.getByLabel("Аты *", { exact: true }).fill("E2E Оқырман");
  await page.getByLabel("Тегі *", { exact: true }).fill("Тексеру");
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page
    .getByLabel("Құпиясөзді қайталаңыз *", { exact: true })
    .fill(password);
  const registered = page.waitForResponse(
    (response) =>
      response.url().endsWith("/auth/register") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Тіркелу", exact: true }).click();
  const registration = await registered;
  expect(registration.status()).toBe(201);
  expect((await registration.json()).role).toBe("READER");
  await expect(page.getByRole("status")).toContainText("Тіркелу сәтті");
  await page.getByRole("link", { name: "Кіру", exact: true }).click();
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText(
    "Email немесе құпиясөз қате",
  );
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "E2E Оқырман",
  );
  const cookie = (await context.cookies()).find(
    (entry) => entry.name === "sl_refresh",
  );
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Strict");
  expect(cookie?.path).toBe("/api/v1/auth");
  expect(
    await page.evaluate(() => document.cookie.includes("sl_refresh")),
  ).toBe(false);
  expect(
    await page.evaluate(() =>
      [localStorage, sessionStorage].every(
        (storage) =>
          !JSON.stringify(storage).match(
            /access_token|refresh_token|password_hash/,
          ),
      ),
    ),
  ).toBe(true);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "E2E Оқырман",
  );
  const second = await context.newPage();
  await Promise.all([page.reload(), second.goto("/dashboard")]);
  await expect(second.getByRole("heading", { level: 1 })).toContainText(
    "E2E Оқырман",
  );
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "E2E Оқырман",
  );
  await page.goto("/admin");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "рұқсатыңыз жоқ",
  );
  await page.goto("/librarian");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "рұқсатыңыз жоқ",
  );
  await page.goto("/account/security");
  await expect(
    page.getByRole("heading", { name: "Осы сеанс", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Қазіргі құпиясөз *", { exact: true }).fill(password);
  await page.getByLabel("Жаңа құпиясөз *", { exact: true }).fill(replacement);
  await page
    .getByLabel("Құпиясөзді қайталаңыз *", { exact: true })
    .fill(replacement);
  await page
    .getByRole("button", { name: "Құпиясөзді өзгерту", exact: true })
    .click();
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText("Құпиясөз өзгерді. Жаңа құпиясөзбен кіріңіз."),
  ).toBeVisible();
  await expect(second).toHaveURL(/\/login/);
  await page.getByLabel("Email *", { exact: true }).fill(email);
  await page.getByLabel("Құпиясөз *", { exact: true }).fill(replacement);
  await page.getByRole("button", { name: "Кіру", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole("button", { name: "Шығу", exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
  await second.close();
});

for (const role of ["admin", "librarian"]) {
  test(`${role} uses its own protected layout and cannot enter the other role's area`, async ({
    page,
  }) => {
    const password = process.env.E2E_SEED_PASSWORD;
    if (!password)
      throw new Error(
        "Set E2E_SEED_PASSWORD privately from the development DEV_SEED_PASSWORD",
      );
    await page.goto("/login");
    await page
      .getByLabel("Email *", { exact: true })
      .fill(`${role}@smartlibrary.example`);
    await page.getByLabel("Құпиясөз *", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Кіру", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/${role}$`));
    await expect(
      page.getByRole("heading", { name: "Тіркелгі", exact: true }),
    ).toBeVisible();
    await page.goto(role === "admin" ? "/librarian" : "/admin");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "рұқсатыңыз жоқ",
    );
    await page.goto(`/${role}`);
    await page.getByRole("button", { name: "Шығу", exact: true }).click();
    await expect(page).toHaveURL(/\/login/);
  });
}
