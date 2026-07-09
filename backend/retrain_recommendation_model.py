"""Manually request and run database-backed recommendation training."""
import argparse

from recommendation.database_training import run_database_training
from services.retraining_coordinator import request_retraining


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.background:
        request_retraining()
        print("[TRAIN] Manual retraining requested")
    return 0 if run_database_training() else 2


if __name__ == "__main__":
    raise SystemExit(main())
