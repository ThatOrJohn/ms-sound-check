// Weekly digest as RSS 2.0 (decision 0031). Entries come from the pipeline's digest.json, newest first.
import type { APIRoute } from "astro";
import { loadDigest, loadLatest } from "../lib/data";
import { href } from "../lib/format";

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export const GET: APIRoute = ({ site }) => {
  const data = loadLatest();
  const home = new URL(href(), site).toString();
  const items = loadDigest().map((e) => {
    const body = [e.headline, ...e.lines].map((l) => `<p>${esc(l)}</p>`).join("");
    return `<item><title>${esc(e.title)}</title><link>${home}</link><guid isPermaLink="false">${e.id}</guid>` +
      `<pubDate>${new Date(e.date).toUTCString()}</pubDate><description>${esc(body)}</description></item>`;
  }).join("");
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>` +
    `<title>Sound Check: ${esc(data.region.name)} weekly</title><link>${home}</link>` +
    `<description>A weekly plain-language summary of ${esc(data.region.name)} conditions. Not for navigation or harvest decisions.</description>` +
    `<language>en-us</language>${items}</channel></rss>`;
  return new Response(xml, { headers: { "Content-Type": "application/rss+xml; charset=utf-8" } });
};
