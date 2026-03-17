"""
Joins team stats onto matchups, creating pairwise features such as:
- elo_delta
- power_delta
- win_pct_delta
- rank_delta
- seed_delta
"""

import pandas as pd

FEATURE_COLUMNS = [
    'elo_delta',
    'power_delta',
    'win_pct_delta',
    'rank_delta',
    'seed_delta',
]

def build_pairwise_features(matchups: pd.DataFrame, team_table: pd.DataFrame) -> pd.DataFrame:
    """
    Takes in DataFrame with columns like ['team1' & 'team2'],
    Creates DataFrame with team statistics (elo, power_score, win_pct, net_rank, seed).
    """
    matchup_df = matchups.copy()
    key_cols = ['team']
    if 'season' in matchup_df.columns and 'season' in team_table.columns:
        key_cols = ['season', 'team']

    left = team_table.copy().rename(columns=lambda c: f'team1_{c}' if c not in {'season'} else c)
    right = team_table.copy().rename(columns=lambda c: f'team2_{c}' if c not in {'season'} else c)

    left_on = ['team1'] if key_cols == ['team'] else ['season', 'team1']
    right_on = ['team1_team'] if key_cols == ['team'] else ['season', 'team1_team']
    feat = matchup_df.merge(left, left_on=left_on, right_on=right_on, how='left')

    left_on = ['team2'] if key_cols == ['team'] else ['season', 'team2']
    right_on = ['team2_team'] if key_cols == ['team'] else ['season', 'team2_team']
    feat = feat.merge(right, left_on=left_on, right_on=right_on, how='left')

    missing = feat[feat[['team1_team', 'team2_team']].isna().any(axis=1)]
    if not missing.empty:
        teams = sorted(set(matchups['team1']).union(set(matchups['team2'])))
        known = sorted(team_table['team'].unique())
        raise ValueError(f'Unknown teams in matchup table. Matchups: {teams}; Known: {known[:20]}...')

    feat['elo_delta'] = feat['team1_elo'] - feat['team2_elo']
    feat['power_delta'] = feat['team1_power_score'] - feat['team2_power_score']
    feat['win_pct_delta'] = feat['team1_win_pct'] - feat['team2_win_pct']
    feat['rank_delta'] = feat['team2_net_rank'] - feat['team1_net_rank']
    feat['seed_delta'] = feat['team2_seed'] - feat['team1_seed']
    return feat

def build_training_frame(results_df: pd.DataFrame, team_table: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs a team table with team statistics & a DataFrame with columns,
    outputting all pairwise features from build_pairwise_features() + 'team1_win',
    where the column will hold 0 if team2 won and 1 if team1 won.
    """
    base = results_df[['season', 'team1', 'team2']].copy()
    feat = build_pairwise_features(base, team_table)
    feat['team1_win'] = (results_df['winner'] == results_df['team1']).astype(int).values
    return feat