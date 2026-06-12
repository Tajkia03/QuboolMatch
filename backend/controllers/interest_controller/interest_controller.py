from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_db
from repositories.interest_repository.interest_repository import InterestRepository
from repositories.notification_repository.notification_repository import NotificationRepository
from repositories.user_repository.user_repository import UserRepository
from repositories.profile_repository.profile_repository import ProfileRepository
from repositories.block_repository import BlockRepository
from shared.token import get_current_user
from models.user.user import User
from typing import Optional
import base64

router = APIRouter()


class SendInterestRequest(BaseModel):
    to_user_id: str
    message: Optional[str] = None


class InterestActionRequest(BaseModel):
    interest_id: str


@router.post("/interests/send")
async def send_interest(
    params: SendInterestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send interest to another user."""
    try:
        # Validate that the recipient exists
        recipient = UserRepository.get_by_id(db, params.to_user_id)
        if not recipient:
            raise HTTPException(status_code=404, detail="User not found")

        if BlockRepository.is_blocked_between(db, current_user.id, params.to_user_id):
            raise HTTPException(status_code=403, detail="You cannot send interest to this user")
        
        # Cannot send interest to yourself
        if current_user.id == params.to_user_id:
            raise HTTPException(status_code=400, detail="Cannot send interest to yourself")
        
        # Check if sender has reached the limit (3 active sent interests: pending + accepted)
        sender_active_count = InterestRepository.count_active_sent_interests(db, current_user.id)
        if sender_active_count >= 3:
            raise HTTPException(
                status_code=403,
                detail="You have reached the maximum limit of 3 active interests. Please wait for responses or withdraw pending interests."
            )
        
        # Check if interest already exists
        existing_interest = InterestRepository.get_existing_interest(
            db, current_user.id, params.to_user_id
        )
        if existing_interest:
            raise HTTPException(
                status_code=400,
                detail=f"Interest already exists with status: {existing_interest.status}"
            )
        
        # Check if there's a reverse interest
        reverse_interest = InterestRepository.get_existing_interest(
            db, params.to_user_id, current_user.id
        )
        if reverse_interest:
            raise HTTPException(
                status_code=400,
                detail="This user has already sent you an interest. Please respond to their request."
            )
        
        # Create the interest
        interest = InterestRepository.create(
            db,
            from_user_id=current_user.id,
            to_user_id=params.to_user_id,
            message=params.message
        )
        
        # Create notification for the recipient
        NotificationRepository.create(
            db,
            user_id=params.to_user_id,
            notification_type="interest_received",
            message=f"{current_user.name} has sent you an interest",
            from_user_id=current_user.id,
            related_id=interest.id
        )
        
        return JSONResponse(
            content={
                "message": "Interest sent successfully",
                "interest": interest.to_dict()
            },
            status_code=201
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interests/received")
async def get_received_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all interests received by the current user."""
    try:
        interests = InterestRepository.get_received(db, current_user.id)
        blocked_ids = BlockRepository.get_blocked_user_ids(db, current_user.id)
        
        # Enrich with sender information
        result = []
        for interest in interests:
            if interest.from_user_id in blocked_ids:
                continue
            sender = UserRepository.get_by_id(db, interest.from_user_id)
            sender_profile = ProfileRepository.get_by_user_id(db, interest.from_user_id)
            
            # Convert profile picture to base64 if exists
            profile_picture_base64 = None
            if sender_profile and sender_profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(sender_profile.profile_picture_data).decode('utf-8')
                    content_type = sender_profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")
            
            interest_dict = interest.to_dict()
            interest_dict["from_user"] = {
                "id": sender.id,
                "name": sender.name,
                "age": sender.age,
                "religion": sender.religion,
                "profile_picture": profile_picture_base64
            }
            result.append(interest_dict)
        
        return JSONResponse(content={"interests": result}, status_code=200)
    
    except Exception as e:
        print(f"Error fetching received interests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interests/sent")
async def get_sent_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all interests sent by the current user."""
    try:
        interests = InterestRepository.get_sent(db, current_user.id)
        blocked_ids = BlockRepository.get_blocked_user_ids(db, current_user.id)
        
        # Enrich with recipient information
        result = []
        for interest in interests:
            if interest.to_user_id in blocked_ids:
                continue
            recipient = UserRepository.get_by_id(db, interest.to_user_id)
            recipient_profile = ProfileRepository.get_by_user_id(db, interest.to_user_id)
            
            # Convert profile picture to base64 if exists
            profile_picture_base64 = None
            if recipient_profile and recipient_profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(recipient_profile.profile_picture_data).decode('utf-8')
                    content_type = recipient_profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")
            
            interest_dict = interest.to_dict()
            interest_dict["to_user"] = {
                "id": recipient.id,
                "name": recipient.name,
                "age": recipient.age,
                "religion": recipient.religion,
                "profile_picture": profile_picture_base64
            }
            result.append(interest_dict)
        
        return JSONResponse(content={"interests": result}, status_code=200)
    
    except Exception as e:
        print(f"Error fetching sent interests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/interests/{interest_id}/accept")
async def accept_interest(
    interest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept an interest request."""
    try:
        # Get the interest
        interest = InterestRepository.get_by_id(db, interest_id)
        if not interest:
            raise HTTPException(status_code=404, detail="Interest not found")
        
        # Verify the current user is the recipient
        if interest.to_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only accept interests sent to you")
        
        # Check if already processed
        if interest.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Interest has already been {interest.status}"
            )
        
        # Check if acceptor has reached the limit (3 accepted interests)
        acceptor_count = InterestRepository.count_accepted_interests(db, current_user.id)
        if acceptor_count >= 3:
            raise HTTPException(
                status_code=403,
                detail="You have reached the maximum limit of 3 mutual interests"
            )
        
        # Check if sender still has room (they might have accepted others since sending)
        sender_count = InterestRepository.count_accepted_interests(db, interest.from_user_id)
        if sender_count >= 3:
            raise HTTPException(
                status_code=403,
                detail="The sender has reached their interest limit. Cannot accept."
            )
        
        # Update interest status to accepted
        updated_interest = InterestRepository.update_status(db, interest, "accepted")
        
        # Create notification for the sender
        sender = UserRepository.get_by_id(db, interest.from_user_id)
        NotificationRepository.create(
            db,
            user_id=interest.from_user_id,
            notification_type="interest_accepted",
            message=f"{current_user.name} has accepted your interest",
            from_user_id=current_user.id,
            related_id=interest.id
        )
        
        return JSONResponse(
            content={
                "message": "Interest accepted successfully",
                "interest": updated_interest.to_dict()
            },
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error accepting interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/interests/{interest_id}/reject")
async def reject_interest(
    interest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an interest request."""
    try:
        # Get the interest
        interest = InterestRepository.get_by_id(db, interest_id)
        if not interest:
            raise HTTPException(status_code=404, detail="Interest not found")
        
        # Verify the current user is the recipient
        if interest.to_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only reject interests sent to you")
        
        # Check if already processed
        if interest.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Interest has already been {interest.status}"
            )
        
        # Update interest status to rejected
        updated_interest = InterestRepository.update_status(db, interest, "rejected")
        
        # Create notification for the sender
        NotificationRepository.create(
            db,
            user_id=interest.from_user_id,
            notification_type="interest_rejected",
            message=f"{current_user.name} has declined your interest",
            from_user_id=current_user.id,
            related_id=interest.id
        )
        
        return JSONResponse(
            content={
                "message": "Interest rejected successfully",
                "interest": updated_interest.to_dict()
            },
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error rejecting interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/interests/{interest_id}/cancel")
async def cancel_interest(
    interest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a sent interest (only pending interests can be canceled)."""
    try:
        # Get the interest
        interest = InterestRepository.get_by_id(db, interest_id)
        if not interest:
            raise HTTPException(status_code=404, detail="Interest not found")
        
        # Verify the current user is the sender
        if interest.from_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only cancel interests you sent")
        
        # Only allow canceling pending interests
        if interest.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel an interest that has been {interest.status}"
            )
        
        # Delete the interest
        InterestRepository.delete(db, interest)
        
        # Optionally notify the recipient that interest was withdrawn
        NotificationRepository.create(
            db,
            user_id=interest.to_user_id,
            notification_type="interest_canceled",
            message=f"{current_user.name} has withdrawn their interest",
            from_user_id=current_user.id,
            related_id=None  # Interest is deleted, so no related_id
        )
        
        return JSONResponse(
            content={
                "message": "Interest canceled successfully"
            },
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error canceling interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interests/matches")
async def get_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all accepted interests (matches) for the current user."""
    try:
        print(f"[MATCHES] Fetching matches for user_id={current_user.id}")
        matches = InterestRepository.get_all_accepted(db, current_user.id)
        print(f"[MATCHES] Found {len(matches)} accepted interests")
        blocked_ids = BlockRepository.get_blocked_user_ids(db, current_user.id)
        
        # Enrich with other user's information
        result = []
        for interest in matches:
            # Determine who the other user is
            other_user_id = (
                interest.to_user_id if interest.from_user_id == current_user.id
                else interest.from_user_id
            )

            if other_user_id in blocked_ids:
                continue
            
            other_user = UserRepository.get_by_id(db, other_user_id)
            other_profile = ProfileRepository.get_by_user_id(db, other_user_id)
            print(
                f"[MATCHES] interest_id={interest.id} other_user_id={other_user_id} "
                f"user_exists={other_user is not None} profile_exists={other_profile is not None}"
            )
            
            # Convert profile picture to base64 if exists
            profile_picture_base64 = None
            if other_profile and other_profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(other_profile.profile_picture_data).decode('utf-8')
                    content_type = other_profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")
            
            match_dict = interest.to_dict()
            nid_verified = other_user.verification_status == "verified"
            photo_verified = other_user.matching_percentage is not None and other_user.matching_percentage >= 70

            match_dict["matched_user"] = {
                "id": other_user.id,
                "name": other_user.name,
                "age": other_user.age,
                "religion": other_user.religion,
                "profile_picture": profile_picture_base64,
                "verification_status": other_user.verification_status,
                "matching_percentage": other_user.matching_percentage,
                "nid_verified": nid_verified,
                "photo_verified": photo_verified
            }
            result.append(match_dict)
        
        return JSONResponse(content={"matches": result}, status_code=200)
    
    except Exception as e:
        print(f"Error fetching matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))
