"""Database adapter for the weighted KNN recommendation model."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from models.profile.profile import Profile
from models.user.user import User
from recommendation.recommender import (
    DEFAULT_ARTIFACTS, INTEREST_COLS, NUMERIC_COLS, REQUIRED_COLUMNS,
    _candidate_is_eligible, _directional_preferences, _interest_tokens,
    _parse_list, _priority_key, _reasons, _text,
    load_runtime_artifacts, transform_profiles,
)
from seed_recommendation_data import demo_user_id


def is_ready() -> bool:
    try:
        load_runtime_artifacts(DEFAULT_ARTIFACTS)
        return True
    except Exception:
        return False


def _query_row(user: User, profile: Profile) -> pd.Series:
    values: dict[str, Any] = {column: None for column in REQUIRED_COLUMNS}
    values.update({
        "user_id": user.id, "name": user.name, "age": user.age,
        "gender": user.gender, "religion": user.religion,
        "preferred_age_min": profile.preferred_age_min or user.preferred_age_from,
        "preferred_age_max": profile.preferred_age_max or user.preferred_age_to,
    })
    for column in Profile.__table__.columns:
        if column.name in values:
            values[column.name] = getattr(profile, column.name)
    for column in REQUIRED_COLUMNS:
        if column in {"user_id", "name", "necessary_preferences", "genetic_conditions"}:
            continue
        if column not in NUMERIC_COLS and not column.startswith("preferred_") or column in {
            "preferred_religion", "preferred_education", "preferred_profession", "preferred_location"
        }:
            values[column] = _text(values[column])
    for column in NUMERIC_COLS + ["preferred_age_min", "preferred_age_max", "preferred_height_min",
                                  "preferred_height_max", "preferred_weight_min", "preferred_weight_max"]:
        values[column] = pd.to_numeric(values[column], errors="coerce")
    values["necessary_preferences"] = _parse_list(values["necessary_preferences"])
    values["genetic_conditions"] = _parse_list(values["genetic_conditions"])
    row = pd.Series(values)
    row["interest_tokens"] = _interest_tokens(row)
    return row


def get_recommendations(current_user_id: str, db: Session, top_n: int = 100) -> Optional[list[dict]]:
    top_n = max(1, min(top_n, 100))
    try:
        artifact, candidates = load_runtime_artifacts(DEFAULT_ARTIFACTS)
    except Exception:
        return None
    user = db.query(User).filter(User.id == current_user_id).first()
    profile = db.query(Profile).filter(Profile.user_id == current_user_id).first()
    if not user or not profile or not profile.is_completed:
        return None
    query = _query_row(user, profile)
    query_frame = pd.DataFrame([query])
    matrix = transform_profiles(query_frame, artifact)
    distances, indices = artifact["knn"].kneighbors(matrix, n_neighbors=len(candidates))
    scored = []
    for distance, index in zip(distances[0], indices[0]):
        candidate = candidates.iloc[index]
        if not _candidate_is_eligible(query, candidate):
            continue
        candidate_id = str(candidate["user_id"])
        db_id = candidate_id if artifact.get("id_source") == "database" else demo_user_id(candidate_id)
        eligible = db.query(User.id).join(Profile, Profile.user_id == User.id).filter(
            User.id == db_id, User.is_deleted == False, User.is_archived == False,
            Profile.is_completed == True,
        ).first()
        if not eligible:
            continue
        similarity = max(0.0, min(1.0, 1.0 - float(distance)))
        a_to_b = _directional_preferences(query, candidate)
        b_to_a = _directional_preferences(candidate, query)
        preference = (a_to_b["score"] + b_to_a["score"]) / 2
        relaxed = set(a_to_b["required_failures"] + b_to_a["required_failures"])
        scored.append({"user_id": db_id, "score": .4 * similarity + .6 * preference,
                       "similarity": similarity, "strict": not relaxed,
                       "reason_tags": _reasons(a_to_b, b_to_a, similarity),
                       "priority_key": _priority_key(
                           a_to_b, b_to_a, .4 * similarity + .6 * preference,
                           similarity, db_id,
                       )})
    scored.sort(key=lambda item: item["priority_key"])
    for item in scored:
        item.pop("priority_key", None)
    return scored[:top_n]
