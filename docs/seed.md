# Mississippi Sound Conditions Watch — Project Seed

## What this is
A fun side project: a plain-language "what's happening in the Mississippi Sound" watch built on public data. Not a business plan; any sponsorship or beer money is a bonus. Spun out of a broader brainstorm about Gulf Coast / blue economy side projects (sparked by Gulf Blue and local oyster farms on Biloxi trips).

## Core insight
The **data plumbing is already solved**. What's missing is the **interpretation layer**: turning salinity, temperature, and river flow into "so what?" for normal people (shrimpers, anglers, seafood buyers, curious locals). Existing tools are built for scientists and resource managers.

## What already exists (don't rebuild)
- **MDMR + USGS hydrological monitoring** (since 1998): continuous recorder stations around the Sound, e.g., Biloxi Back Bay at Point Cadet, Gulfport Light, Round Island Light, Merrill Shell Light, East Ship Island Light, Grand Pass. Real-time USGS feeds are public and machine-readable.
  - https://dmr.ms.gov/hydrological-monitoring/
  - Example station: https://waterdata.usgs.gov/monitoring-location/USGS-301527088521500/
- **USGS MissS salinity predictions**: ML-generated daily salinity time series for 18 Sound locations, with uncertainty. https://catalog.data.gov/dataset/misss
- **USM msbCOAWST model**: Mississippi Sound & Bight ocean model with near-real-time and forecast modes, driven by the National Water Model for river inflow. Lives in academic papers, not public-facing.
- **Dauphin Island Sea Lab ARCOS** (Alabama side): polished public real-time dashboard with parameter explanations. https://arcos.disl.org — reference for what "done well" looks like next door.
- Other sources to consider: NOAA NDBC buoys, USGS river gauges (Pearl River, Pascagoula, etc.), Bonnet Carré Spillway status (USACE), MDMR harvest-area closure notices.

## Candidate angles
1. **Shrimp season opening prediction** (most interesting hook)
   - MDMR sets opening day from sampling + state law requiring legal-size shrimp; the date moves yearly (May 22, 2023; June 23, 2025; May 26, 2026).
   - MDMR has publicly tied brown shrimp movement to salinity (fresher water pushes them offshore).
   - Idea: given spring river flow/salinity, predict early vs. late opening. Small dataset (~a dozen seasons), so predictions are rough, but publicly checkable every spring — good X content.
2. **Recreational fishing conditions** (e.g., speckled trout vs. salinity/temp). Bigger, chattier audience; possible small sponsorship from bait shops/charters. Weakness: crowded fishing-forecast app space.
3. **Spillway / freshwater-pulse alerts**: Bonnet Carré openings hit the Sound weeks later. Likely a feature of the watch, not its own thing.
4. **Dockside shrimp price tracker** (adjacent idea): crowdsourced weekly dock prices; official landings data lag by months. Dies without committed contributors.

## Red-team notes
- Raw data dashboard alone = already done (ARCOS); value must be interpretation and narrative.
- Shrimp-opening model may show weak signal; validate before building any front end.
- Monetization is thin; treat as hobby/audience-builder.
- Fits the existing pattern of live-data X posts (cf. Austin food-inspection animation idea).

## Suggested first step
Weekend script: pull several years of USGS Sound station data (salinity, temp) + river gauge flow, line it up against historical MDMR shrimp season opening dates, and eyeball whether salinity visibly tracks opening day. If no signal, pivot to the fishing-conditions or general "Sound this week" angle before building UI.

## Open questions
- Output format: X bot, simple web page, newsletter, or all three?
- Which stations/gauges matter most? Do all USGS Sound stations still report salinity, or only some?
- How far back do historical MDMR opening dates go, and are they all published?
- Hosting: Cloudflare Pages like the X games?
