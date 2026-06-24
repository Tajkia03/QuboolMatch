from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from repositories.profile_repository.profile_repository import ProfileRepository
from repositories.block_repository import BlockRepository
from shared.token import Token
from models.user.user import User
import json
import base64
import re
from datetime import datetime

router = APIRouter()


def get_current_user_id(authorization: str = Header(None), db: Session = Depends(get_db)) -> str:
    """Extract and verify user ID from Authorization header"""
    print(f"DEBUG: Authorization header: {authorization}")
    
    if not authorization:
        print("DEBUG: No authorization header")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not authorization.startswith("Bearer "):
        print(f"DEBUG: Invalid header format: {authorization[:20]}")
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    print(f"DEBUG: Token extracted: {token[:20]}...")
    
    payload = Token.verify_token(token)
    print(f"DEBUG: Token payload: {payload}")
    
    if not payload:
        print("DEBUG: Token verification failed")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("user_id")
    print(f"DEBUG: User ID from token: {user_id}")
    
    if not user_id:
        print("DEBUG: No user_id in payload")
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"DEBUG: User {user_id} not found in database")
        raise HTTPException(status_code=401, detail="User not found")
    
    print(f"DEBUG: Successfully authenticated user: {user_id}")
    return user_id


def process_base64_file(base64_data: str) -> tuple:
    """
    Convert base64 data URL to binary data
    Returns: (binary_data, filename, content_type)
    """
    if not base64_data or not base64_data.startswith('data:'):
        return None, None, None
    
    try:
        # Extract content type and base64 data
        # Format: data:image/png;base64,iVBORw0KGgoAAAANS...
        match = re.match(r'data:([^;]+);base64,(.+)', base64_data)
        if not match:
            return None, None, None
        
        content_type = match.group(1)
        base64_content = match.group(2)
        
        # Decode base64 to binary
        binary_data = base64.b64decode(base64_content)
        
        # Generate filename based on content type
        extension = content_type.split('/')[-1]
        filename = f"file.{extension}"
        
        return binary_data, filename, content_type
    except Exception as e:
        print(f"Error processing base64 file: {e}")
        return None, None, None


class ProfileCreate(BaseModel):
    # Basic user information
    name: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    religion: Optional[str] = None

    # Personal Information
    location: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_relation_other: Optional[str] = None
    guardian_contact_number: Optional[str] = None
    academic_background: Optional[str] = None
    profession: Optional[str] = None
    marital_status: Optional[str] = None
    hobbies: Optional[str] = None
    intro_video: Optional[str] = None
    
    # Health Information
    medical_history: Optional[str] = None
    overall_health_status: Optional[str] = None
    long_term_condition: Optional[str] = None
    long_term_condition_description: Optional[str] = None
    blood_group: Optional[str] = None
    genetic_conditions: Optional[str] = None  # Accept as string (JSON)
    fertility_awareness: Optional[str] = None
    disability: Optional[str] = None
    disability_description: Optional[str] = None
    medical_documents: Optional[str] = None
    
    # Physical Attributes
    height: Optional[float] = None
    weight: Optional[float] = None
    
    # Lifestyle & Habits
    dietary_preference: Optional[str] = None
    smoking_habit: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    chronic_illness: Optional[str] = None
    interests: Optional[str] = None
    
    # Profile Picture
    profile_picture: Optional[str] = None
    
    # Partner and Marriage Preferences
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_height_min: Optional[float] = None
    preferred_height_max: Optional[float] = None
    preferred_weight_min: Optional[float] = None
    preferred_weight_max: Optional[float] = None
    preferred_religion: Optional[str] = None
    preferred_education: Optional[str] = None
    preferred_profession: Optional[str] = None
    preferred_location: Optional[str] = None
    specific_location: Optional[str] = None
    willing_to_relocate: Optional[bool] = False
    
    # Lifestyle Preferences for Partner
    lifestyle_pref_smoking: Optional[str] = None
    lifestyle_pref_alcohol: Optional[str] = None
    lifestyle_pref_dietary_match: Optional[bool] = False
    
    living_with_in_laws: Optional[str] = None
    living_arrangement_comment: Optional[str] = None
    fertility_comment: Optional[str] = None
    preferred_religion_comment: Optional[str] = None
    preferred_education_comment: Optional[str] = None
    career_support_expectations: Optional[str] = None
    career_support_comment: Optional[str] = None
    necessary_preferences: Optional[str] = None  # Accept as string (JSON)
    additional_comments: Optional[str] = None


class ProfileUpdate(ProfileCreate):
    is_completed: Optional[bool] = None


@router.post("/profile")
async def create_profile(
    profile_data: ProfileCreate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create a new profile for the authenticated user"""
    try:
        user_id = get_current_user_id(authorization, db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if profile already exists
        existing_profile = ProfileRepository.get_by_user_id(db, user_id)
        if existing_profile:
            raise HTTPException(status_code=400, detail="Profile already exists")
        
        # Get profile data
        profile_dict = profile_data.dict()
        name = profile_dict.pop("name", None)
        age = profile_dict.pop("age", None)
        date_of_birth = profile_dict.pop("date_of_birth", None)
        gender = profile_dict.pop("gender", None)
        religion = profile_dict.pop("religion", None)
        # genetic_conditions and necessary_preferences are already strings from frontend
        
        # Process base64 files
        if profile_dict.get('profile_picture'):
            data, filename, content_type = process_base64_file(profile_dict.pop('profile_picture'))
            if data:
                profile_dict['profile_picture_data'] = data
                profile_dict['profile_picture_filename'] = filename
                profile_dict['profile_picture_content_type'] = content_type
        
        if profile_dict.get('intro_video'):
            data, filename, content_type = process_base64_file(profile_dict.pop('intro_video'))
            if data:
                profile_dict['intro_video_data'] = data
                profile_dict['intro_video_filename'] = filename
                profile_dict['intro_video_content_type'] = content_type
        
        if profile_dict.get('medical_documents'):
            data, filename, content_type = process_base64_file(profile_dict.pop('medical_documents'))
            if data:
                profile_dict['medical_documents_data'] = data
                profile_dict['medical_documents_filename'] = filename
                profile_dict['medical_documents_content_type'] = content_type
        
        if name is not None:
            user.name = name
        if age is not None:
            user.age = age
        if date_of_birth:
            user.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        if gender is not None:
            user.gender = gender
        if religion is not None:
            user.religion = religion

        # Create profile
        profile = ProfileRepository.create(db, user_id, **profile_dict)

        return JSONResponse(
            content={
                "message": "Profile created successfully",
                "profile": {
                    **profile.to_dict(),
                    "name": user.name,
                    "age": user.age,
                    "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                    "gender": user.gender,
                    "religion": user.religion,
                }
            },
            status_code=201
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile")
async def get_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get the authenticated user's profile"""
    try:
        user_id = get_current_user_id(authorization, db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return JSONResponse(
            content={
                **profile.to_dict(),
                "name": user.name,
                "age": user.age,
                "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                "gender": user.gender,
                "religion": user.religion,
            },
            status_code=200
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Update the authenticated user's profile"""
    try:
        user_id = get_current_user_id(authorization, db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get profile data
        profile_dict = profile_data.dict(exclude_unset=True)
        name = profile_dict.pop("name", None)
        age = profile_dict.pop("age", None)
        date_of_birth = profile_dict.pop("date_of_birth", None)
        gender = profile_dict.pop("gender", None)
        religion = profile_dict.pop("religion", None)
        # genetic_conditions and necessary_preferences are already strings from frontend
        
        # Process base64 files
        if 'profile_picture' in profile_dict and profile_dict['profile_picture']:
            data, filename, content_type = process_base64_file(profile_dict.pop('profile_picture'))
            if data:
                profile_dict['profile_picture_data'] = data
                profile_dict['profile_picture_filename'] = filename
                profile_dict['profile_picture_content_type'] = content_type
        
        if 'intro_video' in profile_dict and profile_dict['intro_video']:
            data, filename, content_type = process_base64_file(profile_dict.pop('intro_video'))
            if data:
                profile_dict['intro_video_data'] = data
                profile_dict['intro_video_filename'] = filename
                profile_dict['intro_video_content_type'] = content_type
        
        if 'medical_documents' in profile_dict and profile_dict['medical_documents']:
            data, filename, content_type = process_base64_file(profile_dict.pop('medical_documents'))
            if data:
                profile_dict['medical_documents_data'] = data
                profile_dict['medical_documents_filename'] = filename
                profile_dict['medical_documents_content_type'] = content_type
        
        if name is not None:
            user.name = name
        if age is not None:
            user.age = age
        if date_of_birth is not None:
            user.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date() if date_of_birth else None
        if gender is not None:
            user.gender = gender
        if religion is not None:
            user.religion = religion

        # Update profile
        updated_profile = ProfileRepository.update(db, profile, **profile_dict)
        
        return JSONResponse(
            content={
                "message": "Profile updated successfully",
                "profile": {
                    **updated_profile.to_dict(),
                    "name": user.name,
                    "age": user.age,
                    "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                    "gender": user.gender,
                    "religion": user.religion,
                }
            },
            status_code=200
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile")
async def delete_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete the authenticated user's profile"""
    try:
        user_id = get_current_user_id(authorization, db)
        
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        ProfileRepository.delete(db, profile)
        
        return JSONResponse(
            content={"message": "Profile deleted successfully"},
            status_code=200
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles")
async def get_all_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all completed profiles (for matching purposes)"""
    try:
        profiles = ProfileRepository.get_all_completed_profiles(db, skip, limit)
        
        return JSONResponse(
            content={"profiles": [profile.to_dict() for profile in profiles]},
            status_code=200
        )
    except Exception as e:
        print(f"Error fetching profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_profile_by_user_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific user's profile by user ID"""
    try:
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return JSONResponse(content=profile.to_dict(), status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/picture/{user_id}")
async def get_profile_picture(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get profile picture for a user"""
    try:
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile or not profile.profile_picture_data:
            raise HTTPException(status_code=404, detail="Profile picture not found")
        
        return Response(
            content=profile.profile_picture_data,
            media_type=profile.profile_picture_content_type or "image/jpeg"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile picture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/video/{user_id}")
async def get_intro_video(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get intro video for a user"""
    try:
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile or not profile.intro_video_data:
            raise HTTPException(status_code=404, detail="Intro video not found")
        
        return Response(
            content=profile.intro_video_data,
            media_type=profile.intro_video_content_type or "video/mp4"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching intro video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/documents/{user_id}")
async def get_medical_documents(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get medical documents for a user"""
    try:
        profile = ProfileRepository.get_by_user_id(db, user_id)
        
        if not profile or not profile.medical_documents_data:
            raise HTTPException(status_code=404, detail="Medical documents not found")
        
        return Response(
            content=profile.medical_documents_data,
            media_type=profile.medical_documents_content_type or "application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching medical documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/browse")
async def browse_users(
    page: int = 1,
    limit: int = 20,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get brief profiles of all users for browsing (excluding current user) with pagination"""
    try:
        print(f"[BROWSE] Starting browse_users endpoint (page={page}, limit={limit})...")
        # Get current user ID
        if not authorization:
            print("[BROWSE] Missing Authorization header")
        current_user_id = get_current_user_id(authorization, db)
        print(f"[BROWSE] Current user ID: {current_user_id}")
        
        # Import here to avoid circular import
        from repositories.interest_repository.interest_repository import InterestRepository
        from models.profile.profile import Profile
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get total count
        total_users = db.query(User).count()
        blocked_ids = BlockRepository.get_blocked_user_ids(db, current_user_id)
        total_query = db.query(User).filter(
            User.id != current_user_id,
            User.is_deleted == False
        )
        if blocked_ids:
            total_query = total_query.filter(User.id.notin_(blocked_ids))

        total_count = total_query.count()
        print(f"[BROWSE] Total users in DB: {total_users}")
        
        # Get paginated users
        users_query = db.query(User).filter(
            User.id != current_user_id,
            User.is_deleted == False
        )
        if blocked_ids:
            users_query = users_query.filter(User.id.notin_(blocked_ids))

        users = users_query.offset(offset).limit(limit).all()
        print(f"[BROWSE] Found {len(users)} users on page {page} (total: {total_count})")
        if users:
            print(f"[BROWSE] First user on page: id={users[0].id} name={users[0].name}")
        
        result = []
        for user in users:
            profile = ProfileRepository.get_by_user_id(db, user.id)
            if not profile:
                print(f"[BROWSE] No profile found for user_id={user.id}")
            
            # Determine interest status with this user
            interest_status = "none"
            
            # Check if current user sent interest to this user
            sent_interest = InterestRepository.get_existing_interest(db, current_user_id, user.id)
            if sent_interest:
                if sent_interest.status == "pending":
                    interest_status = "pending_sent"
                elif sent_interest.status == "accepted":
                    interest_status = "accepted"
                elif sent_interest.status == "rejected":
                    interest_status = "rejected"
            
            # Check if this user sent interest to current user
            received_interest = InterestRepository.get_existing_interest(db, user.id, current_user_id)
            if received_interest:
                if received_interest.status == "pending":
                    interest_status = "pending_received"
                elif received_interest.status == "accepted":
                    interest_status = "accepted"
            
            # Convert profile picture to base64 if exists
            profile_picture_base64 = None
            if profile and profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(profile.profile_picture_data).decode('utf-8')
                    content_type = profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")
            
            nid_verified = user.verification_status == "verified"
            photo_verified = user.matching_percentage is not None and user.matching_percentage >= 70

            # Build brief profile with overview fields
            user_brief = {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "gender": user.gender,
                "religion": user.religion,
                "location": profile.location if profile else None,
                "profession": profile.profession if profile else None,
                "academic_background": profile.academic_background if profile else None,
                "profile_picture": profile_picture_base64,
                "interest_status": interest_status,
                "verification_status": user.verification_status,
                "matching_percentage": user.matching_percentage,
                "nid_verified": nid_verified,
                "photo_verified": photo_verified,
                # Additional overview fields
                "marital_status": profile.marital_status if profile else None,
                "height": profile.height if profile else None,
                "weight": profile.weight if profile else None,
                "interests": profile.interests if profile else None,
                "hobbies": profile.hobbies if profile else None,
                "dietary_preference": profile.dietary_preference if profile else None,
                "smoking_habit": profile.smoking_habit if profile else None,
                "alcohol_consumption": profile.alcohol_consumption if profile else None,
                "overall_health_status": profile.overall_health_status if profile else None,
                "blood_group": profile.blood_group if profile else None,
                "preferred_age_min": profile.preferred_age_min if profile else None,
                "preferred_age_max": profile.preferred_age_max if profile else None,
                "living_with_in_laws": profile.living_with_in_laws if profile else None,
                "willing_to_relocate": profile.willing_to_relocate if profile else None
            }
            
            result.append(user_brief)
        
        has_more = (offset + len(result)) < total_count
        
        print(f"[BROWSE] Returning {len(result)} users (has_more: {has_more})")
        return JSONResponse(content={
            "users": result,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "has_more": has_more
            }
        }, status_code=200)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[BROWSE ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/recommendations")
async def get_recommendations(
    page: int = 1,
    limit: int = 20,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get ML-ranked profile recommendations for the current user with pagination.
    Falls back to the regular browse list if the model is not trained yet."""
    try:
        print(f"[RECOMMENDATIONS] Starting recommendations endpoint (page={page}, limit={limit})...")
        current_user_id = get_current_user_id(authorization, db)
        print(f"[RECOMMENDATIONS] Current user ID: {current_user_id}")

        from repositories.interest_repository.interest_repository import InterestRepository
        from services.recommendation_service import get_recommendations as ml_recommend, is_ready
        blocked_ids = BlockRepository.get_blocked_user_ids(db, current_user_id)

        print("[RECOMMENDATIONS] Checking if ML model is ready...")
        ml_ready = is_ready()

        # Get ML-ranked user_id list (or None if user not in model index) - fetch more for pagination
        ranked_ids = ml_recommend(current_user_id, db, top_n=200) if ml_ready else None
        print(f"[RECOMMENDATIONS] ML ready: {ml_ready}, Ranked IDs count: {len(ranked_ids) if ranked_ids else 0}")

        # Fall back: all users except self when model is unavailable OR returns no candidates.
        if not ranked_ids:
            if ml_ready:
                print("[RECOMMENDATIONS] Model ready but returned no ranked users, falling back to all users")
            else:
                print("[RECOMMENDATIONS] ML not ready, falling back to all users")
            users_query = db.query(User).filter(
                User.id != current_user_id,
                User.is_deleted == False
            )
            if blocked_ids:
                users_query = users_query.filter(User.id.notin_(blocked_ids))
            users = users_query.all()
            ranked_ids = [u.id for u in users]
            print(f"[RECOMMENDATIONS] Fallback found {len(ranked_ids)} users")

        if blocked_ids:
            ranked_ids = [uid for uid in ranked_ids if uid not in blocked_ids]

        # Apply pagination to ranked_ids
        total_count = len(ranked_ids)
        offset = (page - 1) * limit
        paginated_ids = ranked_ids[offset:offset + limit]
        
        result = []
        print(f"[RECOMMENDATIONS] Processing {len(paginated_ids)} user IDs from page {page}...")
        for uid in paginated_ids:
            user = db.query(User).filter(User.id == uid).first()
            if not user or user.is_deleted:
                continue

            profile = ProfileRepository.get_by_user_id(db, uid)

            # Interest status
            interest_status = "none"
            sent_interest = InterestRepository.get_existing_interest(db, current_user_id, uid)
            if sent_interest:
                if sent_interest.status == "pending":
                    interest_status = "pending_sent"
                elif sent_interest.status == "accepted":
                    interest_status = "accepted"
                elif sent_interest.status == "rejected":
                    interest_status = "rejected"

            received_interest = InterestRepository.get_existing_interest(db, uid, current_user_id)
            if received_interest:
                if received_interest.status == "pending":
                    interest_status = "pending_received"
                elif received_interest.status == "accepted":
                    interest_status = "accepted"

            # Profile picture
            profile_picture_base64 = None
            if profile and profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(profile.profile_picture_data).decode('utf-8')
                    content_type = profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")

            nid_verified = user.verification_status == "verified"
            photo_verified = user.matching_percentage is not None and user.matching_percentage >= 70

            result.append({
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "gender": user.gender,
                "religion": user.religion,
                "location": profile.location if profile else None,
                "profession": profile.profession if profile else None,
                "academic_background": profile.academic_background if profile else None,
                "profile_picture": profile_picture_base64,
                "interest_status": interest_status,
                "verification_status": user.verification_status,
                "matching_percentage": user.matching_percentage,
                "nid_verified": nid_verified,
                "photo_verified": photo_verified,
                # Additional overview fields
                "marital_status": profile.marital_status if profile else None,
                "height": profile.height if profile else None,
                "weight": profile.weight if profile else None,
                "interests": profile.interests if profile else None,
                "hobbies": profile.hobbies if profile else None,
                "dietary_preference": profile.dietary_preference if profile else None,
                "smoking_habit": profile.smoking_habit if profile else None,
                "alcohol_consumption": profile.alcohol_consumption if profile else None,
                "overall_health_status": profile.overall_health_status if profile else None,
                "blood_group": profile.blood_group if profile else None,
                "preferred_age_min": profile.preferred_age_min if profile else None,
                "preferred_age_max": profile.preferred_age_max if profile else None,
                "living_with_in_laws": profile.living_with_in_laws if profile else None,
                "willing_to_relocate": profile.willing_to_relocate if profile else None
            })

        has_more = (offset + len(result)) < total_count
        
        print(f"[RECOMMENDATIONS] Returning {len(result)} users, ml_ready={ml_ready}, has_more={has_more}")
        return JSONResponse(
            content={
                "users": result,
                "ml_ready": ml_ready,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "has_more": has_more
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[RECOMMENDATIONS ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/profile/full")
async def get_full_profile(
    user_id: str,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get full profile of a user (only if mutual interest exists)"""
    try:
        # Get current user ID
        current_user_id = get_current_user_id(authorization, db)
        
        # Import here to avoid circular import
        from repositories.interest_repository.interest_repository import InterestRepository
        
        if BlockRepository.is_blocked_between(db, current_user_id, user_id):
            raise HTTPException(status_code=403, detail="You cannot view this profile")

        # Check if mutual interest exists
        has_mutual_interest = InterestRepository.check_mutual_interest(db, current_user_id, user_id)
        
        if not has_mutual_interest:
            raise HTTPException(
                status_code=403,
                detail="You can only view full profiles of users with mutual interest"
            )
        
        # Get user and profile
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = ProfileRepository.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        nid_verified = user.verification_status == "verified"
        photo_verified = user.matching_percentage is not None and user.matching_percentage >= 70

        # Return full profile with all details
        full_profile = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "age": user.age,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "religion": user.religion,
            "nid": user.nid,
            "verification_status": user.verification_status,
            "matching_percentage": user.matching_percentage,
            "nid_verified": nid_verified,
            "photo_verified": photo_verified,
            "profile": profile.to_dict()
        }
        
        return JSONResponse(content=full_profile, status_code=200)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching full profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
