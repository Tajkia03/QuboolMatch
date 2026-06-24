from datetime import datetime, date, time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from database import get_db
from models.user.user import User
from models.verification_rejection import VerificationRejection
from shared.token import get_current_user, get_current_admin_user
from pydantic import BaseModel
from typing import Optional
import base64
import os
import json
from google import genai
from google.genai import types
from config import get_settings

router = APIRouter()

class VerificationResponse(BaseModel):
    success: bool
    message: str
    verification_status: str

class VerificationStatusResponse(BaseModel):
    verification_status: str
    verification_date: Optional[str] = None
    verification_time: Optional[str] = None
    verified_at: Optional[str] = None
    verification_notes: Optional[str] = None
    rejection_notes: Optional[str] = None
    has_nid_image: bool = False
    nid_image_filename: Optional[str] = None
    has_recent_image: bool = False
    recent_image_filename: Optional[str] = None

@router.post("/submit", response_model=VerificationResponse)
async def submit_verification(
    verification_date: Optional[str] = Form(None),
    verification_time: Optional[str] = Form(None),
    verification_notes: Optional[str] = Form(None),
    nid_image: UploadFile = File(...),
    recent_image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit NID verification information including image, recent image, date, and time
    """
    try:
        # Validate NID image file type
        if not nid_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are allowed for NID image")
        
        # Validate file size (5MB limit)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        nid_image_data = await nid_image.read()
        if len(nid_image_data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="NID image file size exceeds 5MB limit")
        
        # Handle recent image if provided
        recent_image_data = None
        recent_image_filename = None
        recent_image_content_type = None
        
        if recent_image:
            if not recent_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are allowed for recent image")
            
            recent_image_data = await recent_image.read()
            if len(recent_image_data) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Recent image file size exceeds 5MB limit")
            
            recent_image_filename = recent_image.filename
            recent_image_content_type = recent_image.content_type
        
        # Parse date and time only if provided
        parsed_date = None
        parsed_time = None
        if verification_date:
            try:
                parsed_date = datetime.strptime(verification_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        if verification_time:
            try:
                parsed_time = datetime.strptime(verification_time, "%H:%M").time()
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")
        
        # Update user verification info with binary data
        current_user.update_verification_info(
            nid_image_data=nid_image_data,
            nid_image_filename=nid_image.filename,
            nid_image_content_type=nid_image.content_type,
            recent_image_data=recent_image_data,
            recent_image_filename=recent_image_filename,
            recent_image_content_type=recent_image_content_type,
            verification_date=parsed_date,
            verification_time=parsed_time,
            verification_notes=verification_notes
        )
        db.query(VerificationRejection).filter(
            VerificationRejection.user_id == current_user.id
        ).delete()
        
        # Commit changes to database
        db.commit()
        
        return VerificationResponse(
            success=True,
            message="Verification information submitted successfully",
            verification_status=current_user.verification_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit verification: {str(e)}")

@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current verification status for the user
    """
    rejection = db.query(VerificationRejection).filter(
        VerificationRejection.user_id == current_user.id
    ).first()

    return VerificationStatusResponse(
        verification_status=current_user.verification_status,
        verification_date=current_user.verification_date.isoformat() if current_user.verification_date else None,
        verification_time=current_user.verification_time.isoformat() if current_user.verification_time else None,
        verified_at=current_user.verified_at.isoformat() if current_user.verified_at else None,
        verification_notes=current_user.verification_notes,
        rejection_notes=rejection.notes if rejection else None,
        has_nid_image=bool(current_user.nid_image_data),
        nid_image_filename=current_user.nid_image_filename,
        has_recent_image=bool(current_user.recent_image_data),
        recent_image_filename=current_user.recent_image_filename
    )

@router.get("/image")
async def get_verification_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the NID image for the current user
    """
    if not current_user.nid_image_data:
        raise HTTPException(status_code=404, detail="No NID image found")
    
    return Response(
        content=current_user.nid_image_data,
        media_type=current_user.nid_image_content_type or "image/jpeg"
    )

@router.get("/image/{user_id}")
async def get_user_verification_image(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to get NID image for any user
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.nid_image_data:
        raise HTTPException(status_code=404, detail="No NID image found for this user")
    
    return Response(
        content=user.nid_image_data,
        media_type=user.nid_image_content_type or "image/jpeg"
    )

@router.get("/image-base64")
async def get_verification_image_base64(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the NID image as base64 encoded string for the current user
    """
    if not current_user.nid_image_data:
        raise HTTPException(status_code=404, detail="No NID image found")
    
    # Convert binary data to base64
    image_base64 = base64.b64encode(current_user.nid_image_data).decode('utf-8')
    
    return {
        "image_data": image_base64,
        "content_type": current_user.nid_image_content_type,
        "filename": current_user.nid_image_filename
    }

@router.get("/recent-image")
async def get_recent_verification_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the recent verification image for the current user
    """
    if not current_user.recent_image_data:
        raise HTTPException(status_code=404, detail="No recent image found")
    
    return Response(
        content=current_user.recent_image_data,
        media_type=current_user.recent_image_content_type or "image/jpeg"
    )

@router.get("/recent-image/{user_id}")
async def get_user_recent_verification_image(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to get recent verification image for any user
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.recent_image_data:
        raise HTTPException(status_code=404, detail="No recent image found for this user")
    
    return Response(
        content=user.recent_image_data,
        media_type=user.recent_image_content_type or "image/jpeg"
    )

@router.post("/approve/{user_id}")
async def approve_verification(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to approve user verification
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.verify()
    db.query(VerificationRejection).filter(
        VerificationRejection.user_id == user_id
    ).delete()
    db.commit()
    
    return {"success": True, "message": "User verification approved"}

@router.post("/reject/{user_id}")
async def reject_verification(
    user_id: str,
    rejection_notes: str = Form(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to reject user verification
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.reject_verification(rejection_notes)
    existing_rejection = db.query(VerificationRejection).filter(
        VerificationRejection.user_id == user_id
    ).first()
    if existing_rejection:
        existing_rejection.notes = rejection_notes
    else:
        db.add(VerificationRejection(user_id=user_id, notes=rejection_notes))
    db.commit()
    
    return {"success": True, "message": "User verification rejected"}

@router.post("/guardian/approve/{user_id}")
async def approve_guardian_verification(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to approve guardian verification
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.verify_guardian()
    db.commit()

    return {"success": True, "message": "Guardian verification approved"}

@router.post("/guardian/reject/{user_id}")
async def reject_guardian_verification(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to reject guardian verification
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.reject_guardian_verification()
    db.commit()

    return {"success": True, "message": "Guardian verification rejected"}

@router.get("/pending")
async def get_pending_verifications(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to get all pending verifications
    """
    pending_users = db.query(User).filter(
        User.verification_status.in_(["pending", "in_progress"]),
        User.is_deleted == False
    ).all()
    
    return {
        "pending_verifications": [
            {
                "id": user.id,
                "email": user.email,
                "verification_status": user.verification_status,
                "verification_date": user.verification_date.isoformat() if user.verification_date else None,
                "verification_time": user.verification_time.isoformat() if user.verification_time else None,
                "has_nid_image": bool(user.nid_image_data),
                "nid_image_filename": user.nid_image_filename,
                "has_recent_image": bool(user.recent_image_data),
                "recent_image_filename": user.recent_image_filename,
                "verification_notes": user.verification_notes,
                "created_at": user.created_at.isoformat(),
                "matching_percentage": user.matching_percentage,
                "guardian_verification_status": user.guardian_verification_status
            }
            for user in pending_users
        ]
    }

@router.post("/match-images/{user_id}")
async def match_verification_images(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to match NID image with recent verification image using Gemini AI.
    Returns a matching percentage indicating how similar the two faces are.
    """
    # Retrieve user from database
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate that both images exist
    if not user.nid_image_data:
        return {
            "success": False,
            "error": "NID image not found. User must upload NID image first."
        }
    
    if not user.recent_image_data:
        return {
            "success": False,
            "error": "Recent verification image not found. User must upload recent image first."
        }
    
    try:
        # Get Gemini API key from settings
        settings = get_settings()
        api_key = settings.GEMINI_API_KEY
        
        if not api_key:
            return {
                "success": False,
                "error": "Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
            }
        
        # Convert binary images to base64
        nid_image_base64 = base64.b64encode(user.nid_image_data).decode('utf-8')
        recent_image_base64 = base64.b64encode(user.recent_image_data).decode('utf-8')
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Prepare content with both images
        model = "gemini-2.5-flash-lite"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="Compare these two photos and determine if they show the same person. "
                             "Analyze facial features including face shape, eyes, nose, mouth, and overall appearance. "
                             "Return a matching percentage from 0-100 where 100 means definitely the same person "
                             "and 0 means definitely different people. Be strict in your assessment."
                    ),
                    types.Part.from_bytes(
                        data=user.nid_image_data,
                        mime_type=user.nid_image_content_type or "image/jpeg"
                    ),
                    types.Part.from_bytes(
                        data=user.recent_image_data,
                        mime_type=user.recent_image_content_type or "image/jpeg"
                    ),
                ],
            ),
        ]
        
        # Configure response with structured output
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                required=["matchingPercentage"],
                properties={
                    "matchingPercentage": types.Schema(
                        type=types.Type.NUMBER,
                    ),
                },
            ),
        )
        
        # Call Gemini API and collect full response
        full_response = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                full_response += chunk.text
        
        # Parse JSON response
        result = json.loads(full_response)
        matching_percentage = float(result.get("matchingPercentage", 0))
        
        # Ensure percentage is within valid range
        matching_percentage = max(0.0, min(100.0, matching_percentage))
        
        # Save matching percentage to database
        user.matching_percentage = matching_percentage
        db.commit()
        
        return {
            "success": True,
            "matchingPercentage": matching_percentage
        }
        
    except json.JSONDecodeError as e:
        # Set matching percentage to null on error
        user.matching_percentage = None
        db.commit()
        return {
            "success": False,
            "error": f"Failed to parse AI response: {str(e)}"
        }
    except Exception as e:
        # Set matching percentage to null on error
        user.matching_percentage = None
        db.commit()
        return {
            "success": False,
            "error": f"Failed to match images: {str(e)}"
        }
