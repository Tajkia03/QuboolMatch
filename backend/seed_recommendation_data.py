"""Import bundled recommendation profiles as login-enabled demo accounts."""
from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import Any

import bcrypt
import pandas as pd

from database import SessionLocal
from models.profile.profile import Profile
from models.user.user import User

CSV_PATH = Path(__file__).parent / "recommendation" / "quboolmatch_diverse_500_profiles.csv"
DEFAULT_PASSWORD = "seed123"
DEMO_NAMESPACE = uuid.UUID("e2dfaf0e-c6e4-4ba5-a6f2-f192d0fc793e")
USER_FIELDS = {"name", "email", "gender", "age", "religion"}
BOOL_FIELDS = {"willing_to_relocate", "lifestyle_pref_dietary_match", "is_completed"}
PROFILE_FIELDS = {c.name for c in Profile.__table__.columns} - {
    "id", "user_id", "created_at", "updated_at", "identity_verified"
}


def demo_user_id(source_id: Any) -> str:
    return str(uuid.uuid5(DEMO_NAMESPACE, str(source_id).strip()))


def clean(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def seed(csv_path: Path = CSV_PATH, *, allow_production: bool = False, progress_every: int = 25) -> int:
    if os.getenv("ENV", "dev").lower() not in {"dev", "test"} and not allow_production:
        raise RuntimeError("Demo seeding is disabled outside dev/test; pass --allow-production explicitly")
    print(f"[seed] Environment: {os.getenv('ENV', 'dev')}")
    print(f"[seed] Reading: {csv_path.resolve()}")
    frame = pd.read_csv(csv_path)
    total = len(frame)
    if total == 0:
        raise RuntimeError("The recommendation CSV is empty")
    print(f"[seed] Loaded {total} rows; validating and importing in one transaction")
    password_hash = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
    session = SessionLocal()
    created_users = updated_users = created_profiles = updated_profiles = 0
    try:
        for position, (_, row) in enumerate(frame.iterrows(), start=1):
            source = {key: clean(value) for key, value in row.to_dict().items()}
            email = str(source["email"]).strip().lower()
            user = session.query(User).filter(User.email == email).first()
            if user and not user.is_demo:
                raise RuntimeError(f"Refusing to overwrite non-demo account: {email}")
            if user is None:
                user = User(name=str(source["name"]), email=email, password=DEFAULT_PASSWORD,
                            gender=str(source["gender"]), nid=f"DEMO-{source['user_id']}",
                            age=int(source["age"]), religion=source.get("religion"),
                            hashed_password=password_hash)
                user.id = demo_user_id(source["user_id"])
                session.add(user)
                # User/Profile models do not declare an ORM relationship, so force
                # the parent INSERT before adding its foreign-key dependent profile.
                session.flush([user])
                created_users += 1
            else:
                updated_users += 1
            for field in USER_FIELDS:
                if source.get(field) is not None:
                    setattr(user, field, int(source[field]) if field == "age" else source[field])
            user.hashed_password = password_hash
            user.nid = f"DEMO-{source['user_id']}"
            user.is_demo, user.is_admin, user.is_deleted, user.is_archived = True, False, False, False
            user.identity_verified, user.verification_status = True, "verified"
            profile = session.query(Profile).filter(Profile.user_id == user.id).first()
            if profile is None:
                profile = Profile(user_id=user.id)
                session.add(profile)
                created_profiles += 1
            else:
                updated_profiles += 1
            for field in PROFILE_FIELDS:
                if field in source:
                    setattr(profile, field, as_bool(source[field]) if field in BOOL_FIELDS else source[field])
            profile.identity_verified, profile.is_completed = True, True
            if position == 1 or position % progress_every == 0 or position == total:
                print(
                    f"[seed] {position:>3}/{total} ({position / total:>6.1%}) "
                    f"users +{created_users}/~{updated_users}, "
                    f"profiles +{created_profiles}/~{updated_profiles}",
                    flush=True,
                )
        print("[seed] Flushing profiles and committing transaction...")
        session.commit()
        print("[seed] Commit complete")
        from services.retraining_coordinator import request_retraining
        request_retraining()
        print("[seed] Recommendation retraining queued")
        return len(frame)
    except Exception as exc:
        session.rollback()
        print(f"[seed] ERROR: {exc}")
        print("[seed] Transaction rolled back; no partial import was kept")
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--progress-every", type=int, default=25,
                        help="print progress after this many rows (default: 25)")
    args = parser.parse_args()
    if args.progress_every < 1:
        parser.error("--progress-every must be at least 1")
    count = seed(args.csv, allow_production=args.allow_production,
                 progress_every=args.progress_every)
    print(f"Imported {count} demo users and profiles")
    print(f"Shared demo password: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
