"""Commit-triggered, debounced background recommendation retraining."""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from database import engine

DEBOUNCE_SECONDS = 10
POLL_SECONDS = 2
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_hooks_installed = False


def request_retraining() -> None:
    """Record a new desired model generation without blocking the caller."""
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO recommendation_training_state
                (id, requested_generation, completed_generation, status,
                 requested_at, updated_at)
            VALUES (1, 1, 0, 'pending', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                requested_generation = recommendation_training_state.requested_generation + 1,
                requested_at = NOW(),
                updated_at = NOW(),
                status = CASE
                    WHEN recommendation_training_state.status = 'running' THEN 'running'
                    ELSE 'pending'
                END
        """))


def install_session_hooks() -> None:
    """Queue one retrain after commits that mutate User or Profile objects."""
    global _hooks_installed
    if _hooks_installed:
        return

    from models.profile.profile import Profile
    from models.user.user import User

    @event.listens_for(Session, "before_flush")
    def _detect_recommendation_changes(session, _flush_context, _instances):
        changed = session.new.union(session.dirty).union(session.deleted)
        if any(isinstance(item, (User, Profile)) for item in changed):
            session.info["recommendation_retrain_needed"] = True

    @event.listens_for(Session, "after_commit")
    def _queue_after_commit(session):
        if not session.info.pop("recommendation_retrain_needed", False):
            return
        try:
            request_retraining()
            print("[RECOMMENDATION] Database change queued a background retrain")
        except Exception as exc:
            # The application transaction is already committed. Scheduling must
            # never turn a successful API request into an error response.
            print(f"[RECOMMENDATION] Could not queue retraining: {exc}")

    @event.listens_for(Session, "after_rollback")
    def _clear_after_rollback(session):
        session.info.pop("recommendation_retrain_needed", None)

    _hooks_installed = True


class RetrainingWatcher:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="recommendation-retraining-watcher", daemon=True
        )
        self._thread.start()
        print("[RECOMMENDATION] Background retraining watcher started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=POLL_SECONDS + 2)

    def _is_due(self) -> bool:
        with engine.connect() as connection:
            return bool(connection.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM recommendation_training_state
                    WHERE id = 1
                      AND status = 'pending'
                      AND requested_generation > completed_generation
                      AND requested_at <= NOW() - (:seconds * INTERVAL '1 second')
                )
            """), {"seconds": DEBOUNCE_SECONDS}).scalar())

    def _launch(self) -> None:
        self._process = subprocess.Popen(
            [sys.executable, "retrain_recommendation_model.py", "--background"],
            cwd=str(_BACKEND_DIR),
        )
        print(f"[RECOMMENDATION] Started trainer process {self._process.pid}")

    def _run(self) -> None:
        while not self._stop.wait(POLL_SECONDS):
            try:
                if self._process and self._process.poll() is None:
                    continue
                self._process = None
                if self._is_due():
                    self._launch()
            except Exception as exc:
                # A missing state table before migration should not prevent app startup.
                print(f"[RECOMMENDATION] Watcher waiting: {exc}")


watcher = RetrainingWatcher()
