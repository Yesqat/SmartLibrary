import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "../tests/deployment",
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR ?? "test-results-production",
  timeout: 60000,
  expect: { timeout: 15000 },
  use: {
    channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge",
    baseURL: "https://localhost:8443",
    // Only this localhost test CA is untrusted by the browser. Python verifies its chain separately.
    ignoreHTTPSErrors: true,
    trace: "off",
  },
  reporter: "list",
  retries: 0,
});
