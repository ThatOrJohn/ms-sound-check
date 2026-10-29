// Share images (Open Graph, 1200x630) drawn at build time: satori lays the card out as SVG with the text as
// paths, and sharp rasterizes it, so no fonts are needed on the build machine. Decision 0026.
import fs from "node:fs";
import path from "node:path";
import satori from "satori";
import sharp from "sharp";
import type { Tile } from "./readouts";

export const OG_W = 1200;
export const OG_H = 630;
const PAD_X = 64, GAP = 16;
const TILE_W = (OG_W - 2 * PAD_X - 3 * GAP) / 4;   // four across; fewer stay the same size, left-aligned

const root = process.cwd();
// Satori can't read woff2, so the static Geist packages supply plain woff files of the same faces.
const font = (pkg: string, file: string) => fs.readFileSync(path.join(root, "node_modules", "@fontsource", pkg, "files", file));
const FONTS = [
  { name: "Geist", data: font("geist", "geist-latin-400-normal.woff"), weight: 400 as const, style: "normal" as const },
  { name: "Geist", data: font("geist", "geist-latin-600-normal.woff"), weight: 600 as const, style: "normal" as const },
  { name: "Geist Mono", data: font("geist-mono", "geist-mono-latin-500-normal.woff"), weight: 500 as const, style: "normal" as const },
];

/** The dark theme's colors, read from global.css so the image can't drift from the site. */
function tokens(): Record<string, string> {
  const css = fs.readFileSync(path.join(root, "src", "styles", "global.css"), "utf8");
  const read = (block: string) => Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{3,8})/gi)].map((m) => [m[1], m[2]]));
  const light = css.slice(css.indexOf(":root {"), css.indexOf("}", css.indexOf(":root {")));
  const darkAt = css.indexOf(':root[data-theme="dark"]');
  const dark = css.slice(darkAt, css.indexOf("}", darkAt));
  return { ...read(light), ...read(dark) };
}

// Satori takes React-like element objects; this keeps the layout below readable without JSX.
type Node = { type: string; props: Record<string, unknown> };
const h = (type: string, style: Record<string, unknown>, ...children: (Node | string | null | false)[]): Node => {
  const kids = children.filter((c) => c !== null && c !== false);
  return { type, props: { style, children: kids.length === 1 ? kids[0] : kids } };
};

export interface Card { eyebrow: string; headline: string; tiles: Tile[]; stamp: string }

export async function render(card: Card): Promise<Buffer> {
  const t = tokens();
  const size = card.headline.length <= 90 ? 58 : card.headline.length <= 150 ? 48 : 40;
  const tiles = card.tiles.slice(0, 4);
  const el = h("div", { width: OG_W, height: OG_H, display: "flex", flexDirection: "column", background: t.sky, color: t.ink,
      fontFamily: "Geist", padding: `52px ${PAD_X}px 44px` },
    h("div", { display: "flex", alignItems: "center", gap: 16 },
      h("div", { width: 34, height: 34, borderRadius: 17, border: `3px solid ${t.accent}`, display: "flex" }),
      h("div", { fontSize: 30, fontWeight: 600, letterSpacing: -0.5 }, "Sound Check"),
      h("div", { fontFamily: "Geist Mono", fontSize: 20, color: t["ink-soft"], letterSpacing: 2, marginLeft: 8 },
        card.eyebrow.toUpperCase())),
    h("div", { display: "flex", flex: 1, alignItems: "center", fontSize: size, fontWeight: 600, lineHeight: 1.16,
      letterSpacing: -1, paddingRight: 24 }, card.headline),
    tiles.length > 0 && h("div", { display: "flex", gap: GAP, marginBottom: 30 },
      ...tiles.map((x) => h("div", { display: "flex", flexDirection: "column", width: TILE_W, background: t.paper,
          border: `1px solid ${t.rule}`, borderRadius: 14, padding: "16px 20px", gap: 4 },
        // One line, so the numbers line up: "Pascagoula River flow" -> "Pascagoula flow".
        h("div", { fontFamily: "Geist Mono", fontSize: 16, color: t["ink-soft"], letterSpacing: 1.5, whiteSpace: "nowrap",
          overflow: "hidden", textOverflow: "ellipsis" }, x.label.replace(/ River flow$/, " flow").toUpperCase()),
        h("div", { display: "flex", alignItems: "baseline", gap: 8 },
          h("div", { fontSize: 44, fontWeight: 600, letterSpacing: -1 }, x.value),
          h("div", { fontSize: 20, color: t["ink-soft"] }, x.unit)),
        h("div", { fontSize: 18, color: t["ink-soft"] }, x.sub || " ")))),
    h("div", { display: "flex", height: 6, borderRadius: 3, marginBottom: 16,
      backgroundImage: `linear-gradient(90deg, ${t.fresh}, ${t.brackish} 48%, ${t.gulf})` }),
    h("div", { display: "flex", justifyContent: "space-between", fontSize: 19, color: t["ink-soft"] },
      h("div", {}, card.stamp),
      h("div", {}, "Not for navigation or harvest decisions")));
  const svg = await satori(el as any, { width: OG_W, height: OG_H, fonts: FONTS });
  return sharp(Buffer.from(svg)).png().toBuffer();
}
