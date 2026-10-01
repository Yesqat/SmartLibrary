import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Admin manages roles/status, edits settings and reads immutable audit history", async ({
  page,
  request,
}) => {
  test.setTimeout(100000);
  page.setDefaultTimeout(15000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const fixtureEmail = process.env.E2E_ADMIN_READER_EMAIL;
  const reader = fixtureEmail
    ? await (async () => {
        const headers = await apiLogin(request, fixtureEmail, password);
        const response = await request.get("/api/v1/auth/me", { headers });
        expect(response.status()).toBe(200);
        const user = await response.json();
        expect(user.role).toBe("READER");
        expect(user.status).toBe("ACTIVE");
        return { email: fixtureEmail, headers, user };
      })()
    : await apiReader(request);
  const admin = await apiLogin(request, "admin@smartlibrary.example", password);
  const originals = await (
    await request.get("/api/v1/admin/settings", { headers: admin })
  ).json();
  const setting = originals.find(
    (row: { key: string }) => row.key === "max_books_per_user",
  );
  const newLimit = setting.value === 5 ? 6 : 5;
  let changedSettings = false;
  try {
    await pageLogin(page, "admin@smartlibrary.example", password, /\/admin$/);
    await expect(
      page.getByText("Барлық оқырмандар", { exact: true }),
    ).toBeVisible();
    await page.goto("/admin/users");
    await page.getByLabel("Аты, email немесе ID").fill(reader.email);
    await page.getByRole("button", { name: "Іздеу", exact: true }).click();
    await page
      .getByRole("link", { name: "Оқырман Тексеру", exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/admin/users/${reader.user.id}$`));
    await expect(
      page.getByRole("heading", { name: "Пайдаланушы туралы", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Рөл", exact: true })
      .selectOption("LIBRARIAN");
    await expect(
      page.getByRole("combobox", { name: "Рөл", exact: true }),
    ).toHaveValue("LIBRARIAN");
    await expect(
      page.getByRole("button", { name: "Рөлді өзгерту", exact: true }),
    ).toBeEnabled();
    page.once("dialog", (dialog) => dialog.accept());
    await page
      .getByRole("button", { name: "Рөлді өзгерту", exact: true })
      .click();
    await expect(
      page.getByText("Өзгеріс сақталды. Бұрынғы сеанстар аяқталды."),
    ).toBeVisible();
    expect(
      (
        await request.get("/api/v1/auth/me", { headers: reader.headers })
      ).status(),
    ).toBe(401);
    await page
      .getByRole("combobox", { name: "Күйі", exact: true })
      .selectOption("BLOCKED");
    page.once("dialog", (dialog) => dialog.accept());
    const blocked = page.waitForResponse(
      (r) =>
        r.request().method() === "PATCH" &&
        r.url().endsWith(`/users/${reader.user.id}/status`),
    );
    await page
      .getByRole("button", { name: "Күйді өзгерту", exact: true })
      .click();
    expect((await blocked).status()).toBe(200);
    await page.goto("/admin/librarians");
    await page.getByLabel("Аты, email немесе ID").fill(reader.email);
    await page.getByRole("button", { name: "Іздеу", exact: true }).click();
    await expect(page.getByText(reader.email, { exact: true })).toBeVisible();
    await page.goto("/admin/settings");
    await page
      .getByLabel("Оқырманға берілетін кітап лимиті")
      .fill(String(newLimit));
    page.once("dialog", (dialog) => dialog.accept());
    const saved = page.waitForResponse(
      (r) =>
        r.request().method() === "PATCH" && r.url().endsWith("/admin/settings"),
    );
    await page.getByRole("button", { name: "Сақтау", exact: true }).click();
    expect((await saved).status()).toBe(200);
    changedSettings = true;
    await expect(
      page.getByText("Баптаулар сақталды", { exact: true }),
    ).toBeVisible();
    await page.goto("/admin/audit-logs");
    await page.getByLabel("Әрекет коды").fill("ROLE_CHANGED");
    await page.getByRole("button", { name: "Сүзу", exact: true }).click();
    await expect(
      page.getByText("READER->LIBRARIAN", { exact: true }).first(),
    ).toBeVisible();
    expect(await page.getByRole("button", { name: /Өшіру|Жою/ }).count()).toBe(
      0,
    );
    for (const [path, title] of [
      ["/admin/inventory", "Түгендеу"],
      ["/admin/borrowings", "Қарызға берілген кітаптар"],
      ["/admin/reservations", "Броньдар"],
    ]) {
      await page.goto(path);
      await expect(
        page.getByRole("heading", { name: title, exact: true }),
      ).toBeVisible();
    }
  } finally {
    if (changedSettings) {
      const current = await (
        await request.get("/api/v1/admin/settings", { headers: admin })
      ).json();
      const latest = current.find(
        (row: { key: string }) => row.key === setting.key,
      );
      expect(
        (
          await request.patch("/api/v1/admin/settings", {
            headers: admin,
            data: {
              changes: [
                {
                  key: setting.key,
                  value: setting.value,
                  expected_updated_at: latest.updated_at,
                },
              ],
            },
          })
        ).status(),
      ).toBe(200);
    }
    // Restore only this test-created account; audit history is retained.
    expect(
      (
        await request.patch(`/api/v1/admin/users/${reader.user.id}/role`, {
          headers: admin,
          data: { role: "READER" },
        })
      ).status(),
    ).toBe(200);
    expect(
      (
        await request.patch(`/api/v1/admin/users/${reader.user.id}/status`, {
          headers: admin,
          data: { status: "ACTIVE" },
        })
      ).status(),
    ).toBe(200);
  }
});
