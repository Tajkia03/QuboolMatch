import json
from pathlib import Path

import pandas as pd

from recommendation import database_training
from recommender import DEFAULT_CSV, load_profiles, load_runtime_artifacts


def test_database_publish_uses_real_ids_and_atomic_pointer(tmp_path: Path, monkeypatch):
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(database_training, "DEFAULT_ARTIFACTS", artifacts)
    monkeypatch.setattr(database_training, "VERSIONS_DIR", artifacts / "versions")
    monkeypatch.setattr(database_training, "ACTIVE_POINTER", artifacts / "active.json")

    profiles = load_profiles(DEFAULT_CSV).head(4).copy()
    profiles["user_id"] = [f"database-uuid-{index}" for index in range(4)]
    published = database_training._publish(pd.DataFrame(profiles), generation=7)

    pointer = json.loads((artifacts / "active.json").read_text())
    assert pointer["generation"] == 7
    assert published.name == pointer["version"]
    artifact, loaded_profiles = load_runtime_artifacts(artifacts)
    assert artifact["id_source"] == "database"
    assert loaded_profiles["user_id"].tolist() == profiles["user_id"].tolist()


def test_runtime_loader_falls_back_to_bootstrap_artifacts(tmp_path: Path):
    # An invalid pointer must not prevent the tracked flat artifacts from loading.
    source = Path(__file__).with_name("artifacts")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    for name in ("knn_model.joblib", "profiles.joblib"):
        (artifacts / name).write_bytes((source / name).read_bytes())
    (artifacts / "active.json").write_text("not-json")

    artifact, profiles = load_runtime_artifacts(artifacts)
    assert artifact["model_version"] == 1
    assert not profiles.empty
