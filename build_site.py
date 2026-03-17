from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import zipfile

import pandas as pd


@dataclass(frozen=True)
class BuildConfig:
    source_dir: Path
    out_dir: Path
    run_id: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def _champion_from_bracket(pred: pd.DataFrame) -> str | None:
    if pred is None or pred.empty:
        return None
    if "slot" not in pred.columns or "winner" not in pred.columns:
        return None
    champ = pred.loc[pred["slot"] == "CHAMPION", "winner"]
    if champ.empty:
        return None
    value = champ.iloc[0]
    return None if pd.isna(value) else str(value)


def _copy_template(dst: Path) -> None:
    template_dir = Path(__file__).parent / "website_template"
    if not template_dir.exists():
        raise FileNotFoundError(f"Missing template dir: {template_dir}")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(template_dir, dst)


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_data_archive(source_dir: Path, out_dir: Path) -> str:
    archive_path = out_dir / "data" / "data.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for csv_path in sorted(source_dir.glob("*.csv")):
            zf.write(csv_path, arcname=csv_path.name)
    return "./data/data.zip"


def build_site(cfg: BuildConfig) -> Path:
    power_csv = cfg.source_dir / "power_scale.csv"
    bracket_csv = cfg.source_dir / "bracket_predictions.csv"

    power = _read_csv(power_csv)
    bracket = _read_csv(bracket_csv)

    _copy_template(cfg.out_dir)

    # Normalize column names for JS friendliness
    power.columns = [str(c).strip().lower() for c in power.columns]
    bracket.columns = [str(c).strip().lower() for c in bracket.columns]

    _write_json(cfg.out_dir / "data" / "power_scale.json", power.to_dict(orient="records"))
    _write_json(cfg.out_dir / "data" / "bracket_predictions.json", bracket.to_dict(orient="records"))

    data_archive = _make_data_archive(cfg.source_dir, cfg.out_dir)
    meta = {
        "run_id": cfg.run_id,
        "built_at": _utc_now_iso(),
        "source_dir": str(cfg.source_dir),
        "champion": _champion_from_bracket(bracket),
        "data_archive": data_archive,
    }
    _write_json(cfg.out_dir / "data" / "meta.json", meta)

    return cfg.out_dir


def _parse_args():
    import argparse

    p = argparse.ArgumentParser(description="Build a static website from pipeline outputs.")
    p.add_argument("--source", required=True, help="Outputs folder containing bracket_predictions.csv and power_scale.csv")
    p.add_argument("--out", required=True, help="Website output folder")
    p.add_argument("--run-id", default=None, help="Run identifier shown in the UI (default: folder name of --source)")
    return p.parse_args()


def main():
    args = _parse_args()
    source_dir = Path(args.source)
    out_dir = Path(args.out)
    run_id = args.run_id or source_dir.name

    built = build_site(BuildConfig(source_dir=source_dir, out_dir=out_dir, run_id=run_id))
    print(f"Built site: {built}")


if __name__ == "__main__":
    main()

