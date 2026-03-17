"""
Stores all of the constants for tuning. 
Includes power-score weights, base ELO, ELO scaling, & logistic regression settings.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PowerConfig:
    win_pct_weight: float = 0.55
    net_rank_weight: float = 0.35
    seed_weight: float = 0.10
    base_elo: float = 1500.0
    elo_scale: float = 400.0


@dataclass(frozen=True)
class ModelConfig:
    random_state: int = 42 # reproducability
    max_iter: int = 1000


POWER_CONFIG = PowerConfig()
MODEL_CONFIG = ModelConfig()

