import json
from pathlib import Path
from .bracket import simulate_bracket
from .data_io import ensure_dir, load_bracket_slots, load_team_snapshots, load_tournament_results
from .features import build_training_frame
from .model import fit_matchup_model
from .power import add_power_ratings
from .validation import run_season_evaluation


def _csv_has_data_rows(path: Path) -> bool:
    """
    Returns True if the CSV exists and appears to have at least 1 data row
    (i.e., more than just a header line).
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                if line.strip():
                    return True
    except FileNotFoundError:
        return False
    return False


def _infer_current_season(current_teams_df, hist_teams_df) -> int | None:
    """
    Best-effort guess of the "current" season so we don't train on in-progress labels.
    Priority: current snapshot -> historical snapshot.
    """
    for df in (current_teams_df, hist_teams_df):
        if df is None:
            continue
        if "season" not in df.columns:
            continue
        seasons = df["season"].dropna().unique()
        if len(seasons) == 0:
            continue
        try:
            return int(max(seasons))
        except Exception:
            continue
    return None


def _filter_historical_for_supervised_training(
    hist_teams,
    hist_results,
    *,
    current_season: int | None,
    drop_2021: bool,
) -> tuple:
    """
    Filters historical inputs for supervised training:
    - Excludes `current_season` (and any future seasons) from labeled training.
    - Optionally drops 2021 if you want to avoid a non-standard tournament year.
    """
    if hist_teams is None or hist_results is None:
        return hist_teams, hist_results

    results = hist_results.copy()
    teams = hist_teams.copy()

    if current_season is not None and "season" in results.columns:
        results = results[results["season"] < int(current_season)]

    if drop_2021 and "season" in results.columns:
        results = results[results["season"] != 2021]

    if "season" in teams.columns and "season" in results.columns:
        label_seasons = set(results["season"].dropna().astype(int).unique())
        teams = teams[teams["season"].astype(int).isin(label_seasons)]

    return teams, results


def run_pipeline(
    current_team_snapshot_path,
    bracket_slots_path,
    output_dir='outputs',
    historical_team_snapshot_path=None,
    historical_tournament_results_path=None,
    current_season: int | None = None,
    drop_2021: bool = False,
    eval_scheme: str | None = None,
):
    """
    The "master controller" here's what it does:
    1. Loads current team snapshot
    2. Computes power rankings
    3. Optionally builds training data & fits the model from historical inputs
    4. Runs the bracket simulation
    5. Saves `power_scale.csv` & `bracket_predictions.csv` & returns the champion.
    """
    output_dir = ensure_dir(output_dir)

    if historical_team_snapshot_path is None and historical_tournament_results_path is None:
        repo_root = Path(__file__).resolve().parents[1]
        default_hist_teams = repo_root / "inputs" / "historical_team_snapshots_template.csv"
        default_hist_results = repo_root / "inputs" / "historical_tournament_results_template.csv"
        if _csv_has_data_rows(default_hist_teams) and _csv_has_data_rows(default_hist_results):
            historical_team_snapshot_path = default_hist_teams
            historical_tournament_results_path = default_hist_results

    current_teams = add_power_ratings(load_team_snapshots(current_team_snapshot_path))
    current_teams.to_csv(Path(output_dir) / 'power_scale.csv', index=False)

    model = None
    train_df = None
    evaluation = None
    if historical_team_snapshot_path and historical_tournament_results_path:
        hist_teams = add_power_ratings(load_team_snapshots(historical_team_snapshot_path))
        hist_results = load_tournament_results(historical_tournament_results_path)

        inferred_current = current_season or _infer_current_season(current_teams, hist_teams)
        hist_teams, hist_results = _filter_historical_for_supervised_training(
            hist_teams,
            hist_results,
            current_season=inferred_current,
            drop_2021=drop_2021,
        )

        train_df = build_training_frame(hist_results, hist_teams)
        model = fit_matchup_model(train_df)
        train_df.to_csv(Path(output_dir) / 'training_features.csv', index=False)
        if eval_scheme:
            evaluation = run_season_evaluation(train_df, scheme=eval_scheme)
            with (Path(output_dir) / "evaluation.json").open("w", encoding="utf-8") as f:
                json.dump(evaluation, f, ensure_ascii=False, indent=2)

    bracket_df = load_bracket_slots(bracket_slots_path)
    predictions = simulate_bracket(bracket_df, current_teams, model=model)
    predictions.to_csv(Path(output_dir) / 'bracket_predictions.csv', index=False)

    champion = predictions.loc[predictions['slot'] == 'CHAMPION', 'winner']
    champion = champion.iloc[0] if not champion.empty else None

    return {
        'power_scale': current_teams,
        'training_features': train_df,
        'predictions': predictions,
        'champion': champion,
        'evaluation': evaluation,
    }
