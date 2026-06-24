import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Float, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Personal Information
    location = Column(String, nullable=True)
    father_name = Column(String, nullable=True)
    mother_name = Column(String, nullable=True)
    guardian_name = Column(String, nullable=True)
    guardian_relation = Column(String, nullable=True)
    guardian_relation_other = Column(String, nullable=True)
    guardian_contact_number = Column(String, nullable=True)
    academic_background = Column(String, nullable=True)
    profession = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    hobbies = Column(Text, nullable=True)
    
    # Intro Video - stored as binary
    intro_video_data = Column(LargeBinary, nullable=True)
    intro_video_filename = Column(String, nullable=True)
    intro_video_content_type = Column(String, nullable=True)
    
    # Health Information
    medical_history = Column(Text, nullable=True)
    overall_health_status = Column(String, nullable=True)
    long_term_condition = Column(String, nullable=True)  # yes/no
    long_term_condition_description = Column(Text, nullable=True)
    blood_group = Column(String, nullable=True)
    genetic_conditions = Column(Text, nullable=True)  # JSON array stored as text
    fertility_awareness = Column(String, nullable=True)
    disability = Column(String, nullable=True)  # yes/no
    disability_description = Column(Text, nullable=True)
    
    # Medical Documents - stored as binary
    medical_documents_data = Column(LargeBinary, nullable=True)
    medical_documents_filename = Column(String, nullable=True)
    medical_documents_content_type = Column(String, nullable=True)
    
    # Physical Attributes
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    
    # Lifestyle & Habits
    dietary_preference = Column(String, nullable=True)
    smoking_habit = Column(String, nullable=True)
    alcohol_consumption = Column(String, nullable=True)
    chronic_illness = Column(String, nullable=True)
    interests = Column(Text, nullable=True)
    
    # Profile Picture - stored as binary
    profile_picture_data = Column(LargeBinary, nullable=True)
    profile_picture_filename = Column(String, nullable=True)
    profile_picture_content_type = Column(String, nullable=True)
    
    # Partner and Marriage Preferences
    preferred_age_min = Column(Integer, nullable=True)
    preferred_age_max = Column(Integer, nullable=True)
    preferred_height_min = Column(Float, nullable=True)
    preferred_height_max = Column(Float, nullable=True)
    preferred_weight_min = Column(Float, nullable=True)
    preferred_weight_max = Column(Float, nullable=True)
    preferred_religion = Column(String, nullable=True)
    preferred_education = Column(String, nullable=True)
    preferred_profession = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    specific_location = Column(String, nullable=True)
    willing_to_relocate = Column(Boolean, default=False)
    
    # Lifestyle Preferences for Partner
    lifestyle_pref_smoking = Column(String, nullable=True)
    lifestyle_pref_alcohol = Column(String, nullable=True)
    lifestyle_pref_dietary_match = Column(Boolean, default=False)
    
    living_with_in_laws = Column(String, nullable=True)
    living_arrangement_comment = Column(Text, nullable=True)
    fertility_comment = Column(Text, nullable=True)
    preferred_religion_comment = Column(Text, nullable=True)
    preferred_education_comment = Column(Text, nullable=True)
    career_support_expectations = Column(Text, nullable=True)
    career_support_comment = Column(Text, nullable=True)
    necessary_preferences = Column(Text, nullable=True)  # JSON array stored as text
    additional_comments = Column(Text, nullable=True)
    
    # System fields
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    # user = relationship("User", back_populates="profile")

    def __init__(self, user_id: str, **kwargs):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.is_completed = False
        
        # Set all optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def update_profile(self, **kwargs):
        """Update profile fields"""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ['id', 'user_id', 'created_at']:
                setattr(self, key, value)
        
        self.updated_at = datetime.now(timezone.utc)
        return self

    def mark_as_completed(self):
        """Mark profile as completed"""
        self.is_completed = True
        self.updated_at = datetime.now(timezone.utc)
        return self

    def to_dict(self):
        """Convert profile to dictionary"""
        # Convert profile picture to base64 if exists
        profile_picture_base64 = None
        if self.profile_picture_data:
            try:
                import base64
                encoded = base64.b64encode(self.profile_picture_data).decode('utf-8')
                content_type = self.profile_picture_content_type or "image/jpeg"
                profile_picture_base64 = f"data:{content_type};base64,{encoded}"
            except Exception as e:
                print(f"Error encoding profile picture: {e}")
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'location': self.location,
            'father_name': self.father_name,
            'mother_name': self.mother_name,
            'guardian_name': self.guardian_name,
            'guardian_relation': self.guardian_relation,
            'guardian_relation_other': self.guardian_relation_other,
            'guardian_contact_number': self.guardian_contact_number,
            'academic_background': self.academic_background,
            'profession': self.profession,
            'marital_status': self.marital_status,
            'hobbies': self.hobbies,
            'has_intro_video': bool(self.intro_video_data),
            'intro_video_filename': self.intro_video_filename,
            'medical_history': self.medical_history,
            'overall_health_status': self.overall_health_status,
            'long_term_condition': self.long_term_condition,
            'long_term_condition_description': self.long_term_condition_description,
            'blood_group': self.blood_group,
            'genetic_conditions': self.genetic_conditions,
            'fertility_awareness': self.fertility_awareness,
            'disability': self.disability,
            'disability_description': self.disability_description,
            'has_medical_documents': bool(self.medical_documents_data),
            'medical_documents_filename': self.medical_documents_filename,
            'height': self.height,
            'weight': self.weight,
            'dietary_preference': self.dietary_preference,
            'smoking_habit': self.smoking_habit,
            'alcohol_consumption': self.alcohol_consumption,
            'chronic_illness': self.chronic_illness,
            'interests': self.interests,
            'has_profile_picture': bool(self.profile_picture_data),
            'profile_picture': profile_picture_base64,
            'profile_picture_filename': self.profile_picture_filename,
            'preferred_age_min': self.preferred_age_min,
            'preferred_age_max': self.preferred_age_max,
            'preferred_height_min': self.preferred_height_min,
            'preferred_height_max': self.preferred_height_max,
            'preferred_weight_min': self.preferred_weight_min,
            'preferred_weight_max': self.preferred_weight_max,
            'preferred_religion': self.preferred_religion,
            'preferred_education': self.preferred_education,
            'preferred_profession': self.preferred_profession,
            'preferred_location': self.preferred_location,
            'specific_location': self.specific_location,
            'willing_to_relocate': self.willing_to_relocate,
            'lifestyle_pref_smoking': self.lifestyle_pref_smoking,
            'lifestyle_pref_alcohol': self.lifestyle_pref_alcohol,
            'lifestyle_pref_dietary_match': self.lifestyle_pref_dietary_match,
            'living_with_in_laws': self.living_with_in_laws,
            'living_arrangement_comment': self.living_arrangement_comment,
            'fertility_comment': self.fertility_comment,
            'preferred_religion_comment': self.preferred_religion_comment,
            'preferred_education_comment': self.preferred_education_comment,
            'career_support_expectations': self.career_support_expectations,
            'career_support_comment': self.career_support_comment,
            'necessary_preferences': self.necessary_preferences,
            'additional_comments': self.additional_comments,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
