import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "../tests/e2e",
  outputDir: "test-results",
  use: {
    channel: process.env.PLAYWRIGHT_CHANNEL,
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    trace: "retain-on-failure",
  },
  reporter: "list",
  retries: 0,
  // Docker development routes compile on first use; assertions still require completion.
  expect: { timeout: 15000 },
});
