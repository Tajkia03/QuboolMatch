import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    context = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "reporter_id": self.reporter_id,
            "reported_id": self.reported_id,
            "reason": self.reason,
            "details": self.details,
            "context": self.context,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }