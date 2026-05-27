# The Sky Has a Pulse

An interactive explorable explanation for **DSC 106 (Spring 2026)** that turns six
years of white stork bio-logging data into a scrollable story of motion, rhythm,
and loss. Each tagged stork carries a tri-axial accelerometer; this page reads
migration not as a route on a map but as *bodily motion over time*.

**Team:** Roxanne Wang, Ryan Zhang, Keith Gong

## Live prototype

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

## What this prototype includes

This is the **initial prototype** milestone. Per the assignment, the project is
not yet complete: the structure is laid out, the main visualization and its
interactions are working, and the remaining scenes are scaffolded.

- **Scene 1 — Hook** *(scaffolded)*: a static title; the animated "living sky"
  of glowing pulses is planned next.
- **Scene 2 — The pulse wall** *(fully built, D3.js)*: a heatmap of 20 birds by
  70 months built with D3 data joins and scales. Interactions: a **month
  scrubber**, **click-to-select** any bird row, **hover tooltips**, and an
  outcome filter (all / recorded dead / no recorded death).
- **Scene 3 — Selected bird** *(fully built, D3.js)*: selecting a bird drives a
  linked monthly-pulse timeline and a 24-hour radial rhythm clock.
- **Scenes 4 & 5** *(scaffolded)*: "Feel disappearance" and "Return to the
  flock" are present with descriptive text and marked as in progress.
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
