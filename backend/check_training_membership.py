#!/usr/bin/env python3
"""
Inspect which database users are present in the trained recommendation index.

This script loads the already-trained artifacts from backend/ml_artifacts/:
  - preprocess_db.pkl
  - nn_db.pkl
  - user_id_map.json

It then queries the users table and prints which user GUIDs were included in
training, along with basic user details.

Run from the backend directory:
  python check_training_membership.py

Optional flags:
  --trained-only   Show only users that are in the training index
  --missing-only   Show only users that are not in the training index
  --limit N        Limit the number of printed rows
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sqlalchemy import create_engine, text

from config import get_settings


ARTIFACT_DIR = Path(__file__).resolve().parent / "ml_artifacts"
PREPROCESS_PATH = ARTIFACT_DIR / "preprocess_db.pkl"
NN_PATH = ARTIFACT_DIR / "nn_db.pkl"
USER_ID_MAP_PATH = ARTIFACT_DIR / "user_id_map.json"


def build_database_url() -> str:
    settings = get_settings()
    return f"{settings.DATABASE_URL}{settings.DATABASE_NAME}"


def load_training_artifacts() -> dict[str, str]:
    if not PREPROCESS_PATH.exists():
        raise FileNotFoundError(f"Missing artifact: {PREPROCESS_PATH}")
    if not NN_PATH.exists():
        raise FileNotFoundError(f"Missing artifact: {NN_PATH}")
    if not USER_ID_MAP_PATH.exists():
        raise FileNotFoundError(f"Missing artifact: {USER_ID_MAP_PATH}")

    joblib.load(PREPROCESS_PATH)
    joblib.load(NN_PATH)

    with USER_ID_MAP_PATH.open("r", encoding="utf-8") as handle:
        user_id_map = json.load(handle)

    return {str(knn_index): str(user_id) for knn_index, user_id in user_id_map.items()}


def fetch_users():
    engine = create_engine(build_database_url(), pool_pre_ping=True)
    query = text(
        """
        SELECT
            id,
            name,
            email,
            is_deleted,
            created_at
        FROM users
        ORDER BY created_at ASC, id ASC
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

    return rows


def print_report(users, trained_user_ids: set[str], trained_map: dict[str, str], args) -> None:
    matched_users = []
    missing_users = []

    for user in users:
        is_trained = user.id in trained_user_ids
        row = {
            "id": user.id,
            "username": user.name,
            "name": user.name,
            "email": user.email,
            "is_deleted": user.is_deleted,
            "created_at": user.created_at,
            "trained": is_trained,
        }
        if is_trained:
            matched_users.append(row)
        else:
            missing_users.append(row)

    print("=== Training Membership Check ===")
    print(f"Artifact users in training index: {len(trained_user_ids)}")
    print(f"Database users scanned: {len(users)}")
    print(f"Matched users: {len(matched_users)}")
    print(f"Not in training: {len(missing_users)}")
    print()

    if args.trained_only:
        rows_to_print = matched_users
    elif args.missing_only:
        rows_to_print = missing_users
    else:
        rows_to_print = matched_users + missing_users

    if args.limit is not None:
        rows_to_print = rows_to_print[: args.limit]

    for row in rows_to_print:
        status = "TRAINED" if row["trained"] else "NOT TRAINED"
        print(
            f"{status} | guid={row['id']} | username={row['username']} | name={row['name']} | email={row['email']} | deleted={row['is_deleted']}"
        )

    if rows_to_print:
        print()
        print("Legend:")
        print("  TRAINED     = user GUID exists in user_id_map.json")
        print("  NOT TRAINED = user GUID is not present in the trained artifact")


def parse_args():
    parser = argparse.ArgumentParser(description="Check which database users exist in the trained recommendation model.")
    parser.add_argument("--trained-only", action="store_true", help="Show only users included in training")
    parser.add_argument("--missing-only", action="store_true", help="Show only users missing from training")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of printed rows")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.trained_only and args.missing_only:
        raise SystemExit("Use only one of --trained-only or --missing-only.")

    trained_map = load_training_artifacts()
    trained_user_ids = set(trained_map.values())
    users = fetch_users()
    print_report(users, trained_user_ids, trained_map, args)


if __name__ == "__main__":
    main()