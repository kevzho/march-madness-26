# Websites

This folder contains static websites generated from pipeline outputs.

## Build a site from outputs

```bash
python3 build_site.py --source outputs/run_001 --out websites/run_001
```

## View locally

Browsers often block `fetch()` from `file://`, so use a local server:

```bash
python3 -m http.server 5173 --directory websites
```

Then open `http://localhost:5173` and select a run (or go directly to `http://localhost:5173/run_001/`).
