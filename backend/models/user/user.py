import uuid
import bcrypt
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Date, Time, Text, LargeBinary, Integer, Float
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic user information from signup form
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    gender = Column(String, nullable=False)  # Male/Female/Other
    nid = Column(String, nullable=False, unique=True)  # National ID number
    age = Column(Integer, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    religion = Column(String, nullable=True)
    
    # Preferred age range for matching
    preferred_age_from = Column(Integer, nullable=True)
    preferred_age_to = Column(Integer, nullable=True)
    
    # System fields
    is_admin = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(
        timezone.utc), nullable=False)
    
    # NID Verification fields
    nid_image_data = Column(LargeBinary, nullable=True)  # Binary data of uploaded NID image
    nid_image_filename = Column(String, nullable=True)  # Original filename
    nid_image_content_type = Column(String, nullable=True)  # MIME type (image/jpeg, etc.)
    
    # Recent verification image fields
    recent_image_data = Column(LargeBinary, nullable=True)  # Binary data of recent verification image
    recent_image_filename = Column(String, nullable=True)  # Original filename
    recent_image_content_type = Column(String, nullable=True)  # MIME type (image/jpeg, etc.)
    
    verification_date = Column(Date, nullable=True)  # Scheduled verification date
    verification_time = Column(Time, nullable=True)  # Scheduled verification time
    verification_status = Column(String, default="not_submitted")  # not_submitted, pending, verified, rejected
    verification_notes = Column(Text, nullable=True)  # Additional notes for verification
    verified_at = Column(DateTime, nullable=True)  # When verification was completed
    matching_percentage = Column(Float, nullable=True)  # AI-based face matching percentage (0-100)

    guardian_verification_status = Column(String, default="not_submitted", nullable=False)

    def __init__(self, name: str, email: str, password: str, gender: str, nid: str, age: int, 
                 religion: str = None, preferred_age_from: int = None, preferred_age_to: int = None, 
                 is_admin: bool = False):
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.gender = gender
        self.nid = nid
        self.age = age
        self.religion = religion
        self.preferred_age_from = preferred_age_from
        self.preferred_age_to = preferred_age_to
        self.is_admin = is_admin
        self.is_deleted = False
        self.is_archived = False
        self.verification_status = "not_submitted"
        self.guardian_verification_status = "not_submitted"

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.hashed_password.encode())

    def with_email(self, email):
        self.email = email
        return self

    def archive(self):
        self.is_archived = True
        return self

    def delete(self):
        self.is_deleted = True
        return self

    def update_verification_info(self, nid_image_data: bytes = None, nid_image_filename: str = None,
                               nid_image_content_type: str = None, recent_image_data: bytes = None,
                               recent_image_filename: str = None, recent_image_content_type: str = None,
                               verification_date=None, verification_time=None, verification_notes: str = None):
        if nid_image_data:
            self.nid_image_data = nid_image_data
        if nid_image_filename:
            self.nid_image_filename = nid_image_filename
        if nid_image_content_type:
            self.nid_image_content_type = nid_image_content_type
        if recent_image_data:
            self.recent_image_data = recent_image_data
        if recent_image_filename:
            self.recent_image_filename = recent_image_filename
        if recent_image_content_type:
            self.recent_image_content_type = recent_image_content_type
        if verification_date:
            self.verification_date = verification_date
        if verification_time:
            self.verification_time = verification_time
        if verification_notes:
            self.verification_notes = verification_notes
        # Keep status as pending until admin verifies
        self.verification_status = "pending"
        return self

    def verify(self):
        self.verification_status = "verified"
        self.verified_at = datetime.now(timezone.utc)
        return self

    def reject_verification(self, notes: str = None):
        self.verification_status = "rejected"
        return self

    def verify_guardian(self):
        self.guardian_verification_status = "verified"
        return self

    def reject_guardian_verification(self):
        self.guardian_verification_status = "rejected"
        return self

    def promote_to_admin(self):
        """Promote user to admin status"""
        self.is_admin = True
        return self

    def demote_from_admin(self):
        """Remove admin status from user"""
        self.is_admin = False
        return self
