# The Sky Has a Pulse

An interactive explorable explanation for **DSC 106 (Spring 2026)** that turns six
years of white stork bio-logging data into a scrollable story of motion, rhythm,
and loss. Each tagged stork carries a tri-axial accelerometer; this page reads
migration not as a route on a map but as *bodily motion over time*.

**Team:** Roxanne Wang, Ryan Zhang, Keith Gong

## Live project

Published with GitHub Pages from the top level of this repository:

```
https://xibahbah.github.io/LifeTrack/
```

Enable Pages under **Settings -> Pages -> Build from branch -> `main` / root**.

## Running locally

The page loads a JSON asset, so it must be served over HTTP, not opened as a
`file://` URL:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

## What the project includes

The five scenes form one coordinated D3 instrument. A shared month beam moved
in any scene updates all of the others.

- **Scene 1 — Living sky**: a canvas field of 20 drifting lights whose pulse
  speed and glow follow each bird's monthly sampled activity; recorded deaths
  make a light visibly end as time advances.
- **Scene 2 — The pulse wall**: a heatmap of 20 birds by 70 months with a
  shared month scrubber, row selection, tooltips, outcome filters, and coral
  severed endpoints for each recorded death.
- **Scene 3 — Selected bird**: a linked monthly timeline and 24-hour radial
  rhythm clock. Brushing the timeline scales the whole-record hourly shape by
  the sampled activity of the chosen interval, explicitly avoiding invented
  month-by-hour resolution.
- **Scene 4 — Disappearance**: the twelve recorded-death trails gathered
  together, each terminating at a distinct coral cut crossed by the shared
  attention beam.
- **Scene 5 — Flock summary**: all bird traces overlaid against the
  available-bird monthly average, with seasonal bands and a selected-bird
  toggle/click interaction.
- **Project writeup**: embedded at the bottom of the page.

## Repository contents

- `index.html` — the explorable explanation (HTML, CSS, and D3 visualization code).
- `data/stork_pulse_interactive.json` — processed per-bird monthly/hourly pulse data.
- `vendor/d3.v7.min.js` — D3 v7, vendored locally so the page works without a CDN.

## Data source

Movebank Data Repository, *LifeTrack White Stork SW Germany* (2013–2019), DOI
[10.5441/001/1.ck04mn78](https://doi.org/10.5441/001/1.ck04mn78).

The "pulse" shown is a **derived activity index** computed from tri-axial
accelerometer bursts, prepared from a systematic every-500th-row sample of the
raw acceleration files. Raw accelerometer exports are not stored here because
they exceed GitHub's file-size limit; the prepared JSON asset is included so the
page runs without them.
