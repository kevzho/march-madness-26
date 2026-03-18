from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from .config import MODEL_CONFIG, ModelConfig
from .model import fit_matchup_model, predict_probabilities


@dataclass(frozen=True)
class SplitMetrics:
    seasons: list[int]
    games: int
    log_loss: float | None
    brier: float | None
    auc: float | None
    accuracy: float | None


def _as_int_seasons(values: Iterable) -> list[int]:
    out: list[int] = []
    for v in values:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        out.append(int(v))
    return sorted(set(out))


def _metrics(y_true: np.ndarray, y_prob: np.ndarray, seasons: list[int]) -> SplitMetrics:
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    games = int(y_true.shape[0])

    if games == 0:
        return SplitMetrics(seasons=seasons, games=0, log_loss=None, brier=None, auc=None, accuracy=None)

    ll = float(log_loss(y_true, y_prob, labels=[0, 1]))
    brier = float(brier_score_loss(y_true, y_prob))
    acc = float(accuracy_score(y_true, (y_prob >= 0.5).astype(int)))

    # AUC is undefined if only one class appears in y_true
    try:
        auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        auc = None

    return SplitMetrics(seasons=seasons, games=games, log_loss=ll, brier=brier, auc=auc, accuracy=acc)


def evaluate_by_season_split(
    train_df,
    *,
    train_seasons: list[int],
    eval_seasons: list[int],
    cfg: ModelConfig = MODEL_CONFIG,
) -> SplitMetrics:
    """
    Train on all games whose `season` is in `train_seasons`, evaluate on `eval_seasons`.
    This prevents leakage from mixing games within a season across splits.
    """
    if train_df is None or train_df.empty:
        return SplitMetrics(seasons=eval_seasons, games=0, log_loss=None, brier=None, auc=None, accuracy=None)

    df = train_df.copy()
    if "season" not in df.columns:
        raise ValueError("Training frame is missing required column: season")

    train_mask = df["season"].astype(int).isin(set(train_seasons))
    eval_mask = df["season"].astype(int).isin(set(eval_seasons))
    train_part = df.loc[train_mask]
    eval_part = df.loc[eval_mask]

    model = fit_matchup_model(train_part, cfg=cfg)
    if model is None:
        return SplitMetrics(seasons=eval_seasons, games=int(eval_part.shape[0]), log_loss=None, brier=None, auc=None, accuracy=None)

    y_true = eval_part["team1_win"].to_numpy()
    y_prob = predict_probabilities(eval_part, model=model)
    return _metrics(y_true, y_prob, seasons=eval_seasons)


def run_season_evaluation(
    train_df,
    *,
    scheme: str = "fixed",
    cfg: ModelConfig = MODEL_CONFIG,
) -> dict:
    """
    Convenience evaluation runner with sensible defaults.

    - fixed: Train 2008–2022, validate 2023–2024, test 2025
    - rolling: Rolling 1-year-ahead validations (skips 2020), final test on 2025
    """
    if train_df is None or train_df.empty:
        return {"scheme": scheme, "available_seasons": [], "error": "no_training_data"}

    available = _as_int_seasons(train_df["season"].unique())
    available_set = set(available)

    def intersect(seasons: list[int]) -> list[int]:
        return [s for s in seasons if s in available_set]

    if scheme == "fixed":
        train_seasons = intersect(list(range(2008, 2023)))
        val_seasons = intersect([2023, 2024])
        test_seasons = intersect([2025])

        val_metrics = evaluate_by_season_split(
            train_df,
            train_seasons=train_seasons,
            eval_seasons=val_seasons,
            cfg=cfg,
        )
        test_metrics = evaluate_by_season_split(
            train_df,
            train_seasons=sorted(set(train_seasons + val_seasons)),
            eval_seasons=test_seasons,
            cfg=cfg,
        )
        return {
            "scheme": "fixed",
            "available_seasons": available,
            "train_seasons": train_seasons,
            "val": val_metrics.__dict__,
            "test": test_metrics.__dict__,
        }

    if scheme == "rolling":
        val_years = intersect([2019, 2021, 2022, 2023, 2024])
        test_years = intersect([2025])
        folds = []

        for y in val_years:
            train_seasons = [s for s in available if s < y]
            m = evaluate_by_season_split(train_df, train_seasons=train_seasons, eval_seasons=[y], cfg=cfg)
            folds.append(m.__dict__)

        test_metrics = None
        if test_years:
            train_seasons = [s for s in available if s < test_years[0]]
            test_metrics = evaluate_by_season_split(
                train_df,
                train_seasons=train_seasons,
                eval_seasons=test_years,
                cfg=cfg,
            ).__dict__

        return {
            "scheme": "rolling",
            "available_seasons": available,
            "folds": folds,
            "test": test_metrics,
        }

    raise ValueError(f"Unknown evaluation scheme: {scheme!r} (expected 'fixed' or 'rolling')")

