import { test, expect } from "../../frontend/node_modules/@playwright/test";

test("CSP permits hydration and blocks injected inline scripts with a fresh page nonce", async ({
  page,
}) => {
  // Simulate an HTML injection at the document boundary; DevTools evaluation is
  // a trusted browser execution context and is not an untrusted parser script.
  await page.route("**/login", async (route) => {
    const response = await route.fetch();
    const html = (await response.text()).replace(
      "<head>",
      "<head><script>document.documentElement.dataset.injectionExecuted = 'yes'</script>",
    );
    await route.fulfill({ response, body: html });
  });
  const response = await page.goto("/login");
  const policy = response!.headers()["content-security-policy"];
  expect(policy).toContain("'strict-dynamic'");
  expect(policy).toContain("frame-ancestors 'none'");
  const nonce = policy.match(/'nonce-([^']+)'/)![1];
  const scripts = await page
    .locator("script")
    .evaluateAll((elements) => elements.map((s) => s.nonce));
  expect(scripts.filter(Boolean)).toContain(nonce);
  await expect(
    page.getByRole("button", { name: "Кіру", exact: true }),
  ).toBeEnabled();
  expect(
    await page.locator("html").getAttribute("data-injection-executed"),
  ).toBeNull();
  const next = await page.reload();
  expect(next!.headers()["content-security-policy"]).not.toContain(
    `'nonce-${nonce}'`,
  );
});
