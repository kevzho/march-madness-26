"""
Sets up CLI for users to run the program with different input files & options.
"""

import argparse
from .pipeline import run_pipeline


def build_parser():
    """Argument parser for cmd-line args."""
    parser = argparse.ArgumentParser(description='March Madness Elo pipeline')
    parser.add_argument('--teams', required=True, help='Current team snapshot CSV')
    parser.add_argument('--bracket', required=True, help='Bracket slot CSV')
    parser.add_argument('--out', default='outputs', help='Output directory')
    parser.add_argument('--hist-teams', default=None, help='Historical team snapshots CSV')
    parser.add_argument('--hist-results', default=None, help='Historical tournament results CSV')
    parser.add_argument('--current-season', default=None, type=int, help='Current season year (prevents training on in-progress labels)')
    parser.add_argument('--drop-2021', action='store_true', help='Exclude 2021 from supervised training splits')
    parser.add_argument('--eval', default=None, choices=['fixed', 'rolling'], help='Run season-based evaluation on historical training data')
    return parser


def main():
    """Main entry point that parses cmd-line args & calls the pipeline."""
    args = build_parser().parse_args()
    run_pipeline(
        current_team_snapshot_path=args.teams,
        bracket_slots_path=args.bracket,
        output_dir=args.out,
        historical_team_snapshot_path=args.hist_teams,
        historical_tournament_results_path=args.hist_results,
        current_season=args.current_season,
        drop_2021=args.drop_2021,
        eval_scheme=args.eval,
    )


if __name__ == '__main__':
    main()
