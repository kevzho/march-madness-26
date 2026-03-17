import pandas as pd
from .features import build_pairwise_features
from .model import predict_probabilities


def simulate_bracket(bracket_df: pd.DataFrame, team_table: pd.DataFrame, model=None) -> pd.DataFrame:
    """
    The tournament engine: loops through slots in round_order,
    simulating the tournament, predicting the results of the current game, and
    storing the winner, team1_win_prob, and team2_win_prob.
    """
    winners = {}
    rows = []

    for row in bracket_df.sort_values(['round_order', 'slot']).itertuples(index=False):
        team1 = winners.get(row.left, row.left)
        team2 = winners.get(row.right, row.right)
        matchup = pd.DataFrame([{'team1': team1, 'team2': team2}])
        feat = build_pairwise_features(matchup, team_table)
        p_team1 = float(predict_probabilities(feat, model)[0])
        winner = team1 if p_team1 >= 0.5 else team2
        rows.append({
            'slot': row.slot,
            'round_name': row.round_name,
            'round_order': row.round_order,
            'team1': team1,
            'team2': team2,
            'team1_win_prob': round(p_team1, 4),
            'winner': winner,
            'winner_prob': round(p_team1 if winner == team1 else 1.0 - p_team1, 4),
        })
        winners[row.slot] = winner

    return pd.DataFrame(rows)

