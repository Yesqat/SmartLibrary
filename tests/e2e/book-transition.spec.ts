import { randomUUID } from "node:crypto";
import { expect, test } from "../../frontend/node_modules/@playwright/test";
import { apiLogin } from "./library-helpers";

test.use({ trace: "off", video: "off", screenshot: "off" });

const title = `Мұқаба ${randomUUID()}`;
const catalogUrl = `/catalog?q=${encodeURIComponent(title)}&mode=standard&language=kk&sort=title_asc&page=1`;
const overlay = "[data-book-transition]";
let staff: Awaited<ReturnType<typeof apiLogin>>;
let bookId: string;
let coverUrl: string;

test.beforeAll(async ({ request }) => {
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD is required");
  staff = await apiLogin(request, "librarian@smartlibrary.example", password);
  const response = await request.post("/api/v1/books", {
    headers: staff,
    data: { title, language: "kk" },
  });
  expect(response.status()).toBe(201);
  bookId = (await response.json()).id;
  // A portrait PNG on the real media endpoint exercises contain inside a landscape card.
  const uploaded = await request.post(`/api/v1/books/${bookId}/cover`, {
    headers: staff,
    multipart: {
      file: {
        name: "cover.png",
        mimeType: "image/png",
        buffer: Buffer.from(
          "iVBORw0KGgoAAAANSUhEUgAAACgAAABQCAIAAADk7aCWAAAAfUlEQVR42u3aoQ2AMBAF0EKYA8kAjMAOhFFwCBwJm7ADgyCZBFFHkISm5H3Tupc7c5emRTusIUXKkChVPJbuiJdxb35eMRgMBoPBYDD4/+vtLdtcv2j006nVYDAYDM53LD4OMq0Gg8FgMBgMBoPBYDAYDA6Zvfp89sUnfcUXmDYKzWrKxKoAAAAASUVORK5CYII=",
          "base64",
        ),
      },
    },
  });
  expect(uploaded.status()).toBe(200);
  coverUrl = (await uploaded.json()).cover_url;
});

test.afterAll(async ({ request }) => {
  if (!bookId) return;
  if (coverUrl)
    expect(
      (
        await request.delete(`/api/v1/books/${bookId}/cover`, {
          headers: staff,
        })
      ).ok(),
    ).toBe(true);
  expect(
    (
      await request.patch(`/api/v1/books/${bookId}/archive`, {
        headers: staff,
        data: { archived: true },
      })
    ).ok(),
  ).toBe(true);
});

for (const viewport of [
  { width: 1280, height: 800 },
  { width: 390, height: 844 },
]) {
  test(`loaded cover opens, releases detail, and restores catalog at ${viewport.width}px`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.goto(catalogUrl);
    const initialUrl = page.url();
    const card = page.getByRole("link", { name: title, exact: true });
    await expect(card).toBeVisible();
    const image = card.locator("img");
    await image.scrollIntoViewIfNeeded();
    await image.evaluate((img: HTMLImageElement) => img.decode());
    if (viewport.width === 390) {
      await card.focus();
      await page.keyboard.press("Enter");
    } else {
      await image.click();
    }
    await expect(page.locator(overlay)).toBeAttached();
    await expect(page).toHaveURL(new RegExp(`/books/${bookId}$`));
    await expect(page.locator(overlay)).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
    await page
      .getByRole("link", { name: "Брондау үшін кіріңіз" })
      .click({ trial: true });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.goBack();
    await expect(page).toHaveURL(initialUrl);
    await expect(card).toBeVisible();
    await page.goForward();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
    await expect(page.locator(overlay)).toHaveCount(0);
  });
}

test("a pending book request exposes loading and recovers on the real response", async ({
  page,
}) => {
  await page.goto(catalogUrl);
  const card = page.getByRole("link", { name: title, exact: true });
  await card
    .locator("img")
    .evaluate((image: HTMLImageElement) => image.decode());
  const gate = Promise.withResolvers<void>();
  await page.route(`**/api/v1/books/${bookId}?*`, async (route) => {
    await gate.promise;
    await route.continue();
  });
  try {
    await card.click();
    await expect(page.locator(overlay)).toBeAttached();
    await expect(page).toHaveURL(new RegExp(`/books/${bookId}$`));
    await expect(page.locator(overlay)).toHaveCount(0, { timeout: 2800 });
    await expect(
      page.getByRole("main").getByText("Жүктелуде…", { exact: true }),
    ).toBeVisible();
  } finally {
    gate.resolve();
  }
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
});

test("an unavailable cover still opens and modified clicks retain the catalog", async ({
  page,
}) => {
  await page.route(`**${coverUrl}`, (route) => route.abort("failed"));
  await page.goto(catalogUrl);
  const initialUrl = page.url();
  const card = page.getByRole("link", { name: title, exact: true });
  await expect(
    card.getByRole("img", { name: "Мұқабасыз кітап" }),
  ).toBeVisible();
  const [popup] = await Promise.all([
    page.context().waitForEvent("page"),
    card.click({ modifiers: ["ControlOrMeta"] }),
  ]);
  await expect(popup.getByRole("heading", { level: 1 })).toHaveText(title);
  await popup.close();
  await expect(page).toHaveURL(initialUrl);
  await expect(page.locator(overlay)).toHaveCount(0);
  await card.click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(page.locator(overlay)).toHaveCount(0);
});

test("Back during the opening releases the catalog for the next interaction", async ({
  page,
}) => {
  await page.goto(catalogUrl);
  const initialUrl = page.url();
  const card = page.getByRole("link", { name: title, exact: true });
  await card
    .locator("img")
    .evaluate((image: HTMLImageElement) => image.decode());
  await Promise.all([
    page.waitForURL(new RegExp(`/books/${bookId}$`), { waitUntil: "commit" }),
    card.click(),
  ]);
  await expect(page.locator(overlay)).toBeAttached({ timeout: 500 });
  await page.goBack();
  await expect(page).toHaveURL(initialUrl);
  await expect(page.locator(overlay)).toHaveCount(0);
  const field = page.getByRole("searchbox");
  await field.fill("Абай");
  await page.getByRole("button", { name: "Іздеу", exact: true }).click();
  await expect(
    page.locator("article").filter({ hasText: "Абай жолы" }).first(),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/catalog\?/);
});
