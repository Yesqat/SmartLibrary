import { test, expect } from "../../frontend/node_modules/@playwright/test";
test("frontend renders Kazakh shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "kk");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Кітапхана",
  );
});
test("frontend liveness", async ({ request }) => {
  const response = await request.get("/health");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "ok" });
});

test("Nginx routes API readiness and documentation to the backend", async ({
  request,
}) => {
  const response = await request.get("/api/v1/ready");
  expect(response.status()).toBe(200);
  expect(response.headers()["x-request-id"]).toBeTruthy();
  expect(await response.json()).toEqual({
    status: "ready",
    dependencies: { postgres: "ok", redis: "ok" },
  });
  const docs = await request.get("/docs");
  expect(docs.status()).toBe(200);
  expect(await docs.text()).toContain("swagger-ui");
});
