# 0026: Draw share images at build time with satori and sharp

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Links posted to Bluesky, X or a group chat showed only a title and description. A preview image with the headline and
a few numbers says far more, and the weekly digest (roadmap, Next) will need one. The site is static on GitHub Pages
and rebuilds every 4 hours, so there's no server to draw images on request.

## Decision

Every page gets a 1200x630 PNG drawn during `astro build` by a static endpoint (`web/src/pages/og/[name].png.ts`,
layout in `web/src/lib/og.ts`): the home and persona pages show their headline and the same readout tiles as the page
(`web/src/lib/readouts.ts`), station pages show the station's live readings, and About shows a one-line summary.
`og:image` carries `?v=<build time>` so a share made after a rebuild doesn't get the old picture from a cache.

## Why

- **Satori + sharp:** satori lays the card out from flexbox styles and turns the text into SVG paths, and sharp (already
  installed by Astro) rasterizes it. Because the text is paths, the build machine needs no fonts, unlike drawing SVG
  text with sharp alone, which depends on what fontconfig finds on the CI runner. All 21 images take about 0.5 s.
- **Same numbers as the page:** the tiles come from the function the page uses, so the picture and the page can't
  disagree. A reading flagged as a possible sensor problem is left out, since an image has no room for the caveat.
- **Dark theme only, from the tokens:** colors are read from the dark block in `global.css`, so a palette change
  reaches the images. One theme keeps a single image per page; the dark one stands out in a light feed.
- **The disclaimer is in the picture:** a screenshot or repost can travel without the page, so every image says "Not
  for navigation or harvest decisions" and when it was updated.

## Consequences

- New dependencies: `satori` (pinned to 0.33.5: it had dozens of releases in October 2026, and 0.32 and older carry an
  SVG-escaping advisory), `sharp` (pinned to the version Astro uses), and `@fontsource/geist` / `geist-mono` for woff
  files, since satori can't read the woff2 the site ships. satori pins `fflate` 0.7.3, which has a moderate advisory
  (a malformed ZIP64 file can hang it); `overrides` in `web/package.json` lifts it to the patched 0.7.5. Drop the
  override once satori depends on a fixed fflate.
- Social sites cache by URL, and the `?v=` value only changes when the page is shared again after a rebuild; a post
  already out keeps the picture from when it was made. That's fine: it's a snapshot with its time on it.
- Revisit if images need per-theme versions, or if the build moves somewhere sharp's prebuilt binaries don't run.
