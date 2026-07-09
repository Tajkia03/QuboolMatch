from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.recommendation_training_state import RecommendationTrainingState
from models.user.user import User
from services import retraining_coordinator


def test_only_committed_user_or_profile_changes_request_training(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    sessions = sessionmaker(bind=test_engine)
    requests = []
    monkeypatch.setattr(retraining_coordinator, "request_retraining", lambda: requests.append(True))
    retraining_coordinator.install_session_hooks()

    session = sessions()
    session.add(User("Test", "test@example.com", "password", "Male", "NID-1", 25))
    session.commit()
    assert len(requests) == 1

    session.add(User("Rolled Back", "rollback@example.com", "password", "Male", "NID-2", 26))
    session.flush()
    session.rollback()
    assert len(requests) == 1

    session.add(RecommendationTrainingState(id=1))
    session.commit()
    assert len(requests) == 1
    session.close()
