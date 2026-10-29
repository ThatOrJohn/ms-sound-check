# 0024: Vibrio-favorable water is a calm seasonal note, not a Signal

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Vibrio bacteria (including *V. vulnificus*) live naturally in the Sound and grow fastest in warm water, about 20°C
and up, at moderate salinity, about 5-25 ppt. Both readings are live at every station, so we can say when the water
is in that range. We can't measure the bacteria, and the risk falls mostly on a few people: those with open cuts in
the water, those who eat raw oysters, and people with liver disease or weakened immunity. Health warnings about Vibrio
are easy to make alarming ("flesh-eating bacteria").

How often the water is in range, 1998-2026, daily means (readings over the 36 ppt ceiling left out):

| Station | All days | April-October, by month |
|---|---|---|
| West Sound (Merrill Shell) | 51% | 72-89% |
| Biloxi Back Bay | 54% | 76-88% |
| East Sound (Round Island) | 49% | 50-95% |
| Pearl River mouth | 29% | 11-77%, mostly July-October |

## Decision
Show a short, neutral section, "Warm-water bacteria (Vibrio)", on the Coast, Oysters and Fishing pages while at least
one live station's 3-day mean is 20°C or warmer and 5-25 ppt. Leave it out of Signals and headlines, give it no
warning colors, and show nothing when no station is in range. The wording was reviewed before it shipped.

## Why
- The conditions hold on most warm-season days, so as a Signal the note would be on half the year and would make
  the Signals list look like a constant warning. What's useful is plain advice while the water is warm.
- Hiding it in cool months, rather than saying "too cool for Vibrio", avoids implying the water is safe. Vibrio
  is still present in cooler water, just less often.
- The 3-day mean keeps it from flickering on and off when the water sits near 20°C in spring and fall.
- It uses the same QC as everything else: retired stations, readings over the ceiling and virtual-sensor suspects
  are left out.
- Advice follows the Mississippi State Department of Health and CDC (cover cuts or stay out, cook shellfish) and
  links to both. It leaves out case counts, death rates and "flesh-eating".

## Consequences
- Thresholds, season wording and links live in `regions/ms.yaml` (`vibrio:`), and pages opt in through `card_order`.
- No dev fixture forces it on, so in winter it can only be seen by lowering `temp_min_c` locally.
- Revisit if MSDH or MDMR publish actual Vibrio monitoring (use theirs instead), or if readers take the note as a
  closure or a swim advisory.
