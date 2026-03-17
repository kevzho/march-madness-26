from pathlib import Path
from .bracket import simulate_bracket
from .data_io import ensure_dir, load_bracket_slots, load_team_snapshots, load_tournament_results
from .features import build_training_frame
from .model import fit_matchup_model
from .power import add_power_ratings


def run_pipeline(
    current_team_snapshot_path,
    bracket_slots_path,
    output_dir='outputs',
    historical_team_snapshot_path=None,
    historical_tournament_results_path=None,
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

    current_teams = add_power_ratings(load_team_snapshots(current_team_snapshot_path))
    current_teams.to_csv(Path(output_dir) / 'power_scale.csv', index=False)

    model = None
    train_df = None
    if historical_team_snapshot_path and historical_tournament_results_path:
        hist_teams = add_power_ratings(load_team_snapshots(historical_team_snapshot_path))
        hist_results = load_tournament_results(historical_tournament_results_path)
        train_df = build_training_frame(hist_results, hist_teams)
        model = fit_matchup_model(train_df)
        train_df.to_csv(Path(output_dir) / 'training_features.csv', index=False)

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
    }

