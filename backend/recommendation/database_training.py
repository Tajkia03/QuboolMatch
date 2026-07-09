"""Train and atomically publish recommendation artifacts from PostgreSQL."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text

from database import engine
from recommendation.recommender import (
    DEFAULT_ARTIFACTS, FEATURE_WEIGHTS, MODEL_VERSION, RecommendationError,
    fit_model, normalize_profiles,
)

ADVISORY_LOCK_ID = 714_202_606
VERSIONS_DIR = DEFAULT_ARTIFACTS / "versions"
ACTIVE_POINTER = DEFAULT_ARTIFACTS / "active.json"
RETAINED_VERSIONS = 5

PROFILE_COLUMNS = [
    "location", "academic_background", "profession", "marital_status", "blood_group",
    "height", "weight", "dietary_preference", "smoking_habit", "alcohol_consumption",
    "willing_to_relocate", "living_with_in_laws", "career_support_expectations",
    "hobbies", "interests", "preferred_height_min", "preferred_height_max",
    "preferred_weight_min", "preferred_weight_max", "preferred_religion",
    "preferred_education", "preferred_profession", "preferred_location", "specific_location",
    "lifestyle_pref_smoking", "lifestyle_pref_alcohol", "lifestyle_pref_dietary_match",
    "necessary_preferences", "medical_history", "overall_health_status",
    "long_term_condition", "long_term_condition_description", "fertility_awareness",
    "disability", "disability_description", "chronic_illness", "genetic_conditions",
]


def fetch_database_profiles(connection) -> pd.DataFrame:
    profile_select = ",\n            ".join(f"p.{column}" for column in PROFILE_COLUMNS)
    query = text(f"""
        SELECT
            u.id AS user_id, u.name, u.age, u.gender, u.religion,
            COALESCE(p.preferred_age_min, u.preferred_age_from) AS preferred_age_min,
            COALESCE(p.preferred_age_max, u.preferred_age_to) AS preferred_age_max,
            {profile_select}
        FROM users u
        JOIN profiles p ON p.user_id = u.id
        WHERE p.is_completed = TRUE
          AND u.is_deleted = FALSE
          AND u.is_archived = FALSE
    """)
    return pd.read_sql_query(query, connection)


def _publish(profiles: pd.DataFrame, generation: int) -> Path:
    normalized = normalize_profiles(profiles)
    if len(normalized) < 2:
        raise RecommendationError("At least two eligible completed profiles are required")
    artifact, matrix = fit_model(normalized)
    artifact["id_source"] = "database"

    DEFAULT_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    version = f"g{generation}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    staging = DEFAULT_ARTIFACTS / f".staging-{uuid.uuid4().hex}"
    final = VERSIONS_DIR / version
    staging.mkdir()
    try:
        joblib.dump(artifact, staging / "knn_model.joblib")
        joblib.dump(normalized, staging / "profiles.joblib")
        metadata = {
            "model_version": MODEL_VERSION,
            "generation": generation,
            "profile_count": len(normalized),
            "feature_count": matrix.shape[1],
            "feature_weights": FEATURE_WEIGHTS,
            "source": "database",
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        (staging / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

        # Validate every file before publishing the version.
        loaded_artifact = joblib.load(staging / "knn_model.joblib")
        loaded_profiles = joblib.load(staging / "profiles.joblib")
        if loaded_artifact.get("model_version") != MODEL_VERSION or len(loaded_profiles) != len(normalized):
            raise RecommendationError("Generated artifact validation failed")

        os.replace(staging, final)
        pointer_tmp = DEFAULT_ARTIFACTS / "active.json.tmp"
        pointer_tmp.write_text(json.dumps({"version": version, "generation": generation}) + "\n")
        os.replace(pointer_tmp, ACTIVE_POINTER)
        old_versions = sorted(
            (path for path in VERSIONS_DIR.iterdir() if path.is_dir() and path != final),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old_version in old_versions[RETAINED_VERSIONS - 1:]:
            shutil.rmtree(old_version, ignore_errors=True)
        return final
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def run_database_training() -> bool:
    """Run one requested generation, returning False when another trainer owns the lock."""
    with engine.connect() as connection:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": ADVISORY_LOCK_ID}
        ).scalar()
        connection.commit()
        if not acquired:
            print("[TRAIN] Another recommendation trainer is already running")
            return False

        generation = None
        try:
            row = connection.execute(text("""
                SELECT requested_generation, completed_generation
                FROM recommendation_training_state WHERE id = 1
            """)).mappings().one()
            generation = max(row["requested_generation"], row["completed_generation"] + 1)
            connection.execute(text("""
                UPDATE recommendation_training_state
                SET status = 'running', started_at = NOW(), finished_at = NULL,
                    last_error = NULL, updated_at = NOW()
                WHERE id = 1
            """))
            connection.commit()

            print(f"[TRAIN] Fetching eligible database profiles for generation {generation}")
            profiles = fetch_database_profiles(connection)
            connection.commit()
            print(f"[TRAIN] Training with {len(profiles)} eligible profiles")
            published = _publish(profiles, generation)

            connection.execute(text("""
                UPDATE recommendation_training_state
                SET completed_generation = :generation,
                    status = CASE WHEN requested_generation > :generation
                                  THEN 'pending' ELSE 'idle' END,
                    finished_at = NOW(), updated_at = NOW(), last_error = NULL
                WHERE id = 1
            """), {"generation": generation})
            connection.commit()
            print(f"[TRAIN] Published generation {generation}: {published}")
            return True
        except Exception as exc:
            connection.rollback()
            connection.execute(text("""
                UPDATE recommendation_training_state
                SET status = 'failed', finished_at = NOW(), updated_at = NOW(),
                    last_error = :error
                WHERE id = 1
            """), {"error": str(exc)[:4000]})
            connection.commit()
            print(f"[TRAIN] Failed: {exc}")
            raise
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": ADVISORY_LOCK_ID}
            )
            connection.commit()
