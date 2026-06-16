# backend/services/recommendation_service.py
#
# Loads trained KNN artifacts and produces ranked match recommendations
# for a given user using the same scoring logic as the research notebook.

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

ML_DIR = Path(__file__).resolve().parent.parent / "ml_artifacts"

NUMERIC_COLS = ["age"]
CATEGORICAL_COLS = [
    "gender", "religion", "location", "academic_background",
    "profession", "marital_status", "dietary_preference",
    "smoking_habit", "alcohol_consumption"
]
ALL_COLS = NUMERIC_COLS + CATEGORICAL_COLS


# ─────────────────────────────────────────────
# Lazy-load artifacts once on first use
# ─────────────────────────────────────────────
_preprocess = None
_nn = None
_user_id_map: dict = {}       # str(knn_index) -> user_id
_user_index_map: dict = {}    # user_id -> knn_index (int)


def _load_artifacts() -> bool:
    """Load pkl / json artifacts. Returns True if successful."""
    global _preprocess, _nn, _user_id_map, _user_index_map

    print("[ML_SERVICE] Attempting to load artifacts...")
    preprocess_path = ML_DIR / "preprocess_db.pkl"
    nn_path = ML_DIR / "nn_db.pkl"
    map_path = ML_DIR / "user_id_map.json"

    print(f"[ML_SERVICE] Checking paths:")
    print(f"  - preprocess_db.pkl exists: {preprocess_path.exists()}")
    print(f"  - nn_db.pkl exists: {nn_path.exists()}")
    print(f"  - user_id_map.json exists: {map_path.exists()}")

    if not (preprocess_path.exists() and nn_path.exists() and map_path.exists()):
        print("[ML_SERVICE] One or more artifacts missing")
        return False

    try:
        _preprocess = joblib.load(preprocess_path)
        _nn = joblib.load(nn_path)
        with open(map_path, "r") as f:
            _user_id_map = json.load(f)
        # Build reverse map
        _user_index_map = {uid: int(idx) for idx, uid in _user_id_map.items()}
        print(f"[ML_SERVICE] ✅ Artifacts loaded successfully. {len(_user_id_map)} users in index.")
        return True
    except Exception as e:
        print(f"[ML_SERVICE] ❌ Failed to load artifacts: {e}")
        import traceback
        traceback.print_exc()
        return False


def is_ready() -> bool:
    """Returns True if the ML model artifacts are available."""
    if _preprocess is None:
        return _load_artifacts()
    return True


# ─────────────────────────────────────────────
# Preference scoring (mirrors the notebook)
# ─────────────────────────────────────────────
def _preference_score(A: dict, B: dict) -> float:
    score = 0.0

    # Age closeness (±5 years)
    try:
        if abs(float(A.get("age", 0)) - float(B.get("age", 0))) <= 5:
            score += 1.5
    except (TypeError, ValueError):
        pass

    # Same location
    if A.get("location", "unknown") != "unknown" and A.get("location") == B.get("location"):
        score += 1.5

    # Same religion
    if A.get("religion", "unknown") != "unknown" and A.get("religion") == B.get("religion"):
        score += 1.5

    # Same education
    if A.get("academic_background", "unknown") != "unknown" and A.get("academic_background") == B.get("academic_background"):
        score += 1.0

    # Lifestyle alignment
    if A.get("smoking_habit") == B.get("smoking_habit"):
        score += 1.0
    if A.get("alcohol_consumption") == B.get("alcohol_consumption"):
        score += 1.0

    # Dietary preference match
    if A.get("dietary_preference", "unknown") != "unknown" and A.get("dietary_preference") == B.get("dietary_preference"):
        score += 1.0

    return score


def _normalize(val, default="unknown") -> str:
    if val is None:
        return default
    s = str(val).lower().strip()
    return default if s in ("", "nan", "none") else s


# ─────────────────────────────────────────────
# Main recommendation function
# ─────────────────────────────────────────────
def get_recommendations(current_user_id: str, db: Session, top_n: int = 20) -> Optional[List[str]]:
    """
    Returns an ordered list of user_ids (best match first).
    Returns None if ML model is not ready (caller should fall back to browse).
    """
    print(f"[ML_SERVICE] get_recommendations called for user_id: {current_user_id}")
    if not is_ready():
        print("[ML_SERVICE] Model not ready")
        return None

    # Current user must exist in the KNN index
    if current_user_id not in _user_index_map:
        print(f"[ML_SERVICE] User {current_user_id} not found in index")
        return None

    user_index = _user_index_map[current_user_id]
    print(f"[ML_SERVICE] User index: {user_index}")

    # Get up to 500 nearest neighbors (expanded to find opposite-gender matches)
    print(f"[ML_SERVICE] Getting neighbors...")
    distances, indices = _nn.kneighbors(
        _preprocess.transform(_get_user_feature_df(current_user_id, db)),
        n_neighbors=min(500, len(_user_id_map))
    )
    print(f"[ML_SERVICE] Found {len(indices[0])} neighbors")

    candidates = indices[0][1:]       # skip self (index 0)
    cosine_sims = 1 - distances[0][1:]

    # Fetch current user row for scoring
    current_row = _fetch_user_row(current_user_id, db)
    if current_row is None:
        print(f"[ML_SERVICE] Could not fetch current user row")
        return None

    scored = []
    print(f"[ML_SERVICE] Scoring {len(candidates)} candidates...")
    
    # Log current user's gender
    current_gender_raw = current_row.get("gender")
    current_gender_normalized = _normalize(current_row.get("gender"))
    print(f"[ML_SERVICE] Current user gender: raw='{current_gender_raw}' normalized='{current_gender_normalized}'")
    
    # Build list of opposite-gender user indices for filtering
    opposite_gender_indices = set()
    if current_gender_normalized != "unknown":
        # Query DB for all opposite-gender users' indices
        try:
            opposite_gender = "Female" if current_gender_normalized == "male" else "Male"
            result = db.execute(
                text("""
                    SELECT u.id FROM users u
                    JOIN profiles p ON u.id = p.user_id
                    WHERE LOWER(u.gender) = LOWER(:gender)
                    AND u.is_deleted = FALSE
                    AND p.is_completed = TRUE
                """),
                {"gender": opposite_gender}
            )
            opposite_gender_user_ids = {row[0] for row in result.fetchall()}
            
            # Map to KNN indices
            for idx_str, uid in _user_id_map.items():
                if uid in opposite_gender_user_ids:
                    opposite_gender_indices.add(int(idx_str))
            print(f"[ML_SERVICE] Found {len(opposite_gender_indices)} opposite-gender users in index")
        except Exception as e:
            print(f"[ML_SERVICE] Warning: could not pre-filter by gender: {e}")
    
    # Filter candidates to only opposite-gender users if we have that data
    if opposite_gender_indices:
        filtered_candidates = []
        filtered_sims = []
        for idx, sim in zip(candidates, cosine_sims):
            if int(idx) in opposite_gender_indices:
                filtered_candidates.append(idx)
                filtered_sims.append(sim)
        candidates = filtered_candidates
        cosine_sims = filtered_sims
        print(f"[ML_SERVICE] Filtered to {len(candidates)} opposite-gender candidates")
    
    # Track filter statistics
    filter_map_fail = 0      # Failed to map KNN index to user_id or is self
    filter_db_fetch_fail = 0 # Failed to fetch user row from DB
    candidates_passed = 0    # Successfully scored
    
    for knn_idx, sim in zip(candidates, cosine_sims):
        # FILTER 1: Map lookup validation
        candidate_user_id = _user_id_map.get(str(knn_idx))
        if not candidate_user_id or candidate_user_id == current_user_id:
            filter_map_fail += 1
            continue

        # FILTER 2: Database fetch validation
        candidate_row = _fetch_user_row(candidate_user_id, db)
        if candidate_row is None:
            filter_db_fetch_fail += 1
            continue

        # Gender filtering is now done via pre-filtering, so all remaining candidates are opposite-gender
        candidates_passed += 1
        s_ab = _preference_score(current_row, candidate_row)
        s_ba = _preference_score(candidate_row, current_row)
        mutual_score = min(s_ab, s_ba)

        scored.append((candidate_user_id, mutual_score, float(sim)))
    
    # Log filter statistics
    print(f"[ML_SERVICE] Filter breakdown:")
    print(f"  - FILTER 1 (Map lookup): {filter_map_fail} rejected")
    print(f"  - FILTER 2 (DB fetch):   {filter_db_fetch_fail} rejected")
    print(f"  - Candidates passed:     {candidates_passed} scored")

    # Sort by mutual_score desc, then cosine similarity desc
    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
    print(f"[ML_SERVICE] After scoring and filtering: {len(scored)} matches, returning top {top_n}")
    return [uid for uid, _, _ in scored[:top_n]]


def _get_user_feature_df(user_id: str, db: Session) -> pd.DataFrame:
    """Build a single-row feature DataFrame for the given user."""
    row = _fetch_user_row(user_id, db)
    if row is None:
        return pd.DataFrame([{c: "unknown" for c in ALL_COLS}])

    data = {}
    for c in NUMERIC_COLS:
        try:
            data[c] = float(row.get(c) or 0)
        except (TypeError, ValueError):
            data[c] = 0.0
    for c in CATEGORICAL_COLS:
        data[c] = _normalize(row.get(c))

    return pd.DataFrame([data])


def _fetch_user_row(user_id: str, db: Session) -> Optional[dict]:
    """Fetch a single user's features from the DB."""
    result = db.execute(
        text("""
            SELECT u.age, u.gender, u.religion,
                   p.location, p.academic_background, p.profession,
                   p.marital_status, p.dietary_preference,
                   p.smoking_habit, p.alcohol_consumption
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            WHERE u.id = :uid
        """),
        {"uid": user_id}
    ).fetchone()

    if result is None:
        return None

    return {
        "age": result[0],
        "gender": result[1],
        "religion": result[2],
        "location": result[3],
        "academic_background": result[4],
        "profession": result[5],
        "marital_status": result[6],
        "dietary_preference": result[7],
        "smoking_habit": result[8],
        "alcohol_consumption": result[9],
    }
