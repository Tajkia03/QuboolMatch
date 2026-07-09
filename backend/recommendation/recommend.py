#!/usr/bin/env python3
"""Recommend matches for an existing user in the trained CSV dataset."""

import argparse
import json
import sys
from pathlib import Path

from recommender import DEFAULT_ARTIFACTS, RecommendationError, recommend


def _print_human(result: dict) -> None:
    query = result["query_user"]
    print(f"Recommended matches for {query['name']} ({query['user_id']}):")
    if not result["matches"]:
        print("No eligible matches found.")
        return
    for match in result["matches"]:
        status = "strict" if match["strict_compatible"] else "relaxed"
        print(
            f"{match['rank']}. {match['name']} ({match['user_id']}) | "
            f"score={match['score']:.4f} | {match['age']}, {match['location']}, "
            f"{match['profession']} | {status}"
        )
        print(f"   Reasons: {', '.join(match['reason_tags'])}")
        if match["relaxed_preferences"]:
            print(f"   Relaxed: {', '.join(match['relaxed_preferences'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        result = recommend(args.user_id, args.top_k, args.artifacts_dir)
    except (RecommendationError, OSError) as exc:
        print(f"Recommendation failed: {exc}", file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
