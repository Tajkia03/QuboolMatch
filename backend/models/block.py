import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from database import Base


class Block(Base):
    __tablename__ = "blocks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    blocker_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "blocker_id": self.blocker_id,
            "blocked_id": self.blocked_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }