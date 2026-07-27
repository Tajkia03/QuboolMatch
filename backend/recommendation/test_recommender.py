from pathlib import Path

import numpy as np
import pytest

from fix_gender_names import INVALID_LAST_NAMES, NAME_POOLS, correct_rows
from recommender import (
    DEFAULT_CSV,
    RecommendationError,
    _candidate_is_eligible,
    _directional_preferences,
    _education_group,
    _priority_key,
    _religion_value,
    fit_model,
    load_profiles,
    recommend,
    train,
    transform_profiles,
)


def test_feature_matrix_is_finite_and_stable():
    profiles = load_profiles(DEFAULT_CSV)
    artifact, matrix = fit_model(profiles)
    transformed = transform_profiles(profiles, artifact)

    assert len(profiles) == 500
    assert matrix.shape == transformed.shape
    assert matrix.shape[1] == artifact["feature_count"]
    assert np.isfinite(matrix).all()
    assert np.allclose(matrix, transformed)


def test_recommendations_exclude_self_and_same_gender(tmp_path: Path):
    profiles = load_profiles(DEFAULT_CSV)
    query = profiles.iloc[0]
    train(DEFAULT_CSV, tmp_path)

    result = recommend(query["user_id"], 20, tmp_path)

    assert 0 < result["match_count"] <= 20
    assert all(item["user_id"] != query["user_id"] for item in result["matches"])
    assert all(item["gender"] != query["gender"] for item in result["matches"])
    assert all(
        _religion_value(item["religion"]) == _religion_value(query["preferred_religion"])
        for item in result["matches"]
    )
    assert [item["rank"] for item in result["matches"]] == list(
        range(1, result["match_count"] + 1)
    )


def test_ranking_is_deterministic_and_strict_first(tmp_path: Path):
    profiles = load_profiles(DEFAULT_CSV)
    user_id = profiles.iloc[0]["user_id"]
    train(DEFAULT_CSV, tmp_path)

    first = recommend(user_id, 500, tmp_path)
    second = recommend(user_id, 500, tmp_path)

    assert first == second
    compatibility = [item["strict_compatible"] for item in first["matches"]]
    assert compatibility == sorted(compatibility, reverse=True)
    assert any(not value for value in compatibility)
    assert first["match_count"] <= 100


def test_recommendations_include_match_explanation(tmp_path: Path):
    profiles = load_profiles(DEFAULT_CSV)
    user_id = profiles.iloc[0]["user_id"]
    train(DEFAULT_CSV, tmp_path)

    result = recommend(user_id, 5, tmp_path)
    explanation = result["matches"][0]["match_explanation"]

    assert set(explanation) >= {
        "overall_score",
        "similarity_score",
        "preference_score",
        "strict_compatible",
        "reason_tags",
        "rows",
    }
    assert explanation["reason_tags"] == result["matches"][0]["reason_tags"]
    assert explanation["strict_compatible"] == result["matches"][0]["strict_compatible"]
    assert 0 <= explanation["overall_score"] <= 1
    assert 0 <= explanation["similarity_score"] <= 1
    assert 0 <= explanation["preference_score"] <= 1
    assert {row["key"] for row in explanation["rows"]} == {
        "age", "height", "weight", "religion", "education", "profession", "location", "lifestyle",
    }
    assert all(
        set(row) >= {"label", "matched", "required", "user_preference", "candidate_value", "note"}
        for row in explanation["rows"]
    )


def test_religion_filter_preference_fallback_and_no_preference():
    profiles = load_profiles(DEFAULT_CSV)
    query = profiles.iloc[0].copy()
    candidate = profiles.loc[profiles["gender"] != query["gender"]].iloc[0].copy()

    query["preferred_religion"] = "muslim"
    candidate["religion"] = "Islam"
    assert _candidate_is_eligible(query, candidate)
    candidate["religion"] = "Christianity"
    assert not _candidate_is_eligible(query, candidate)

    query["preferred_religion"] = "unknown"
    query["religion"] = "Buddhism"
    candidate["religion"] = "buddhist"
    assert _candidate_is_eligible(query, candidate)

    query["preferred_religion"] = "noPreference"
    candidate["religion"] = "any-religion"
    assert _candidate_is_eligible(query, candidate)


def test_requester_must_have_failures_are_the_first_priority():
    base = {"dimensions": {"age": True}, "required": ["age"], "required_failures": []}
    requester_failed = {**base, "required_failures": ["age"]}
    reciprocal_failed = {**base, "required_failures": ["age"]}

    requester_match_key = _priority_key(base, reciprocal_failed, 0.2, 0.2, "a")
    requester_failure_key = _priority_key(requester_failed, base, 0.99, 0.99, "b")
    assert requester_match_key < requester_failure_key


def test_directional_preference_rules_and_required_failures():
    profiles = load_profiles(DEFAULT_CSV)
    owner = profiles.iloc[0].copy()
    candidate = profiles.iloc[1].copy()
    owner["preferred_age_min"] = owner["preferred_age_max"] = candidate["age"]
    owner["preferred_height_min"] = owner["preferred_height_max"] = candidate["height"]
    owner["preferred_weight_min"] = owner["preferred_weight_max"] = candidate["weight"]
    owner["preferred_religion"] = candidate["religion"]
    owner["preferred_education"] = _education_group(candidate["academic_background"])
    owner["preferred_profession"] = "any respectful profession"
    owner["preferred_location"] = "specific"
    owner["specific_location"] = candidate["location"]
    owner["lifestyle_pref_smoking"] = "nopreference"
    owner["lifestyle_pref_alcohol"] = "nopreference"
    owner["lifestyle_pref_dietary_match"] = "false"
    owner["necessary_preferences"] = [
        "age", "height", "religion", "education", "location",
    ]

    matched = _directional_preferences(owner, candidate)
    assert matched["score"] == 1.0
    assert matched["required_failures"] == []

    candidate["religion"] = "not-the-preferred-religion"
    candidate["location"] = "not-the-preferred-location"
    failed = _directional_preferences(owner, candidate)
    assert failed["score"] < 1.0
    assert failed["required_failures"] == ["location", "religion"]


def test_invalid_inputs_raise_clear_errors(tmp_path: Path):
    with pytest.raises(RecommendationError, match="Artifacts not found"):
        recommend("missing", artifacts_dir=tmp_path)

    train(DEFAULT_CSV, tmp_path)
    with pytest.raises(RecommendationError, match="User not found"):
        recommend("missing", artifacts_dir=tmp_path)
    with pytest.raises(RecommendationError, match="top-k"):
        recommend("missing", top_k=0, artifacts_dir=tmp_path)


def test_csv_names_match_gender_and_correction_is_idempotent():
    profiles = load_profiles(DEFAULT_CSV)
    for row in profiles.itertuples():
        parts = row.name.split()
        first_name = parts[0].casefold()
        assert first_name in {name.casefold() for name in NAME_POOLS[row.gender.title()]}
        assert parts[-1].casefold() not in INVALID_LAST_NAMES[row.gender.title()]

    rows = profiles[["user_id", "name", "gender"]].to_dict("records")
    corrected, changes = correct_rows(rows)
    corrected_again, second_changes = correct_rows(corrected)
    assert changes == []
    assert second_changes == []
    assert corrected_again == corrected

    mismatched = [{
        "user_id": "example", "name": "Raisa Rahman", "gender": "Male",
        "email": "unchanged@example.test", "location": "Dhaka",
    }]
    fixed, fixture_changes = correct_rows(mismatched)
    assert len(fixture_changes) == 1
    assert fixed[0]["name"].split(maxsplit=1)[1] == "Rahman"
    assert {key: fixed[0][key] for key in mismatched[0] if key != "name"} == {
        key: mismatched[0][key] for key in mismatched[0] if key != "name"
    }

    invalid_surnames = [
        {"user_id": "male", "name": "Arif Begum", "gender": "Male"},
        {"user_id": "female", "name": "Aisha Miah", "gender": "Female"},
    ]
    fixed_surnames, surname_changes = correct_rows(invalid_surnames)
    assert len(surname_changes) == 2
    assert fixed_surnames[0]["name"].split()[-1].casefold() not in INVALID_LAST_NAMES["Male"]
    assert fixed_surnames[1]["name"].split()[-1].casefold() not in INVALID_LAST_NAMES["Female"]
