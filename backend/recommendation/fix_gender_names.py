#!/usr/bin/env python3
"""Validate or correct names that conflict with profile gender."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

from recommender import DEFAULT_CSV, RecommendationError


# Deliberately non-overlapping pools make validation deterministic for this POC.
MALE_FIRST_NAMES = (
    "Aarif", "Aayan", "Abdullah", "Abrar", "Ahsan", "Akib", "Anik",
    "Arif", "Ashik", "Asif", "Atif", "Fahad", "Faisal", "Fardin",
    "Farhan", "Hasan", "Hridoy", "Imran", "Irfan", "Jahid", "Kawsar",
    "Mahfuz", "Mahin", "Mehedi", "Minhaz", "Nabil", "Nafis", "Naim",
    "Omar", "Rafi", "Rakib", "Rayhan", "Ridwan", "Sabbir", "Sajid",
    "Sakib", "Salman", "Shahriar", "Shawon", "Siam", "Sohan", "Tanjim",
    "Tariq", "Tasin", "Towhid", "Zahid", "Zubair",
)

FEMALE_FIRST_NAMES = (
    "Afsana", "Aisha", "Anika", "Arifa", "Bushra", "Disha", "Elma",
    "Farhana", "Faria", "Fatema", "Habiba", "Ishrat", "Jannatul",
    "Khadija", "Lamisa", "Maliha", "Mariam", "Mehrin", "Mim", "Nabila",
    "Nafisa", "Nusrat", "Raisa", "Rashida", "Rumana", "Sadia", "Sadika",
    "Samia", "Sanjida", "Sharmin", "Sinthia", "Sumaiya", "Tahmina",
    "Tasmia", "Tasnim", "Trisha", "Umme", "Zakia", "Zara", "Zarin",
)

NAME_POOLS = {"Male": MALE_FIRST_NAMES, "Female": FEMALE_FIRST_NAMES}
NORMALIZED_NAME_POOLS = {
    gender: {name.casefold() for name in names} for gender, names in NAME_POOLS.items()
}

# Begum and Akter are female honorific/name markers in this dataset; Miah is a
# male title. Other CSV suffixes are treated as inherited, gender-neutral names.
INVALID_LAST_NAMES = {
    "Male": {"begum", "akter"},
    "Female": {"miah"},
}
NEUTRAL_LAST_NAMES = (
    "Ahmed", "Alam", "Bhuiyan", "Chowdhury", "Haque", "Islam", "Khan",
    "Rahman", "Rashid", "Sarker", "Siddique",
)


def _replacement_first_name(user_id: str, gender: str) -> str:
    pool = NAME_POOLS[gender]
    digest = hashlib.sha256(f"{gender}:{user_id}".encode("utf-8")).digest()
    return pool[int.from_bytes(digest[:8], "big") % len(pool)]


def _replacement_last_name(user_id: str, gender: str) -> str:
    digest = hashlib.sha256(f"surname:{gender}:{user_id}".encode("utf-8")).digest()
    return NEUTRAL_LAST_NAMES[int.from_bytes(digest[:8], "big") % len(NEUTRAL_LAST_NAMES)]


def correct_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    corrected: list[dict[str, str]] = []
    changes: list[dict[str, str]] = []
    for source in rows:
        row = source.copy()
        user_id = row.get("user_id", "").strip()
        gender = row.get("gender", "").strip().title()
        name = row.get("name", "").strip()
        if not user_id:
            raise RecommendationError("Every row must have a user_id")
        if gender not in NAME_POOLS:
            raise RecommendationError(f"Unsupported gender for user {user_id}: {gender or '<missing>'}")
        if not name:
            raise RecommendationError(f"Missing name for user {user_id}")

        parts = name.split()
        first_name = parts[0]
        if first_name.casefold() not in NORMALIZED_NAME_POOLS[gender]:
            replacement = _replacement_first_name(user_id, gender)
            parts[0] = replacement

        if len(parts) >= 2 and parts[-1].casefold() in INVALID_LAST_NAMES[gender]:
            parts[-1] = _replacement_last_name(user_id, gender)

        corrected_name = " ".join(parts)
        if corrected_name != name:
            row["name"] = corrected_name
            changes.append({
                "user_id": user_id,
                "gender": gender,
                "old_name": name,
                "new_name": corrected_name,
            })
        corrected.append(row)
    return corrected, changes


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise RecommendationError(f"CSV file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"user_id", "name", "gender"}.issubset(reader.fieldnames):
            raise RecommendationError("CSV must contain user_id, name, and gender columns")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Report mismatches without changing the CSV")
    mode.add_argument("--write", action="store_true", help="Correct mismatches in the CSV")
    args = parser.parse_args()

    try:
        fieldnames, rows = read_csv(args.csv)
        corrected, changes = correct_rows(rows)
        if args.write and changes:
            write_csv(args.csv, fieldnames, corrected)
    except (RecommendationError, OSError) as exc:
        print(f"Name correction failed: {exc}", file=sys.stderr)
        return 2

    action = "corrected" if args.write else "found"
    print(f"Inspected {len(rows)} profiles; {action} {len(changes)} mismatches; {len(rows) - len(changes)} unchanged.")
    for change in changes[:10]:
        print(
            f"  {change['user_id']}: {change['old_name']} -> {change['new_name']} "
            f"({change['gender']})"
        )
    if len(changes) > 10:
        print(f"  ... and {len(changes) - 10} more")
    return 1 if args.check and changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
