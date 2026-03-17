import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from .config import MODEL_CONFIG, ModelConfig
from .features import FEATURE_COLUMNS

def fit_matchup_model(train_df, cfg: ModelConfig = MODEL_CONFIG):
    """
    Fitting the model with standardized features through sklearn's StandardScaler()
    + utilizing Logistic Regression for predictions.
    """
    if train_df is None or train_df.empty:
        return None
    y = train_df['team1_win']
    if y.nunique() < 2:
        return None
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('logit', LogisticRegression(max_iter=cfg.max_iter, random_state=cfg.random_state)),
    ])
    model.fit(train_df[FEATURE_COLUMNS], y)
    return model

def fallback_probabilities(feature_df):
    """
    Fallback if historical training data is missing or unusable.
    Applies a logistic-style transform to the 5 deltas, with different weights.
    """
    z = (
        feature_df['elo_delta'] / 80.0
        + feature_df['power_delta'] / 12.0
        + feature_df['rank_delta'] / 18.0
        + feature_df['seed_delta'] / 3.0
        + feature_df['win_pct_delta'] * 4.0
    )
    return 1.0 / (1.0 + np.exp(-z))

def predict_probabilities(feature_df, model=None):
    """
    Predicting the probabilities with fit_matchup_model() & fallback_probabilities()
    """
    if model is None:
        return fallback_probabilities(feature_df).to_numpy()
    return model.predict_proba(feature_df[FEATURE_COLUMNS])[:, 1]