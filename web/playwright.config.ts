import { defineConfig, devices } from "@playwright/test";

// Tests run against the built site via `astro preview`, under the same base path as production.
const base = process.env.SITE_BASE || "/";
export default defineConfig({
  testDir: "tests",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://localhost:4321${base.replace(/\/?$/, "/")}` },
  webServer: { command: "npx astro preview --port 4321", port: 4321, reuseExistingServer: !process.env.CI },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
});
