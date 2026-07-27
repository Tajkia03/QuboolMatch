"""Shared training and ranking logic for the standalone recommendation POC."""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder, StandardScaler, normalize


MODEL_VERSION = 1
DEFAULT_CSV = Path(__file__).with_name("quboolmatch_diverse_500_profiles.csv")
DEFAULT_ARTIFACTS = Path(__file__).with_name("artifacts")

NUMERIC_COLS = ["age", "height", "weight"]
BACKGROUND_COLS = [
    "religion", "location", "academic_background", "profession",
    "marital_status", "blood_group",
]
LIFESTYLE_COLS = ["dietary_preference", "smoking_habit", "alcohol_consumption"]
HOUSEHOLD_COLS = [
    "willing_to_relocate", "living_with_in_laws", "career_support_expectations",
]
INTEREST_COLS = ["hobbies", "interests"]
SENSITIVE_TEXT_COLS = [
    "medical_history", "overall_health_status", "long_term_condition",
    "long_term_condition_description", "fertility_awareness", "disability",
    "disability_description", "chronic_illness",
]
FEATURE_WEIGHTS = {
    "numeric": 0.20,
    "background": 0.30,
    "lifestyle": 0.20,
    "household": 0.15,
    "interests": 0.15,
}

REQUIRED_COLUMNS = {
    "user_id", "name", "gender", *NUMERIC_COLS, *BACKGROUND_COLS,
    *LIFESTYLE_COLS, *HOUSEHOLD_COLS, *INTEREST_COLS,
    "preferred_age_min", "preferred_age_max",
    "preferred_height_min", "preferred_height_max",
    "preferred_weight_min", "preferred_weight_max",
    "preferred_religion", "preferred_education", "preferred_profession",
    "preferred_location", "specific_location", "lifestyle_pref_smoking",
    "lifestyle_pref_alcohol", "lifestyle_pref_dietary_match",
    "necessary_preferences",
    *SENSITIVE_TEXT_COLS, "genetic_conditions",
}

NO_PREFERENCE = {"", "unknown", "none", "nopreference", "anywhere"}
NECESSARY_KEYS = {"age", "height", "religion", "education", "location", "lifestyle"}

PROFESSION_GROUPS = {
    "accountant": "accounting", "architect": "architecture", "banker": "banking",
    "business owner": "entrepreneurship", "civil engineer": "engineering",
    "doctor": "medical", "freelancer": "media", "government officer": "government service",
    "lawyer": "law", "marketing executive": "business", "ngo professional": "ngo",
    "nurse": "medical", "pharmacist": "pharmacy", "software engineer": "it",
    "teacher": "education", "university lecturer": "research",
}


class RecommendationError(ValueError):
    """Raised for expected input and artifact errors."""


def _text(value: Any) -> str:
    if value is None:
        return "unknown"
    if not isinstance(value, (list, tuple, set, dict, np.ndarray)) and pd.isna(value):
        return "unknown"
    result = str(value).strip().lower()
    return "unknown" if result in {"", "nan", "none"} else result


def _bool(value: Any) -> bool:
    return _text(value) in {"true", "1", "yes"}


def _parse_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item) != "unknown"]
    if value is None or pd.isna(value) or not str(value).strip():
        return []
    try:
        parsed = ast.literal_eval(str(value))
    except (SyntaxError, ValueError):
        parsed = []
    if not isinstance(parsed, list):
        return []
    return [_text(item) for item in parsed if _text(item) != "unknown"]


def _interest_tokens(row: pd.Series) -> list[str]:
    tokens: set[str] = set()
    for column in INTEREST_COLS:
        value = row[column]
        if value is None or pd.isna(value):
            continue
        tokens.update(_text(item) for item in str(value).split(",") if item.strip())
    tokens.discard("unknown")
    return sorted(tokens)


def load_profiles(csv_path: Path | str) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.is_file():
        raise RecommendationError(f"CSV file not found: {path}")
    profiles = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS - set(profiles.columns))
    if missing:
        raise RecommendationError(f"CSV is missing required columns: {', '.join(missing)}")
    if profiles.empty:
        raise RecommendationError("CSV contains no profiles")
    if profiles["user_id"].isna().any() or profiles["user_id"].duplicated().any():
        raise RecommendationError("user_id values must be present and unique")

    return normalize_profiles(profiles)


def normalize_profiles(profiles: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize profiles from CSV or database rows."""
    missing = sorted(REQUIRED_COLUMNS - set(profiles.columns))
    if missing:
        raise RecommendationError(f"Profiles are missing required columns: {', '.join(missing)}")
    if profiles.empty:
        raise RecommendationError("Profiles contain no rows")
    if profiles["user_id"].isna().any() or profiles["user_id"].duplicated().any():
        raise RecommendationError("user_id values must be present and unique")

    result = profiles.copy()
    result["user_id"] = result["user_id"].astype(str)
    for column in NUMERIC_COLS + [
        "preferred_age_min", "preferred_age_max", "preferred_height_min",
        "preferred_height_max", "preferred_weight_min", "preferred_weight_max",
    ]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    for column in NUMERIC_COLS:
        if result[column].isna().all():
            raise RecommendationError(f"Numeric column has no usable values: {column}")
        result[column] = result[column].fillna(result[column].median())
    for column in REQUIRED_COLUMNS - set(NUMERIC_COLS) - {
        "preferred_age_min", "preferred_age_max", "preferred_height_min",
        "preferred_height_max", "preferred_weight_min", "preferred_weight_max",
    }:
        if column not in {"user_id", "name", "necessary_preferences"}:
            result[column] = result[column].map(_text)
    result["name"] = result["name"].fillna("Unknown").astype(str).str.strip()
    result["necessary_preferences"] = result["necessary_preferences"].map(_parse_list)
    result["genetic_conditions"] = result["genetic_conditions"].map(_parse_list)
    result["interest_tokens"] = result.apply(_interest_tokens, axis=1)
    return result


def _new_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # scikit-learn < 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _weighted_block(matrix: np.ndarray, weight: float) -> np.ndarray:
    if matrix.shape[1] == 0:
        return matrix
    return normalize(matrix, norm="l2") * math.sqrt(weight)


def fit_model(profiles: pd.DataFrame) -> tuple[dict[str, Any], np.ndarray]:
    scaler = StandardScaler()
    encoders = {
        "background": _new_one_hot_encoder(),
        "lifestyle": _new_one_hot_encoder(),
        "household": _new_one_hot_encoder(),
    }
    interests = MultiLabelBinarizer()
    blocks = [
        _weighted_block(scaler.fit_transform(profiles[NUMERIC_COLS]), FEATURE_WEIGHTS["numeric"]),
        _weighted_block(encoders["background"].fit_transform(profiles[BACKGROUND_COLS]), FEATURE_WEIGHTS["background"]),
        _weighted_block(encoders["lifestyle"].fit_transform(profiles[LIFESTYLE_COLS]), FEATURE_WEIGHTS["lifestyle"]),
        _weighted_block(encoders["household"].fit_transform(profiles[HOUSEHOLD_COLS]), FEATURE_WEIGHTS["household"]),
        _weighted_block(interests.fit_transform(profiles["interest_tokens"]), FEATURE_WEIGHTS["interests"]),
    ]
    matrix = normalize(np.hstack(blocks), norm="l2")
    if not np.isfinite(matrix).all():
        raise RecommendationError("Feature matrix contains non-finite values")
    knn = NearestNeighbors(metric="cosine", algorithm="brute")
    knn.fit(matrix)
    artifact = {
        "model_version": MODEL_VERSION,
        "feature_weights": FEATURE_WEIGHTS,
        "scaler": scaler,
        "encoders": encoders,
        "interests": interests,
        "knn": knn,
        "feature_count": int(matrix.shape[1]),
        "profile_count": int(len(profiles)),
    }
    return artifact, matrix


def transform_profiles(profiles: pd.DataFrame, artifact: dict[str, Any]) -> np.ndarray:
    encoders = artifact["encoders"]
    blocks = [
        _weighted_block(artifact["scaler"].transform(profiles[NUMERIC_COLS]), FEATURE_WEIGHTS["numeric"]),
        _weighted_block(encoders["background"].transform(profiles[BACKGROUND_COLS]), FEATURE_WEIGHTS["background"]),
        _weighted_block(encoders["lifestyle"].transform(profiles[LIFESTYLE_COLS]), FEATURE_WEIGHTS["lifestyle"]),
        _weighted_block(encoders["household"].transform(profiles[HOUSEHOLD_COLS]), FEATURE_WEIGHTS["household"]),
        _weighted_block(artifact["interests"].transform(profiles["interest_tokens"]), FEATURE_WEIGHTS["interests"]),
    ]
    return normalize(np.hstack(blocks), norm="l2")


def train(csv_path: Path | str, artifacts_dir: Path | str) -> dict[str, Any]:
    profiles = load_profiles(csv_path)
    artifact, matrix = fit_model(profiles)
    output = Path(artifacts_dir)
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output / "knn_model.joblib")
    joblib.dump(profiles, output / "profiles.joblib")
    metadata = {
        "model_version": MODEL_VERSION,
        "profile_count": len(profiles),
        "feature_count": matrix.shape[1],
        "feature_weights": FEATURE_WEIGHTS,
        "source_csv": str(Path(csv_path).resolve()),
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    return metadata


def load_artifacts(artifacts_dir: Path | str) -> tuple[dict[str, Any], pd.DataFrame]:
    path = Path(artifacts_dir)
    model_path, profiles_path = path / "knn_model.joblib", path / "profiles.joblib"
    if not model_path.is_file() or not profiles_path.is_file():
        raise RecommendationError(f"Artifacts not found in {path}; run train_knn.py first")
    artifact = joblib.load(model_path)
    profiles = joblib.load(profiles_path)
    if artifact.get("model_version") != MODEL_VERSION:
        raise RecommendationError("Artifact version is incompatible; retrain the model")
    return artifact, profiles


def load_runtime_artifacts(artifacts_dir: Path | str = DEFAULT_ARTIFACTS) -> tuple[dict[str, Any], pd.DataFrame]:
    """Load the atomically selected DB model, or the tracked bootstrap model."""
    root = Path(artifacts_dir)
    pointer = root / "active.json"
    if pointer.is_file():
        try:
            selected = json.loads(pointer.read_text(encoding="utf-8"))["version"]
            version_dir = root / "versions" / selected
            return load_artifacts(version_dir)
        except (KeyError, json.JSONDecodeError, OSError, RecommendationError):
            # A bad runtime pointer must not take down recommendations.
            pass
    return load_artifacts(root)


def _education_group(value: Any) -> str:
    text = _text(value)
    if "phd" in text or "doctorate" in text:
        return "doctorate"
    if text.startswith("msc") or text.startswith("mba"):
        return "masters"
    if text.startswith(("ba", "bba", "bsc", "llb", "mbbs")):
        return "bachelors"
    return "highschool"


def _range_match(candidate: pd.Series, owner: pd.Series, field: str) -> bool | None:
    low, high = owner.get(f"preferred_{field}_min"), owner.get(f"preferred_{field}_max")
    value = candidate.get(field)
    if pd.isna(low) or pd.isna(high) or pd.isna(value):
        return None
    return float(low) <= float(value) <= float(high)


def _category_match(candidate_value: Any, preference: Any) -> bool | None:
    preference = _text(preference)
    if preference in NO_PREFERENCE:
        return None
    return _text(candidate_value) == preference


def _location_match(candidate: pd.Series, owner: pd.Series) -> bool | None:
    preference = _text(owner["preferred_location"])
    if preference in {"anywhere", "samecountry"}:
        return None
    if preference == "samecity":
        return candidate["location"] == owner["location"]
    if preference == "specific":
        return candidate["location"] == owner["specific_location"]
    return None


def _lifestyle_match(candidate: pd.Series, owner: pd.Series) -> tuple[bool | None, str]:
    checks: list[bool] = []
    smoking = _text(owner["lifestyle_pref_smoking"])
    if smoking not in NO_PREFERENCE:
        checks.append(_bool(candidate["smoking_habit"]) == (smoking == "occasional"))
    alcohol = _text(owner["lifestyle_pref_alcohol"])
    if alcohol not in NO_PREFERENCE:
        checks.append(_bool(candidate["alcohol_consumption"]) == (alcohol == "occasional"))
    if _bool(owner["lifestyle_pref_dietary_match"]):
        checks.append(candidate["dietary_preference"] == owner["dietary_preference"])
    if not checks:
        return None, "lifestyle preference neutral"
    return all(checks), "lifestyle preference matched" if all(checks) else "lifestyle preference differs"


def _directional_preferences(owner: pd.Series, candidate: pd.Series) -> dict[str, Any]:
    required = set(owner["necessary_preferences"]) & NECESSARY_KEYS
    dimensions: dict[str, bool | None] = {
        "age": _range_match(candidate, owner, "age"),
        "height": _range_match(candidate, owner, "height"),
        "weight": _range_match(candidate, owner, "weight"),
        "religion": _category_match(candidate["religion"], owner["preferred_religion"]),
        "education": _category_match(_education_group(candidate["academic_background"]), owner["preferred_education"]),
        "profession": None if owner["preferred_profession"] == "any respectful profession" else (
            PROFESSION_GROUPS.get(candidate["profession"], candidate["profession"]) == owner["preferred_profession"]
        ),
        "location": _location_match(candidate, owner),
    }
    dimensions["lifestyle"], _ = _lifestyle_match(candidate, owner)

    weighted_total = 0.0
    possible = 0.0
    for key, matched in dimensions.items():
        if matched is None:
            continue
        weight = 2.0 if key in required else 1.0
        possible += weight
        weighted_total += weight if matched else 0.0
    score = weighted_total / possible if possible else 1.0
    failures = sorted(key for key in required if dimensions.get(key) is False)
    return {
        "score": score,
        "dimensions": dimensions,
        "required": sorted(required),
        "required_failures": failures,
    }


def _religion_filter_value(query: pd.Series) -> str | None:
    """Resolve the hard religion filter, respecting explicit no-preference."""
    raw_preference = _text(query.get("preferred_religion"))
    if raw_preference == "nopreference":
        return None
    if raw_preference not in NO_PREFERENCE:
        return _religion_value(raw_preference)
    actual_religion = _text(query.get("religion"))
    return None if actual_religion in NO_PREFERENCE else _religion_value(actual_religion)


def _religion_value(value: Any) -> str:
    normalized = _text(value)
    aliases = {
        "islam": "muslim", "muslim": "muslim",
        "christianity": "christian", "christian": "christian",
        "hinduism": "hindu", "hindu": "hindu",
        "buddhism": "buddhist", "buddhist": "buddhist",
        "judaism": "jewish", "jewish": "jewish",
        "sikhism": "sikh", "sikh": "sikh",
    }
    return aliases.get(normalized, normalized)


def _candidate_is_eligible(query: pd.Series, candidate: pd.Series) -> bool:
    if str(candidate.get("user_id")) == str(query.get("user_id")):
        return False
    if _text(candidate.get("gender")) == _text(query.get("gender")):
        return False
    religion = _religion_filter_value(query)
    return religion is None or _religion_value(candidate.get("religion")) == religion


def _priority_key(
    query_to_candidate: dict[str, Any],
    candidate_to_query: dict[str, Any],
    score: float,
    similarity: float,
    user_id: str,
) -> tuple[Any, ...]:
    """Sort requester must-haves first, then reciprocal/mutual compatibility."""
    requester_failures = len(query_to_candidate["required_failures"])
    reciprocal_failures = len(candidate_to_query["required_failures"])
    required_keys = set(query_to_candidate["required"]) | set(candidate_to_query["required"])
    mutually_satisfied = sum(
        query_to_candidate["dimensions"].get(key) is True
        and candidate_to_query["dimensions"].get(key) is True
        for key in required_keys
    )
    return (
        requester_failures,
        reciprocal_failures,
        -mutually_satisfied,
        -score,
        -similarity,
        user_id,
    )


def _reasons(a_to_b: dict[str, Any], b_to_a: dict[str, Any], similarity: float) -> list[str]:
    labels = {
        "age": "mutual age preference", "height": "mutual height preference",
        "weight": "mutual weight preference", "religion": "religion preference matched",
        "education": "education preference matched", "profession": "profession preference matched",
        "location": "location preference matched", "lifestyle": "lifestyle preference matched",
    }
    reasons = [
        label for key, label in labels.items()
        if a_to_b["dimensions"].get(key) is True and b_to_a["dimensions"].get(key) is True
    ]
    if similarity >= 0.75:
        reasons.append("high profile similarity")
    elif similarity >= 0.5:
        reasons.append("similar profile and interests")
    return reasons[:4] or ["closest available profile match"]


def _display_value(value: Any, unit: str | None = None) -> str:
    if value is None or pd.isna(value):
        return "Not specified"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).replace("_", " ").strip()
    if not text or text.lower() in {"nan", "none", "unknown"}:
        return "Not specified"
    return f"{text} {unit}" if unit else text


def _range_preference(row: pd.Series, field: str, unit: str | None = None) -> str:
    low = row.get(f"preferred_{field}_min")
    high = row.get(f"preferred_{field}_max")
    if pd.isna(low) or pd.isna(high):
        return "No preference"
    return f"{_display_value(low, unit)} - {_display_value(high, unit)}"


def _preference_value(row: pd.Series, key: str) -> str:
    if key == "age":
        return _range_preference(row, "age", "years")
    if key == "height":
        return _range_preference(row, "height", "cm")
    if key == "weight":
        return _range_preference(row, "weight", "kg")
    if key == "religion":
        return _display_value(row.get("preferred_religion"))
    if key == "education":
        return _display_value(row.get("preferred_education"))
    if key == "profession":
        value = _text(row.get("preferred_profession"))
        return "Any respectful profession" if value == "any respectful profession" else _display_value(value)
    if key == "location":
        preference = _text(row.get("preferred_location"))
        if preference == "specific":
            return f"Specific: {_display_value(row.get('specific_location'))}"
        if preference == "samecity":
            return "Same city"
        if preference == "samecountry":
            return "Same country"
        return _display_value(preference)
    if key == "lifestyle":
        parts: list[str] = []
        smoking = _text(row.get("lifestyle_pref_smoking"))
        alcohol = _text(row.get("lifestyle_pref_alcohol"))
        if smoking not in NO_PREFERENCE:
            parts.append(f"smoking: {smoking}")
        if alcohol not in NO_PREFERENCE:
            parts.append(f"alcohol: {alcohol}")
        if _bool(row.get("lifestyle_pref_dietary_match")):
            parts.append(f"diet: {_display_value(row.get('dietary_preference'))}")
        return ", ".join(parts) if parts else "No lifestyle preference"
    return "No preference"


def _candidate_value(row: pd.Series, key: str) -> str:
    if key == "age":
        return _display_value(row.get("age"), "years")
    if key == "height":
        return _display_value(row.get("height"), "cm")
    if key == "weight":
        return _display_value(row.get("weight"), "kg")
    if key == "education":
        return _display_value(row.get("academic_background"))
    if key == "lifestyle":
        return ", ".join([
            f"diet: {_display_value(row.get('dietary_preference'))}",
            f"smoking: {_display_value(row.get('smoking_habit'))}",
            f"alcohol: {_display_value(row.get('alcohol_consumption'))}",
        ])
    return _display_value(row.get(key))


def _match_note(key: str, requester_match: bool | None, reciprocal_match: bool | None) -> str:
    if requester_match is None and reciprocal_match is None:
        return "This preference was not specified by either side."
    if requester_match is True and reciprocal_match is True:
        return "Mutual preference satisfied."
    if requester_match is True and reciprocal_match is None:
        return "Matches your preference; their matching preference was not specified."
    if requester_match is None and reciprocal_match is True:
        return "Their preference matches your profile; you did not specify this preference."
    if requester_match is False and reciprocal_match is False:
        return "This was relaxed because closer ranked matches were limited."
    if requester_match is False:
        return "Does not fully match your preference."
    if reciprocal_match is False:
        return "Does not fully match their preference."
    return "Partially considered by the recommendation model."


def _build_match_explanation(
    query: pd.Series,
    candidate: pd.Series,
    a_to_b: dict[str, Any],
    b_to_a: dict[str, Any],
    similarity: float,
    preference: float,
) -> dict[str, Any]:
    labels = {
        "age": "Age",
        "height": "Height",
        "weight": "Weight",
        "religion": "Religion",
        "education": "Education",
        "profession": "Profession",
        "location": "Location",
        "lifestyle": "Lifestyle",
    }
    required = set(a_to_b["required"]) | set(b_to_a["required"])
    rows = []
    for key, label in labels.items():
        requester_match = a_to_b["dimensions"].get(key)
        reciprocal_match = b_to_a["dimensions"].get(key)
        matched = None if requester_match is None and reciprocal_match is None else (
            requester_match is not False and reciprocal_match is not False
        )
        rows.append({
            "key": key,
            "label": label,
            "matched": matched,
            "required": key in required,
            "user_preference": _preference_value(query, key),
            "candidate_value": _candidate_value(candidate, key),
            "candidate_preference": _preference_value(candidate, key),
            "note": _match_note(key, requester_match, reciprocal_match),
        })
    relaxed = sorted(set(a_to_b["required_failures"] + b_to_a["required_failures"]))
    return {
        "overall_score": round(0.40 * similarity + 0.60 * preference, 4),
        "similarity_score": round(similarity, 4),
        "preference_score": round(preference, 4),
        "strict_compatible": not relaxed,
        "reason_tags": _reasons(a_to_b, b_to_a, similarity),
        "relaxed_preferences": relaxed,
        "rows": rows,
    }


def recommend(
    user_id: str,
    top_k: int = 5,
    artifacts_dir: Path | str = DEFAULT_ARTIFACTS,
) -> dict[str, Any]:
    if top_k < 1:
        raise RecommendationError("top-k must be at least 1")
    top_k = min(top_k, 100)
    artifact, profiles = load_artifacts(artifacts_dir)
    matches = profiles.index[profiles["user_id"] == str(user_id)].tolist()
    if not matches:
        raise RecommendationError(f"User not found: {user_id}")
    query_index = matches[0]
    query = profiles.loc[query_index]
    matrix = transform_profiles(profiles, artifact)
    distances, indices = artifact["knn"].kneighbors(
        matrix[[query_index]], n_neighbors=len(profiles)
    )

    scored: list[dict[str, Any]] = []
    for distance, index in zip(distances[0], indices[0]):
        candidate = profiles.iloc[index]
        if not _candidate_is_eligible(query, candidate):
            continue
        similarity = max(0.0, min(1.0, 1.0 - float(distance)))
        a_to_b = _directional_preferences(query, candidate)
        b_to_a = _directional_preferences(candidate, query)
        preference = (a_to_b["score"] + b_to_a["score"]) / 2.0
        relaxed = sorted(set(a_to_b["required_failures"] + b_to_a["required_failures"]))
        explanation = _build_match_explanation(query, candidate, a_to_b, b_to_a, similarity, preference)
        scored.append({
            "user_id": candidate["user_id"],
            "name": candidate["name"],
            "age": int(candidate["age"]) if float(candidate["age"]).is_integer() else float(candidate["age"]),
            "gender": candidate["gender"],
            "religion": candidate["religion"],
            "location": candidate["location"],
            "profession": candidate["profession"],
            "score": round(0.40 * similarity + 0.60 * preference, 4),
            "similarity": round(similarity, 4),
            "preference_score": round(preference, 4),
            "strict_compatible": not relaxed,
            "reason_tags": _reasons(a_to_b, b_to_a, similarity),
            "relaxed_preferences": relaxed,
            "match_explanation": explanation,
            "priority_key": _priority_key(
                a_to_b, b_to_a,
                0.40 * similarity + 0.60 * preference,
                similarity, str(candidate["user_id"]),
            ),
        })

    ordered = sorted(scored, key=lambda item: item["priority_key"])
    selected = ordered[:top_k]
    for rank, item in enumerate(selected, start=1):
        item.pop("priority_key", None)
        item["rank"] = rank
    return {
        "query_user": {"user_id": query["user_id"], "name": query["name"]},
        "match_count": len(selected),
        "matches": selected,
    }
