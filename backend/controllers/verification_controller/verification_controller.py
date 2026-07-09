import json
import logging
from difflib import SequenceMatcher
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from database import get_db
from models.user.user import User
from models.verification_rejection import VerificationRejection
from repositories.profile_repository.profile_repository import ProfileRepository
from shared.token import get_current_user, get_current_admin_user
from pydantic import BaseModel, Field
import base64
from services.gemini_nid_ocr_service import (
    NIDOcrExtractionError,
    NIDOcrExtractionResult,
    ocr_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_NID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_NID_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

class VerificationResponse(BaseModel):
    success: bool
    message: str
    verification_status: str

class VerificationStatusResponse(BaseModel):
    verification_status: str
    name: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    nid: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    identity_verified: bool = False
    verified_at: Optional[str] = None
    verification_notes: Optional[str] = None
    rejection_notes: Optional[str] = None
    ocr_name: Optional[str] = None
    ocr_father_name: Optional[str] = None
    ocr_mother_name: Optional[str] = None
    ocr_date_of_birth: Optional[str] = None
    ocr_nid_number: Optional[str] = None
    ocr_nid_masked: Optional[str] = None
    ocr_blood_group: Optional[str] = None
    ocr_image_quality: Optional[str] = None
    ocr_warnings: list[str] = Field(default_factory=list)
    ocr_confirmed: bool = False
    ocr_processed_at: Optional[str] = None
    ocr_name_match_score: Optional[float] = None
    ocr_name_match_status: Optional[str] = None
    ocr_nid_match: Optional[bool] = None
    ocr_dob_match: Optional[bool] = None
    ocr_review_status: Optional[str] = None
    admin_review_notes: Optional[str] = None
    has_nid_image: bool = False
    nid_image_filename: Optional[str] = None


class PendingVerificationUserResponse(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    nid: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    identity_verified: bool = False
    verification_status: str
    verification_notes: Optional[str] = None
    guardian_verification_status: str
    has_nid_image: bool = False
    nid_image_filename: Optional[str] = None
    created_at: str
    ocr_name: Optional[str] = None
    ocr_father_name: Optional[str] = None
    ocr_mother_name: Optional[str] = None
    ocr_date_of_birth: Optional[str] = None
    ocr_nid_number: Optional[str] = None
    ocr_nid_masked: Optional[str] = None
    ocr_image_quality: Optional[str] = None
    ocr_warnings: list[str] = Field(default_factory=list)
    ocr_confirmed: bool = False
    ocr_processed_at: Optional[str] = None
    ocr_name_match_score: Optional[float] = None
    ocr_name_match_status: Optional[str] = None
    ocr_nid_match: Optional[bool] = None
    ocr_dob_match: Optional[bool] = None
    ocr_review_status: Optional[str] = None
    admin_review_notes: Optional[str] = None


class PendingVerificationsResponse(BaseModel):
    pending_verifications: list[PendingVerificationUserResponse]


class OcrConfirmationUpdateRequest(BaseModel):
    ocr_confirmed: bool


class OcrConfirmationUpdateResponse(BaseModel):
    success: bool
    message: str
    ocr_confirmed: bool


class AdminVerificationCorrectionRequest(BaseModel):
    reason: str = Field(min_length=1)


class CorrectSubmittedIdentityRequest(BaseModel):
    name: str = Field(min_length=1)
    nid: str = Field(min_length=1)
    age: Optional[int] = None
    date_of_birth: Optional[str] = None


class SimpleVerificationActionResponse(BaseModel):
    success: bool
    message: str
    verification_status: str


class NIDOcrExtractionResponse(BaseModel):
    success: bool
    message: str
    document_detected: bool = False
    name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nid_number: Optional[str] = None
    image_quality: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


def _build_ocr_response(
    *,
    success: bool,
    message: str,
    extraction: Optional[NIDOcrExtractionResult] = None,
) -> NIDOcrExtractionResponse:
    if not extraction:
        return NIDOcrExtractionResponse(
            success=success,
            message=message,
            warnings=[],
        )

    return NIDOcrExtractionResponse(
        success=success,
        message=message,
        document_detected=extraction.document_detected,
        name=extraction.name,
        father_name=extraction.father_name,
        mother_name=extraction.mother_name,
        date_of_birth=extraction.date_of_birth,
        nid_number=extraction.nid_number,
        image_quality=extraction.image_quality,
        warnings=extraction.warnings,
    )


def _parse_ocr_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_ocr_warnings(value) -> Optional[list[str]]:
    if value is None:
        return None

    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized or None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [stripped]

        if isinstance(parsed, list):
            normalized = [str(item).strip() for item in parsed if str(item).strip()]
            return normalized or None
        if isinstance(parsed, str) and parsed.strip():
            return [parsed.strip()]
        return None

    return None


def _normalize_nid_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    digits_only = "".join(char for char in value if char.isdigit())
    return digits_only or None


def _is_valid_nid(value: Optional[str]) -> bool:
    normalized = _normalize_nid_value(value)
    return bool(normalized) and len(normalized) in {10, 13, 17}


def _calculate_age_from_date_of_birth(date_of_birth: date) -> int:
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _parse_user_date_of_birth(value: Optional[str]) -> Optional[date]:
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date_of_birth must use YYYY-MM-DD format")


def _optional_string(value) -> Optional[str]:
    return value if isinstance(value, str) else None


def _optional_int(value) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_float(value) -> Optional[float]:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _optional_bool(value) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _optional_isoformat(value) -> Optional[str]:
    if not isinstance(value, (date, datetime)):
        return None
    return value.isoformat()


def _normalize_text_for_comparison(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _mask_nid_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    return trimmed.replace(" ", "").replace("-", "").replace(".", "").replace("\u00b7", "")


def _format_nid_masked(value: Optional[str]) -> Optional[str]:
    normalized = _mask_nid_number(value)
    if not normalized:
        return None

    if len(normalized) <= 4:
        return normalized

    return "*" * (len(normalized) - 4) + normalized[-4:]


def _compute_name_match_score(submitted_name: Optional[str], ocr_name: Optional[str]) -> Optional[float]:
    normalized_submitted = _normalize_text_for_comparison(submitted_name)
    normalized_ocr = _normalize_text_for_comparison(ocr_name)
    if not normalized_submitted or not normalized_ocr:
        return None

    return round(SequenceMatcher(None, normalized_submitted, normalized_ocr).ratio(), 4)


def _derive_name_match_status(
    submitted_name: Optional[str],
    ocr_name: Optional[str],
    score: Optional[float],
) -> Optional[str]:
    if not _normalize_text_for_comparison(submitted_name) or not _normalize_text_for_comparison(ocr_name):
        return None

    if score is None:
        return None

    if score >= 0.9:
        return "matched"
    if score >= 0.65:
        return "needs_review"
    return "does_not_match"


def _derive_nid_match(submitted_nid: Optional[str], ocr_nid: Optional[str]) -> Optional[bool]:
    normalized_submitted = _normalize_nid_value(submitted_nid)
    normalized_ocr = _normalize_nid_value(ocr_nid)
    if not normalized_submitted or not normalized_ocr:
        return None

    return normalized_submitted == normalized_ocr


def _derive_dob_match(
    submitted_date_of_birth: Optional[date],
    submitted_age: Optional[int],
    ocr_date_of_birth: Optional[date],
) -> Optional[bool]:
    if submitted_date_of_birth and ocr_date_of_birth:
        return submitted_date_of_birth == ocr_date_of_birth

    if submitted_age is not None and ocr_date_of_birth:
        today = date.today()
        derived_age = today.year - ocr_date_of_birth.year - (
            (today.month, today.day) < (ocr_date_of_birth.month, ocr_date_of_birth.day)
        )
        return derived_age == submitted_age

    return None


def _build_comparison_payload(user: User) -> dict[str, object]:
    submitted_name = _optional_string(getattr(user, "name", None))
    submitted_nid = _optional_string(getattr(user, "nid", None))
    submitted_date_of_birth = getattr(user, "date_of_birth", None) if isinstance(getattr(user, "date_of_birth", None), date) else None
    submitted_age = _optional_int(getattr(user, "age", None))
    ocr_name = _optional_string(getattr(user, "ocr_name", None))
    ocr_nid_number = _optional_string(getattr(user, "ocr_nid_number", None))
    ocr_date_of_birth_obj = getattr(user, "ocr_date_of_birth", None) if isinstance(getattr(user, "ocr_date_of_birth", None), date) else None
    ocr_date_of_birth = _optional_isoformat(ocr_date_of_birth_obj)

    ocr_name_match_score = _optional_float(getattr(user, "ocr_name_match_score", None))
    if ocr_name_match_score is None:
        ocr_name_match_score = _compute_name_match_score(submitted_name, ocr_name)

    ocr_name_match_status = _optional_string(getattr(user, "ocr_name_match_status", None))
    if ocr_name_match_status is None:
        ocr_name_match_status = _derive_name_match_status(submitted_name, ocr_name, ocr_name_match_score)

    ocr_nid_match = _optional_bool(getattr(user, "ocr_nid_match", None))
    if ocr_nid_match is None:
        ocr_nid_match = _derive_nid_match(submitted_nid, ocr_nid_number)

    ocr_dob_match = _optional_bool(getattr(user, "ocr_dob_match", None))
    if ocr_dob_match is None:
        ocr_dob_match = _derive_dob_match(submitted_date_of_birth, submitted_age, ocr_date_of_birth_obj)

    ocr_review_status = _optional_string(getattr(user, "ocr_review_status", None)) or (
        "pending_review" if getattr(user, "ocr_processed_at", None) else None
    )

    return {
        "ocr_name_match_score": ocr_name_match_score,
        "ocr_name_match_status": ocr_name_match_status,
        "ocr_nid_match": ocr_nid_match,
        "ocr_dob_match": ocr_dob_match,
        "ocr_review_status": ocr_review_status,
        "admin_review_notes": _optional_string(getattr(user, "admin_review_notes", None)),
        "ocr_date_of_birth": ocr_date_of_birth,
        "ocr_nid_masked": _format_nid_masked(ocr_nid_number),
    }


def _build_pending_user_response(user: User) -> PendingVerificationUserResponse:
    comparison_payload = _build_comparison_payload(user)
    return PendingVerificationUserResponse(
        id=user.id,
        name=_optional_string(getattr(user, "name", None)),
        email=_optional_string(getattr(user, "email", None)) or "",
        age=_optional_int(getattr(user, "age", None)),
        date_of_birth=_optional_isoformat(getattr(user, "date_of_birth", None)),
        nid=_format_nid_masked(_optional_string(getattr(user, "nid", None))),
        father_name=_optional_string(getattr(user, "father_name", None)),
        mother_name=_optional_string(getattr(user, "mother_name", None)),
        identity_verified=_optional_bool(getattr(user, "identity_verified", False)) or False,
        verification_status=_optional_string(getattr(user, "verification_status", None)) or "",
        verification_notes=_optional_string(getattr(user, "verification_notes", None)),
        guardian_verification_status=_optional_string(getattr(user, "guardian_verification_status", None)) or "",
        has_nid_image=isinstance(getattr(user, "nid_image_data", None), (bytes, bytearray)),
        nid_image_filename=_optional_string(getattr(user, "nid_image_filename", None)),
        created_at=_optional_isoformat(getattr(user, "created_at", None)) or "",
        ocr_name=_optional_string(getattr(user, "ocr_name", None)),
        ocr_father_name=_optional_string(getattr(user, "ocr_father_name", None)),
        ocr_mother_name=_optional_string(getattr(user, "ocr_mother_name", None)),
        ocr_date_of_birth=comparison_payload["ocr_date_of_birth"],
        ocr_nid_number=_optional_string(getattr(user, "ocr_nid_number", None)),
        ocr_nid_masked=comparison_payload["ocr_nid_masked"],
        ocr_image_quality=_optional_string(getattr(user, "ocr_image_quality", None)),
        ocr_warnings=_normalize_ocr_warnings(getattr(user, "ocr_warnings", None)) or [],
        ocr_confirmed=_optional_bool(getattr(user, "ocr_confirmed", False)) or False,
        ocr_processed_at=_optional_isoformat(getattr(user, "ocr_processed_at", None)),
        ocr_name_match_score=comparison_payload["ocr_name_match_score"],
        ocr_name_match_status=comparison_payload["ocr_name_match_status"],
        ocr_nid_match=comparison_payload["ocr_nid_match"],
        ocr_dob_match=comparison_payload["ocr_dob_match"],
        ocr_review_status=comparison_payload["ocr_review_status"],
        admin_review_notes=comparison_payload["admin_review_notes"],
    )


def _build_status_response(user: User, rejection_notes: Optional[str]) -> VerificationStatusResponse:
    comparison_payload = _build_comparison_payload(user)
    return VerificationStatusResponse(
        verification_status=_optional_string(getattr(user, "verification_status", None)) or "",
        name=_optional_string(getattr(user, "name", None)),
        age=_optional_int(getattr(user, "age", None)),
        date_of_birth=_optional_isoformat(getattr(user, "date_of_birth", None)),
        nid=_format_nid_masked(_optional_string(getattr(user, "nid", None))),
        father_name=_optional_string(getattr(user, "father_name", None)),
        mother_name=_optional_string(getattr(user, "mother_name", None)),
        identity_verified=_optional_bool(getattr(user, "identity_verified", False)) or False,
        verified_at=_optional_isoformat(getattr(user, "verified_at", None)),
        verification_notes=_optional_string(getattr(user, "verification_notes", None)),
        rejection_notes=rejection_notes,
        ocr_name=_optional_string(getattr(user, "ocr_name", None)),
        ocr_father_name=_optional_string(getattr(user, "ocr_father_name", None)),
        ocr_mother_name=_optional_string(getattr(user, "ocr_mother_name", None)),
        ocr_date_of_birth=comparison_payload["ocr_date_of_birth"],
        ocr_nid_number=_optional_string(getattr(user, "ocr_nid_number", None)),
        ocr_nid_masked=comparison_payload["ocr_nid_masked"],
        ocr_image_quality=_optional_string(getattr(user, "ocr_image_quality", None)),
        ocr_warnings=_normalize_ocr_warnings(getattr(user, "ocr_warnings", None)) or [],
        ocr_confirmed=_optional_bool(getattr(user, "ocr_confirmed", False)) or False,
        ocr_processed_at=_optional_isoformat(getattr(user, "ocr_processed_at", None)),
        ocr_name_match_score=comparison_payload["ocr_name_match_score"],
        ocr_name_match_status=comparison_payload["ocr_name_match_status"],
        ocr_nid_match=comparison_payload["ocr_nid_match"],
        ocr_dob_match=comparison_payload["ocr_dob_match"],
        ocr_review_status=comparison_payload["ocr_review_status"],
        admin_review_notes=comparison_payload["admin_review_notes"],
        has_nid_image=isinstance(getattr(user, "nid_image_data", None), (bytes, bytearray)),
        nid_image_filename=_optional_string(getattr(user, "nid_image_filename", None)),
    )


def _update_verified_identity_from_ocr(user: User) -> None:
    ocr_nid = _normalize_nid_value(getattr(user, "ocr_nid_number", None))
    official_nid = _normalize_nid_value(getattr(user, "nid", None))
    normalized_nid = ocr_nid if ocr_nid and _is_valid_nid(ocr_nid) else official_nid
    if not normalized_nid or not _is_valid_nid(normalized_nid):
        raise HTTPException(
            status_code=400,
            detail="A valid NID number is required before approval",
        )

    name = _optional_string(getattr(user, "ocr_name", None)) or _optional_string(getattr(user, "name", None))
    father_name = _optional_string(getattr(user, "ocr_father_name", None)) or _optional_string(getattr(user, "father_name", None))
    mother_name = _optional_string(getattr(user, "ocr_mother_name", None)) or _optional_string(getattr(user, "mother_name", None))

    ocr_date_of_birth = getattr(user, "ocr_date_of_birth", None)
    official_date_of_birth = getattr(user, "date_of_birth", None)
    chosen_date_of_birth = ocr_date_of_birth if isinstance(ocr_date_of_birth, date) else official_date_of_birth
    chosen_age = _calculate_age_from_date_of_birth(chosen_date_of_birth) if isinstance(chosen_date_of_birth, date) else _optional_int(getattr(user, "age", None))

    user.set_official_identity(
        name=name,
        nid=normalized_nid,
        date_of_birth=chosen_date_of_birth if isinstance(chosen_date_of_birth, date) else None,
        age=chosen_age,
        father_name=father_name,
        mother_name=mother_name,
    )
    user.verify()
    user.ocr_review_status = "approved"


def _clear_comparison_fields(user: User) -> None:
    user.ocr_name_match_score = None
    user.ocr_name_match_status = None
    user.ocr_nid_match = None
    user.ocr_dob_match = None
    user.ocr_review_status = None


@router.post("/extract-nid", response_model=NIDOcrExtractionResponse)
async def extract_nid_information(
    nid_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract OCR data from the front side of a Bangladesh NID using Gemini.
    """
    try:
        if not nid_image.content_type or nid_image.content_type.lower() not in ALLOWED_NID_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only JPEG, PNG, and WebP images are allowed for NID OCR",
            )

        nid_image_data = await nid_image.read()
        if not nid_image_data:
            raise HTTPException(status_code=400, detail="NID image file cannot be empty")

        if len(nid_image_data) > MAX_NID_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="NID image file size exceeds 5MB limit")

        try:
            extraction = ocr_service.extract(
                image_data=nid_image_data,
                content_type=nid_image.content_type,
            )
        except NIDOcrExtractionError as exc:
            logger.warning("NID OCR extraction failed: %s", exc)
            return _build_ocr_response(
                success=False,
                message=str(exc) or "We could not extract NID information at this time. Please try again.",
            )

        if not extraction.document_detected:
            return _build_ocr_response(
                success=False,
                message="No front side of a Bangladesh NID was detected in the uploaded image.",
                extraction=extraction,
            )

        parsed_date_of_birth = _parse_ocr_date(extraction.date_of_birth)
        warnings = list(extraction.warnings)
        if extraction.date_of_birth and not parsed_date_of_birth:
            warnings.append("Date of birth could not be parsed")

        current_user.update_ocr_extraction(
            ocr_name=extraction.name,
            ocr_father_name=extraction.father_name,
            ocr_mother_name=extraction.mother_name,
            ocr_date_of_birth=parsed_date_of_birth,
            ocr_nid_number=extraction.nid_number,
            ocr_image_quality=extraction.image_quality,
            ocr_warnings=warnings,
            processed_at=datetime.now(timezone.utc),
        )

        comparison_payload = _build_comparison_payload(current_user)
        current_user.ocr_name_match_score = comparison_payload["ocr_name_match_score"]
        current_user.ocr_name_match_status = comparison_payload["ocr_name_match_status"]
        current_user.ocr_nid_match = comparison_payload["ocr_nid_match"]
        current_user.ocr_dob_match = comparison_payload["ocr_dob_match"]
        current_user.ocr_review_status = comparison_payload["ocr_review_status"]
        current_user.admin_review_notes = comparison_payload["admin_review_notes"]

        try:
            db.commit()
        except Exception:
            db.rollback()
            return _build_ocr_response(
                success=False,
                message="We could not save the extracted NID information. Please try again.",
                extraction=extraction,
            )

        return _build_ocr_response(
            success=True,
            message="NID information extracted successfully",
            extraction=NIDOcrExtractionResult(
                document_detected=True,
                name=current_user.ocr_name,
                father_name=current_user.ocr_father_name,
                mother_name=current_user.ocr_mother_name,
                date_of_birth=current_user.ocr_date_of_birth.isoformat() if current_user.ocr_date_of_birth else None,
                nid_number=current_user.ocr_nid_number,
                image_quality=current_user.ocr_image_quality,
                warnings=current_user.ocr_warnings or [],
            ),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during NID OCR extraction")
        db.rollback()
        return _build_ocr_response(
            success=False,
            message="We could not extract NID information at this time. Please try again.",
        )

@router.post("/submit", response_model=VerificationResponse)
async def submit_verification(
    verification_notes: Optional[str] = Form(None),
    nid_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit NID verification information including NID image and optional notes
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
        
        # Update user verification info with binary data
        current_user.update_verification_info(
            nid_image_data=nid_image_data,
            nid_image_filename=nid_image.filename,
            nid_image_content_type=nid_image.content_type,
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
    return _build_status_response(current_user, rejection.notes if rejection else None)


@router.put("/ocr-confirmation", response_model=OcrConfirmationUpdateResponse)
async def update_ocr_confirmation(
    request: OcrConfirmationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        current_user.ocr_confirmed = request.ocr_confirmed
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update OCR confirmation")

    return OcrConfirmationUpdateResponse(
        success=True,
        message="OCR confirmation updated successfully",
        ocr_confirmed=current_user.ocr_confirmed,
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

@router.post("/approve/{user_id}", response_model=SimpleVerificationActionResponse)
async def approve_verification(
    user_id: str,
    admin_review_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to approve user verification
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        _update_verified_identity_from_ocr(user)
        user.ocr_confirmed = True
        profile = ProfileRepository.get_by_user_id(db, user_id)
        if profile:
            profile.identity_verified = True
            profile.date_of_birth = user.date_of_birth
            profile.father_name = user.father_name
            profile.mother_name = user.mother_name
        if admin_review_notes is not None:
            user.admin_review_notes = admin_review_notes.strip() or None

        db.query(VerificationRejection).filter(
            VerificationRejection.user_id == user_id
        ).delete()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve verification: {str(exc)}") from exc

    return SimpleVerificationActionResponse(
        success=True,
        message="User verification approved",
        verification_status=user.verification_status,
    )

@router.post("/reject/{user_id}", response_model=SimpleVerificationActionResponse)
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

    try:
        user.reject_verification(rejection_notes)
        user.ocr_review_status = "rejected"
        user.admin_review_notes = rejection_notes
        existing_rejection = db.query(VerificationRejection).filter(
            VerificationRejection.user_id == user_id
        ).first()
        if existing_rejection:
            existing_rejection.notes = rejection_notes
        else:
            db.add(VerificationRejection(user_id=user_id, notes=rejection_notes))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reject verification: {str(exc)}") from exc

    return SimpleVerificationActionResponse(
        success=True,
        message="User verification rejected",
        verification_status=user.verification_status,
    )

@router.post("/request-correction/{user_id}", response_model=SimpleVerificationActionResponse)
async def request_verification_correction(
    user_id: str,
    request: AdminVerificationCorrectionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin endpoint to request correction of submitted identity information.
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.verification_status = "correction_required"
        user.identity_verified = False
        user.verified_at = None
        user.ocr_confirmed = False
        user.admin_review_notes = request.reason.strip()
        user.ocr_review_status = "correction_required"
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to request correction: {str(exc)}") from exc

    return SimpleVerificationActionResponse(
        success=True,
        message="Verification correction requested",
        verification_status=user.verification_status,
    )

@router.post("/correct-submitted-info", response_model=SimpleVerificationActionResponse)
async def correct_submitted_info(
    request: CorrectSubmittedIdentityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allow a user to correct submitted identity data before resubmission.
    """
    if current_user.verification_status == "verified":
        raise HTTPException(status_code=400, detail="Verified identity data cannot be corrected")

    if current_user.verification_status not in {"correction_required", "resubmission_required", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Identity corrections are only allowed after a correction or rejection request",
        )

    normalized_name = request.name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Name is required")

    normalized_nid = _normalize_nid_value(request.nid)
    if not normalized_nid:
        raise HTTPException(status_code=400, detail="NID is required")
    if not _is_valid_nid(normalized_nid):
        raise HTTPException(status_code=400, detail="NID must contain 10, 13, or 17 digits")

    parsed_date_of_birth = _parse_user_date_of_birth(request.date_of_birth)
    if parsed_date_of_birth is not None:
        corrected_age = _calculate_age_from_date_of_birth(parsed_date_of_birth)
    else:
        if request.age is None:
            raise HTTPException(
                status_code=400,
                detail="Age is required when date_of_birth is not provided",
            )
        if request.age < 0:
            raise HTTPException(status_code=400, detail="Age must be a valid number")
        corrected_age = request.age

    try:
        current_user.set_official_identity(
            name=normalized_name,
            nid=normalized_nid,
            date_of_birth=parsed_date_of_birth,
            age=corrected_age,
        )
        current_user.ocr_confirmed = False
        current_user.verification_status = "not_submitted"
        current_user.verified_at = None
        _clear_comparison_fields(current_user)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update submitted information: {str(exc)}") from exc

    return SimpleVerificationActionResponse(
        success=True,
        message="Submitted identity information updated successfully",
        verification_status=current_user.verification_status,
    )

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

@router.get("/pending", response_model=PendingVerificationsResponse)
async def get_pending_verifications(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to get all pending verifications
    """
    pending_users = db.query(User).filter(
        User.verification_status.in_(["pending", "in_progress", "correction_required"]),
        User.is_deleted == False
    ).all()
    
    return PendingVerificationsResponse(
        pending_verifications=[_build_pending_user_response(user) for user in pending_users]
    )
