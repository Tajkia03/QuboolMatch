from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Response, HTTPException, Form
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from database import get_db
from repositories.user_repository.user_repository import UserRepository
from facade import register_user
from shared.token import Token
from services.email_verification_service import (
    EmailVerificationError,
    create_and_send_code,
    ensure_code_for_login,
    verify_code,
)
from typing import Optional

router = APIRouter()

PASSWORD_REQUIREMENTS = (
    "Password must be 7-128 characters and include uppercase, lowercase, "
    "number, and special character."
)
MIN_NID_LENGTH = 8


class UserSignUp(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=7, max_length=128)
    gender: str = Field(min_length=1)
    nid: str = Field(min_length=MIN_NID_LENGTH)
    age: int = Field(ge=18, le=99)
    religion: Optional[str] = None
    preferred_age_from: int = Field(ge=18, le=99)
    preferred_age_to: int = Field(ge=18, le=99)

    @field_validator("name", "gender")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("This field is required.")
        return trimmed

    @field_validator("nid")
    @classmethod
    def validate_nid(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("This field is required.")
        if len(trimmed) < MIN_NID_LENGTH:
            raise ValueError(f"NID number must be at least {MIN_NID_LENGTH} characters.")
        return trimmed

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        has_upper = any(char.isupper() for char in password)
        has_lower = any(char.islower() for char in password)
        has_digit = any(char.isdigit() for char in password)
        has_special = any(not char.isalnum() for char in password)

        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError(PASSWORD_REQUIREMENTS)

        return password

    @model_validator(mode="after")
    def validate_preferred_age_range(self):
        if self.preferred_age_from > self.preferred_age_to:
            raise ValueError("Preferred age range 'From' must be less than or equal to 'To'.")
        return self


@router.post("/sign_up")
async def sign_up(params: UserSignUp, db: Session = Depends(get_db)):
    try:
        new_user = register_user(params, db)
        verification_meta = create_and_send_code(db, new_user, new_user.email)
        return JSONResponse(
            content={
                "user_id": str(new_user.id),
                "email": new_user.email,
                "email_verification_required": True,
                **verification_meta,
            },
            status_code=201
        )
    except EmailVerificationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e)) from e


class UserSignIn(BaseModel):
    # Login identifiers may include reserved development domains such as
    # ``quboolmatch.test``. Signup remains strictly validated with EmailStr.
    email: str = Field(min_length=3, max_length=320)
    password: str


class VerifyEmailRequest(BaseModel):
    user_id: str = Field(min_length=1)
    email: EmailStr
    pin: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ResendEmailVerificationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


@router.post("/sign_in")
async def sign_in(params: UserSignIn, db: Session = Depends(get_db)):
    user = UserRepository.get_by_email(db, params.email.strip().lower())

    if user and user.check_password(params.password):
        if not user.email_verified:
            verification_meta = ensure_code_for_login(db, user)
            return JSONResponse(
                content={
                    "email_verification_required": True,
                    "user_id": str(user.id),
                    "email": user.email,
                    **verification_meta,
                },
                status_code=403,
            )
        token = Token.generate_and_sign(user_id=str(user.id))
        return JSONResponse(content={"access_token": token}, status_code=200)

    raise HTTPException(status_code=401, detail="Incorrect email or password")


@router.post("/verify-email")
async def verify_email(params: VerifyEmailRequest, db: Session = Depends(get_db)):
    try:
        user = verify_code(db, params.user_id, str(params.email), params.pin)
        token = Token.generate_and_sign(user_id=str(user.id))
        return JSONResponse(
            content={"access_token": token, "token_type": "bearer"},
            status_code=200,
        )
    except EmailVerificationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e


@router.post("/resend-email-verification")
async def resend_email_verification(params: ResendEmailVerificationRequest, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, params.user_id)
    if not user or user.email != str(params.email):
        raise HTTPException(status_code=404, detail="Verification request not found.")
    if user.email_verified:
        return JSONResponse(content={"email_verified": True}, status_code=200)

    try:
        verification_meta = create_and_send_code(db, user, user.email, enforce_cooldown=True)
        return JSONResponse(
            content={
                "email_verification_required": True,
                "user_id": str(user.id),
                "email": user.email,
                **verification_meta,
            },
            status_code=200,
        )
    except EmailVerificationError as e:
        content = {"detail": str(e)}
        if e.retry_after_seconds is not None:
            content["retry_after_seconds"] = e.retry_after_seconds
        return JSONResponse(content=content, status_code=e.status_code)


@router.post("/admin-login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Admin-specific login endpoint that only allows admin users
    """
    user = UserRepository.get_by_email(db, username.strip().lower())

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.check_password(password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    token = Token.generate_and_sign(user_id=str(user.id))
    return JSONResponse(content={"access_token": token, "token_type": "bearer"}, status_code=200)
