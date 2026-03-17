# March Madness Elo Pipeline (2026)

Compute simple power ratings (Elo-like) from a team snapshot, simulate a slot-based tournament bracket, and generate a static website to explore the results.

## Requirements
- Python 3.9+

## Data inputs
- `inputs/team_snapshots_2026_sample.csv`: current-season team snapshot (wins/losses/NET/seed/region).
- `inputs/bracket_slots_2026_sample.csv`: slot-based bracket structure (includes First Four placeholders).
- `inputs/historical_team_snapshots_template.csv`: template for multi-season snapshot data (optional).
- `inputs/historical_tournament_results_template.csv`: template for multi-season tournament outcomes (optional).

## Note:
`run_00X` refers to the $x$th run. I've provided one example run for you.

## Install
```bash
python3 -m pip install -r requirements.txt
```

## Run the pipeline
```bash
python3 -m marchmadness.cli \
  --teams inputs/team_snapshots_2026_sample.csv \
  --bracket inputs/bracket_slots_2026_sample.csv \
  --out outputs/run_00X
```

### Outputs
- `outputs/run_00X/power_scale.csv`
- `outputs/run_00X/bracket_predictions.csv`

Make a new run by changing `--out` (e.g. `outputs/run_002`).

### Optional: train a matchup model (historical)
If you provide both historical files, the pipeline will build training features and fit a simple classifier:

```bash
python3 -m marchmadness.cli \
  --teams inputs/team_snapshots_2026_sample.csv \
  --bracket inputs/bracket_slots_2026_sample.csv \
  --hist-teams inputs/historical_team_snapshots_template.csv \
  --hist-results inputs/historical_tournament_results_template.csv \
  --out outputs/run_00X
```

## Website (from outputs)
Generate a static site from a run’s outputs:

```bash
python3 build_site.py --source outputs/run_00X --out websites/run_00X
```

### Pages
- `websites/run_00X/index.html` (overview)
- `websites/run_00X/bracket.html` (bracket view + table)
- `websites/run_00X/power.html` (power table)

## View locally
Browsers often block `fetch()` from `file://`, so use a local server:

```bash
python3 -m http.server 5173 --directory websites/run_00X # replace with run_001
```

Then open `http://localhost:5173`.

## Notes / troubleshooting
- If `python` isn’t found on your system, use `python3`.
- If you see missing dependency errors, re-run `python3 -m pip install -r requirements.txt`.
- Make sure you change `X` in `run_00X` to an actual number.