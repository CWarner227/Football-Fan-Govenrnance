import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 180000,
  expect: { timeout: 15000 },
  use: {
    baseURL: process.env.DASHBOARD_URL ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  reporter: [["list"], ["html", { open: "never" }]],
});
