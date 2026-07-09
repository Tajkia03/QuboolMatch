from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, Text

from database import Base


class RecommendationTrainingState(Base):
    """Singleton row coordinating recommendation retraining."""

    __tablename__ = "recommendation_training_state"

    id = Column(Integer, primary_key=True, default=1)
    requested_generation = Column(BigInteger, nullable=False, default=0)
    completed_generation = Column(BigInteger, nullable=False, default=0)
    status = Column(Text, nullable=False, default="idle")
    requested_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
