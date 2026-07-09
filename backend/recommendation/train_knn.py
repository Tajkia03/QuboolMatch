#!/usr/bin/env python3
"""Train the standalone CSV recommendation model."""

import argparse
import json
import sys
from pathlib import Path

from recommender import DEFAULT_ARTIFACTS, DEFAULT_CSV, RecommendationError, train


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS)
    args = parser.parse_args()
    try:
        metadata = train(args.csv, args.artifacts_dir)
    except (RecommendationError, OSError) as exc:
        print(f"Training failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(metadata, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
