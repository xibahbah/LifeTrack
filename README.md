# The Shorter Way South

An interactive data visualization project about white stork migration from
southwest Germany toward Spain and Africa. The project uses D3-based
scrollytelling and exploratory prototypes to show how some birds now take
shorter wintering routes closer to home.

## View The Prototypes

- `final_project_proposal/stork_migration_map.html` is the map-first
  scrollytelling experience.
- `final_project_proposal/sky_has_a_pulse.html` is an ecosystem-style concept.
- `final_project_proposal/stork_pulse_interactive_mockup.html` is a pulse-wall
  interactive concept.

Serve the repository locally so the HTML files can load their JSON assets:

```bash
python3 -m http.server 8000
```

Then open
`http://localhost:8000/final_project_proposal/stork_migration_map.html`.

## Contents

- `final_project_proposal/data/` contains prepared JSON and sampled CSV assets
  used by the visualizations.
- `final_project_proposal/scripts/` and the `make_*_assets.py` files contain
  preparation and figure-generation scripts.
- `final_project_proposal/figures*/` contains rendered project images.
- `final_project_proposal/*.pdf` and `proposal.tex` contain the proposal
  deliverables and source.

## Data Source

The project is based on the Movebank Data Repository dataset *LifeTrack White
Stork SW Germany*, DOI:
[10.5441/001/1.ck04mn78](https://doi.org/10.5441/001/1.ck04mn78).

The raw GPS and acceleration exports used during preparation are not stored in
this repository because they exceed GitHub's individual file size limit. The
prepared visualization assets are included so the interactive pages can be
viewed without those raw inputs.
