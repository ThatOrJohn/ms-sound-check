# 0025: The tide strip shows NOAA predictions at one station, drawn in the browser

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The Fishing card listed NOAA's predicted highs and lows as text. A small chart of the recent and upcoming tide under
the map makes the same data readable at a glance for everyone, not only the Fishing view. Three things needed
deciding: which water level to show, where "now" comes from, and how the curve is drawn between highs and lows.

Mississippi tides are small (about 1-2.5 ft at Gulfport) and mostly one high and one low a day. Wind often moves the
water more than the tide does: a strong north wind can hold the level a foot or more below the prediction.

## Decision
Show a 48-hour strip (12 hours back, 36 ahead) of NOAA's predicted tide at the middle station in `tides` (Gulfport
Harbor, the one the Fishing card leads with), with a sentence above it ("Rising: high 2.5 ft at 11:55 PM, then low
−0.3 ft at 10:29 AM tomorrow.") and a line saying wind can push the water above or below the prediction. The build
publishes the highs and lows with UTC offsets; the browser draws the curve and places "now".

## Why
- **Predictions, not observed levels.** Predictions are free, reliable and known days ahead. Observed water levels
  would add a sensor feed for a decorative strip, and mixing the two in one line would blur what's measured and
  what's forecast. The wind caveat covers the gap honestly.
- **One station.** Three curves in 44 px would be unreadable. The stations differ by up to about two hours at low
  tide (Bay Waveland runs latest) and a few tenths of a foot, so the strip names its station, and all three stay in
  the Fishing card.
- **"Now" in the browser.** The page is rebuilt every 3 hours. Placing "now" at build time would leave the marker
  up to 3 hours wrong, so the component reads the clock and re-renders every 5 minutes. The fetch starts a day early
  so there's always a past half day to draw.
- **Half-cosine between turns.** NOAA publishes only the highs and lows here (`interval=hilo`). The usual half-cosine
  between turning points is the standard way to sketch the curve from them and needs no extra API call. It's a
  picture of the shape; the labeled times and heights are NOAA's.

## Consequences
- The strip hides itself when predictions are over 2 days old (the adapter's existing max age), or when the reader's
  clock falls outside the predicted range.
- NOAA gives local clock times; in the repeated hour when daylight time ends, the build takes the first one.
- If observed levels are ever wanted (for example to show wind setup), add them as a separate, labeled line.
