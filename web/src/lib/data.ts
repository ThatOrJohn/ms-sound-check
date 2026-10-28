// Build-time data access. Astro pages read the pipeline's JSON from public/data
// so every page is pre-rendered with current numbers.
import fs from "node:fs";
import path from "node:path";
import type { Latest, SiteFile } from "./types";

export const REGION = process.env.REGION || "ms";
const dataDir = path.join(process.cwd(), "public", "data", REGION);

export function loadLatest(): Latest {
  return JSON.parse(fs.readFileSync(path.join(dataDir, "latest.json"), "utf8"));
}

export function loadSite(id: string): SiteFile | null {
  const p = path.join(dataDir, "sites", `${id}.json`);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
}
