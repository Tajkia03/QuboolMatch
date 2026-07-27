from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Optional

from sqlalchemy.orm import Session

from config import get_settings
from models.email_verification_code import EmailVerificationCode
from models.user.user import User


class EmailVerificationError(ValueError):
    def __init__(self, message: str, status_code: int = 400, retry_after_seconds: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _code_hash(code: str) -> str:
    key = get_settings().SECRET_KEY.encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), sha256).hexdigest()


def _generate_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _active_code_query(db: Session, user_id: str, email: str):
    return (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.email == _normalize_email(email),
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )


def _invalidate_active_codes(db: Session, user_id: str, email: str) -> None:
    timestamp = _now()
    for code in _active_code_query(db, user_id, email).all():
        code.consumed_at = timestamp


def _format_from_address() -> str:
    settings = get_settings()
    sender = settings.RESEND_FROM_EMAIL
    name = settings.RESEND_FROM_NAME
    if "<" in sender and ">" in sender:
        return sender
    return f"{name} <{sender}>"


def send_verification_email(email: str, pin: str) -> None:
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        print(f"[EMAIL VERIFICATION] Resend is not configured. PIN for {email}: {pin}")
        return

    import resend

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": _format_from_address(),
        "to": [_normalize_email(email)],
        "subject": "Verify your Qubool Match email",
        "html": (
            "<div style='font-family:Arial,sans-serif;line-height:1.6;color:#2f2430'>"
            "<h2>Your Qubool Match verification PIN</h2>"
            "<p>Use this 6-digit PIN to verify your email address:</p>"
            f"<p style='font-size:30px;font-weight:800;letter-spacing:8px'>{pin}</p>"
            f"<p>This PIN expires in {settings.EMAIL_VERIFICATION_PIN_TTL_MINUTES} minutes.</p>"
            "</div>"
        ),
        "text": f"Your Qubool Match verification PIN is {pin}. It expires in {settings.EMAIL_VERIFICATION_PIN_TTL_MINUTES} minutes.",
    })


def create_and_send_code(db: Session, user: User, email: str, *, enforce_cooldown: bool = False) -> dict:
    settings = get_settings()
    normalized_email = _normalize_email(email)
    timestamp = _now()
    latest_code = _active_code_query(db, user.id, normalized_email).first()

    if enforce_cooldown and latest_code:
        elapsed = (timestamp - _as_aware(latest_code.last_sent_at)).total_seconds()
        cooldown = settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
        if elapsed < cooldown:
            retry_after = max(1, int(cooldown - elapsed))
            raise EmailVerificationError(
                "Please wait before requesting another verification PIN.",
                status_code=429,
                retry_after_seconds=retry_after,
            )

    _invalidate_active_codes(db, user.id, normalized_email)
    pin = _generate_pin()
    expires_at = timestamp + timedelta(minutes=settings.EMAIL_VERIFICATION_PIN_TTL_MINUTES)
    code = EmailVerificationCode(
        user_id=user.id,
        email=normalized_email,
        code_hash=_code_hash(pin),
        expires_at=expires_at,
        attempt_count=0,
        max_attempts=settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
        last_sent_at=timestamp,
        created_at=timestamp,
    )
    db.add(code)
    db.commit()
    send_verification_email(normalized_email, pin)
    return {
        "expires_in_seconds": settings.EMAIL_VERIFICATION_PIN_TTL_MINUTES * 60,
        "resend_cooldown_seconds": settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    }


def ensure_code_for_login(db: Session, user: User) -> dict:
    active_code = _active_code_query(db, user.id, user.email).first()
    if active_code and _as_aware(active_code.expires_at) > _now():
        return {
            "expires_in_seconds": max(1, int((_as_aware(active_code.expires_at) - _now()).total_seconds())),
            "resend_cooldown_seconds": get_settings().EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
        }
    return create_and_send_code(db, user, user.email)


def verify_code(db: Session, user_id: str, email: str, pin: str) -> User:
    if not pin.isdigit() or len(pin) != 6:
        raise EmailVerificationError("Enter a valid 6-digit verification PIN.")

    normalized_email = _normalize_email(email)
    user = db.query(User).filter(User.id == user_id, User.email == normalized_email).first()
    if not user:
        raise EmailVerificationError("Verification request not found.", status_code=404)
    if user.email_verified:
        return user

    code = _active_code_query(db, user_id, normalized_email).first()
    if not code:
        raise EmailVerificationError("Verification PIN not found. Please request a new PIN.")

    timestamp = _now()
    if _as_aware(code.expires_at) <= timestamp:
        code.consumed_at = timestamp
        db.commit()
        raise EmailVerificationError("Verification PIN expired. Please request a new PIN.")
    if code.attempt_count >= code.max_attempts:
        code.consumed_at = timestamp
        db.commit()
        raise EmailVerificationError("Too many invalid attempts. Please request a new PIN.", status_code=429)

    if not hmac.compare_digest(code.code_hash, _code_hash(pin)):
        code.attempt_count += 1
        if code.attempt_count >= code.max_attempts:
            code.consumed_at = timestamp
            db.commit()
            raise EmailVerificationError("Too many invalid attempts. Please request a new PIN.", status_code=429)
        db.commit()
        raise EmailVerificationError("Invalid verification PIN.")

    code.consumed_at = timestamp
    user.email_verified = True
    user.email_verified_at = timestamp
    db.commit()
    db.refresh(user)
    return user
