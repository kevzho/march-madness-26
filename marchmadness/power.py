"""
Converts wins, losses, NET rank, & seed into normalized power score.
Maps the score to ELO. 
"""

import numpy as np
import pandas as pd
from .config import POWER_CONFIG, PowerConfig


def add_power_ratings(team_df: pd.DataFrame, cfg: PowerConfig = POWER_CONFIG) -> pd.DataFrame:
    """
    Computes win_pct, rank_strength, and seed_strength. Then, combines into 
    power_score, centering the score around a field average & converting it into ELO.
    """
    df = team_df.copy()
    games = (df['wins'] + df['losses']).replace(0, np.nan)
    df['win_pct'] = (df['wins'] / games).fillna(0.0)

    max_rank = max(float(df['net_rank'].max()), 2.0)
    df['rank_strength'] = 1.0 - ((df['net_rank'] - 1.0) / (max_rank - 1.0))
    df['seed_strength'] = 1.0 - ((df['seed'] - 1.0) / 15.0)

    df['power_score'] = 100.0 * (
        cfg.win_pct_weight * df['win_pct']
        + cfg.net_rank_weight * df['rank_strength']
        + cfg.seed_weight * df['seed_strength']
    )

    centered_power = df['power_score'] - df['power_score'].mean()
    df['elo'] = cfg.base_elo + centered_power * (cfg.elo_scale / 100.0)

    ordered_cols = [
        'season', 'team', 'region', 'seed', 'wins', 'losses', 'win_pct',
        'net_rank', 'rank_strength', 'seed_strength', 'power_score', 'elo'
    ]
    cols = [c for c in ordered_cols if c in df.columns] + [c for c in df.columns if c not in ordered_cols]
    return df[cols].sort_values('elo', ascending=False).reset_index(drop=True)

