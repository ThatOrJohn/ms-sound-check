// @ts-check
import { defineConfig } from "astro/config";
import react from "@astrojs/react";

// On GitHub Pages without a custom domain the site lives under /<repo>/.
// CI passes SITE_URL and SITE_BASE; locally both default to the root.
export default defineConfig({
  site: process.env.SITE_URL || "http://localhost:4321",
  base: process.env.SITE_BASE || "/",
  trailingSlash: "always",
  integrations: [react()],
  build: { format: "directory" },
  // Astro 7's default ("jsx") drops whitespace at line breaks inside prose, e.g. "check\n<a>MDMR</a>"
  // renders as "checkMDMR". Keep the classic collapsing so wrapped text in templates stays readable.
  compressHTML: true,
});
