"""
Loads CSVs
Validates required columns
Normalizes names of teams
Parses record
Creates output folders
"""

from pathlib import Path
import pandas as pd

# just in case of mixups
ALIASES = {
    "St John's": "Saint John's",
    "SJU": "Saint John's",
    "Michigan St": "Michigan State",
    "UConn": "Connecticut",
    "CA Baptist": "California Baptist",
    "N Dakota St": "North Dakota State",
    "Miami": "Miami (FL)",
}

def normalize_team_name(value):
    """
    Normalizes team name. 
    Checks for empty names, strips extra whitespace
    for "_" character, and assigns aliases for organization.
    """
    if pd.isna(value):
        return value
    value = str(value).strip()
    if isinstance(value, str) and "_" in value:
        return value
    return ALIASES.get(value, value)

def _parse_record(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts win/loss numbers from a string column 
    & creates separate numeric columns for wins & losses.
    """
    if 'record' in df.columns and not {'wins', 'losses'}.issubset(df.columns):
        wl = df['record'].astype(str).str.extract(r'(?P<wins>\d+)-(?P<losses>\d+)').astype(float)
        df = df.copy()
        df['wins'] = wl['wins']
        df['losses'] = wl['losses']
    return df

def load_team_snapshots(path) -> pd.DataFrame:
    """
    Loads CSV with required columns. Returns DataFrame with normalized columns.
    """
    df = pd.read_csv(Path(path))
    df.columns = [c.strip().lower() for c in df.columns]
    df = _parse_record(df)
    df['team'] = df['team'].map(normalize_team_name)
    required = {'team', 'wins', 'losses', 'net_rank', 'seed'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing team snapshot columns: {sorted(missing)}')
    if 'season' in df.columns:
        df['season'] = df['season'].astype(int)
    for col in ['wins', 'losses', 'net_rank', 'seed']:
        df[col] = pd.to_numeric(df[col])
    return df

def load_tournament_results(path) -> pd.DataFrame:
    """
    Loads actual tournament game results.
    Learns from past NCAA tournament outcomes (for historically supervised ML).
    """
    df = pd.read_csv(Path(path))
    df.columns = [c.strip().lower() for c in df.columns]
    required = {'season', 'team1', 'team2', 'winner'}
    missing = required - set(df.columns)
    # fallback
    if missing:
        raise ValueError(f'Missing tournament result columns: {sorted(missing)}')
    for col in ['team1', 'team2', 'winner']:
        # mapping to normalized names for organization
        df[col] = df[col].map(normalize_team_name)
    df['season'] = df['season'].astype(int)
    return df

def load_bracket_slots(path) -> pd.DataFrame:
    """
    Loads CSV defining the bracket layout. 
    Contains required columns, returning a sorted DataFrame by round & slot.
    """
    df = pd.read_csv(Path(path))
    df.columns = [c.strip().lower() for c in df.columns]
    required = {'slot', 'round_name', 'round_order', 'left', 'right'}
    missing = required - set(df.columns)
    # fallback
    if missing:
        raise ValueError(f'Missing bracket columns: {sorted(missing)}')
    df['slot'] = df['slot'].astype(str)
    # mapping to normalized names for organization
    df['left'] = df['left'].map(normalize_team_name)
    df['right'] = df['right'].map(normalize_team_name)
    df['round_order'] = pd.to_numeric(df['round_order'])
    return df.sort_values(['round_order', 'slot']).reset_index(drop=True)

def ensure_dir(path):
    """
    Creates a directory & any necessary parent directories for outputs.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path