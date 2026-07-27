import uuid
import bcrypt
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, Date, DateTime, Text, LargeBinary, Integer, Float, JSON
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
    father_name = Column(String, nullable=True)
    mother_name = Column(String, nullable=True)
    religion = Column(String, nullable=True)
    
    # Preferred age range for matching
    preferred_age_from = Column(Integer, nullable=True)
    preferred_age_to = Column(Integer, nullable=True)
    
    # System fields
    is_admin = Column(Boolean, default=False, nullable=False)
    # Synthetic accounts imported for local/demo recommendation testing.
    is_demo = Column(Boolean, default=False, nullable=False)
    identity_verified = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(
        timezone.utc), nullable=False)
    
    # NID Verification fields
    nid_image_data = Column(LargeBinary, nullable=True)  # Binary data of uploaded NID image
    nid_image_filename = Column(String, nullable=True)  # Original filename
    nid_image_content_type = Column(String, nullable=True)  # MIME type (image/jpeg, etc.)
    nid_back_image_data = Column(LargeBinary, nullable=True)
    nid_back_image_filename = Column(String, nullable=True)
    nid_back_image_content_type = Column(String, nullable=True)
    verification_status = Column(String, default="not_submitted")  # not_submitted, pending, verified, rejected
    verification_notes = Column(Text, nullable=True)  # Additional notes for verification
    verified_at = Column(DateTime, nullable=True)  # When verification was completed
    matching_percentage = Column(Float, nullable=True)  # AI-based face matching percentage (0-100)
    ocr_name = Column(String, nullable=True)
    ocr_father_name = Column(String, nullable=True)
    ocr_mother_name = Column(String, nullable=True)
    ocr_date_of_birth = Column(Date, nullable=True)
    ocr_nid_number = Column(String, nullable=True)
    ocr_address = Column(Text, nullable=True)
    ocr_blood_group = Column(String, nullable=True)
    ocr_image_quality = Column(String, nullable=True)
    ocr_warnings = Column(JSON, nullable=True)
    ocr_confirmed = Column(Boolean, default=False, nullable=False)
    ocr_processed_at = Column(DateTime, nullable=True)
    ocr_name_match_score = Column(Float, nullable=True)
    ocr_name_match_status = Column(String(30), nullable=True)
    ocr_nid_match = Column(Boolean, nullable=True)
    ocr_dob_match = Column(Boolean, nullable=True)
    ocr_review_status = Column(String(30), nullable=True)
    admin_review_notes = Column(Text, nullable=True)

    guardian_verification_status = Column(String, default="not_submitted", nullable=False)

    def __init__(self, name: str, email: str, password: str, gender: str, nid: str, age: int, 
                 religion: str = None, preferred_age_from: int = None, preferred_age_to: int = None, 
                 is_admin: bool = False, hashed_password: str = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.hashed_password = hashed_password or bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.gender = gender
        self.nid = nid
        self.age = age
        self.father_name = None
        self.mother_name = None
        self.religion = religion
        self.preferred_age_from = preferred_age_from
        self.preferred_age_to = preferred_age_to
        self.is_admin = is_admin
        self.identity_verified = False
        self.is_deleted = False
        self.is_archived = False
        self.email_verified = False
        self.email_verified_at = None
        self.verification_status = "not_submitted"
        self.guardian_verification_status = "not_submitted"
        self.ocr_confirmed = False
        self.ocr_review_status = "pending_review"
        self.admin_review_notes = None

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
                               nid_image_content_type: str = None,
                               nid_back_image_data: bytes = None, nid_back_image_filename: str = None,
                               nid_back_image_content_type: str = None,
                               verification_notes: str = None):
        if nid_image_data:
            self.nid_image_data = nid_image_data
        if nid_image_filename:
            self.nid_image_filename = nid_image_filename
        if nid_image_content_type:
            self.nid_image_content_type = nid_image_content_type
        if nid_back_image_data:
            self.nid_back_image_data = nid_back_image_data
        if nid_back_image_filename:
            self.nid_back_image_filename = nid_back_image_filename
        if nid_back_image_content_type:
            self.nid_back_image_content_type = nid_back_image_content_type
        if verification_notes:
            self.verification_notes = verification_notes
        # Keep status as pending until admin verifies
        self.verification_status = "pending"
        return self

    def update_ocr_extraction(
        self,
        *,
        ocr_name: Optional[str] = None,
        ocr_father_name: Optional[str] = None,
        ocr_mother_name: Optional[str] = None,
        ocr_date_of_birth=None,
        ocr_nid_number: Optional[str] = None,
        ocr_address: Optional[str] = None,
        ocr_blood_group: Optional[str] = None,
        ocr_image_quality: Optional[str] = None,
        ocr_warnings=None,
        processed_at=None,
        ocr_name_match_score: Optional[float] = None,
        ocr_name_match_status: Optional[str] = None,
        ocr_nid_match: Optional[bool] = None,
        ocr_dob_match: Optional[bool] = None,
        ocr_review_status: Optional[str] = "pending_review",
        admin_review_notes: Optional[str] = None,
    ):
        self.ocr_name = ocr_name
        self.ocr_father_name = ocr_father_name
        self.ocr_mother_name = ocr_mother_name
        self.ocr_date_of_birth = ocr_date_of_birth
        self.ocr_nid_number = ocr_nid_number
        self.ocr_address = ocr_address
        self.ocr_blood_group = ocr_blood_group
        self.ocr_image_quality = ocr_image_quality
        self.ocr_warnings = ocr_warnings or []
        self.ocr_confirmed = False
        self.ocr_processed_at = processed_at
        self.ocr_name_match_score = ocr_name_match_score
        self.ocr_name_match_status = ocr_name_match_status
        self.ocr_nid_match = ocr_nid_match
        self.ocr_dob_match = ocr_dob_match
        self.ocr_review_status = ocr_review_status
        self.admin_review_notes = admin_review_notes
        return self

    def verify(self):
        self.verification_status = "verified"
        self.verified_at = datetime.now(timezone.utc)
        self.identity_verified = True
        return self

    def reject_verification(self, notes: str = None):
        self.verification_status = "rejected"
        self.identity_verified = False
        return self

    def set_official_identity(
        self,
        *,
        name: Optional[str] = None,
        nid: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        age: Optional[int] = None,
        father_name: Optional[str] = None,
        mother_name: Optional[str] = None,
    ):
        if name is not None:
            self.name = name
        if nid is not None:
            self.nid = nid
        if date_of_birth is not None:
            self.date_of_birth = date_of_birth
        if age is not None:
            self.age = age
        if father_name is not None:
            self.father_name = father_name
        if mother_name is not None:
            self.mother_name = mother_name
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
