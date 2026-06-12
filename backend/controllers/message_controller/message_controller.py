from collections import defaultdict
from typing import Dict, List
import json
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models.user.user import User
from repositories.interest_repository.interest_repository import InterestRepository
from repositories.message_repository.message_repository import MessageRepository
from repositories.notification_repository.notification_repository import NotificationRepository
from repositories.user_repository.user_repository import UserRepository
from repositories.block_repository import BlockRepository
from shared.token import Token, get_current_user
from google import genai
from google.genai import types
from config import get_settings

router = APIRouter()


class SendMessageRequest(BaseModel):
    to_user_id: str
    content: str


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections and websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, payload: dict):
        dead_connections: List[WebSocket] = []
        for connection in self.active_connections.get(user_id, []):
            try:
                await connection.send_json(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(user_id, dead)


manager = ConnectionManager()

logger = logging.getLogger(__name__)

BLOCKLIST = {
    "asshole",
    "bastard",
    "bitch",
    "bloody",
    "bullshit",
    "crap",
    "damn",
    "dick",
    "douche",
    "freak",
    "fuck",
    "idiot",
    "jerk",
    "loser",
    "moron",
    "piss",
    "prick",
    "scumbag",
    "shit",
    "slut",
    "stupid",
    "ugly",
}

BAD_PHRASES = {
    "send login details",
    "share your password",
    "give me your password",
    "send otp",
    "share otp",
    "send verification code",
    "share verification code",
    "send bank details",
    "share bank details",
    "send card details",
    "share card details",
}

RISKY_TERMS = {
    "kill",
    "murder",
    "hurt",
    "harm",
    "abusive",
    "attack",
    "assault",
    "blackmail",
    "extort",
    "scam",
    "fraud",
    "threaten",
    "threatening",
    "suicide",
    "threat",
    "rape",
    "abuse",
    "bomb",
}

RISKY_PHRASES = {
    "send me your address",
    "share your address",
    "send your location",
    "meet me alone",
    "come alone",
    "send nude",
    "send nudes",
    "send nude photos",
}

LEET_MAP = str.maketrans({
    "@": "a",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "0": "o",
    "$": "s",
})


def _normalize_for_filter(text: str) -> str:
    lowered = text.lower().translate(LEET_MAP)
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"(.)\1{2,}", r"\1\1", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _has_term(normalized: str, terms: set[str]) -> bool:
    tokens = set(normalized.split())
    return any(term in tokens for term in terms)


def _has_phrase(normalized: str, phrases: set[str]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _moderate_message(content: str) -> Dict[str, str | bool]:
    settings = get_settings()
    api_key = settings.GEMINI_MODERATION_API_KEY
    if not api_key:
        return {
            "allowed": False,
            "category": "other",
            "severity": "high",
            "reason": "Moderation API key is not configured",
        }

    prompt = (
        "You are a safety classifier for chat messages. "
        "Classify the message and respond ONLY with valid JSON. "
        "No markdown, no extra text.\n\n"
        "Return JSON with:\n"
        "- allowed: boolean\n"
        "- category: safe | harassment | hate | threat | sexual | spam | scam | profanity | other\n"
        "- severity: none | low | medium | high\n"
        "- reason: string\n\n"
        "Message:\n"
        f"{content}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        raw_text = (response.text or "").strip()
        data = json.loads(raw_text)
    except Exception as exc:
        return {
            "allowed": False,
            "category": "other",
            "severity": "high",
            "reason": f"Moderation failed: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "allowed": False,
            "category": "other",
            "severity": "high",
            "reason": "Moderation response was not an object",
        }

    allowed = data.get("allowed")
    category = data.get("category")
    severity = data.get("severity")
    reason = data.get("reason")

    if not isinstance(allowed, bool):
        return {
            "allowed": False,
            "category": "other",
            "severity": "high",
            "reason": "Moderation response missing allowed boolean",
        }

    if not isinstance(category, str) or not isinstance(severity, str) or not isinstance(reason, str):
        return {
            "allowed": False,
            "category": "other",
            "severity": "high",
            "reason": "Moderation response missing required fields",
        }

    return {
        "allowed": allowed,
        "category": category,
        "severity": severity,
        "reason": reason,
    }


def _validate_thread_allowed(db: Session, current_user_id: str, other_user_id: str):
    if current_user_id == other_user_id:
        raise HTTPException(status_code=400, detail="You cannot chat with yourself")

    other_user = UserRepository.get_by_id(db, other_user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not InterestRepository.check_accepted_interest_between(db, current_user_id, other_user_id):
        raise HTTPException(status_code=403, detail="Chat is allowed only after an accepted interest request")


def _validate_send_allowed(db: Session, current_user_id: str, other_user_id: str):
    _validate_thread_allowed(db, current_user_id, other_user_id)

    if BlockRepository.has_blocked(db, current_user_id, other_user_id):
        raise HTTPException(status_code=403, detail="Unblock this user before sending messages")

    if BlockRepository.has_blocked(db, other_user_id, current_user_id):
        raise HTTPException(status_code=403, detail="This user is not available anymore")


@router.post("/messages/send")
async def send_message(
    params: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = (params.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(content) > 1000:
        raise HTTPException(status_code=400, detail="Message is too long (max 1000 characters)")

    _validate_send_allowed(db, current_user.id, params.to_user_id)

    normalized = _normalize_for_filter(content)
    if _has_term(normalized, BLOCKLIST) or _has_phrase(normalized, BAD_PHRASES):
        preview = content[:120]
        logger.warning(
            "Blocked message due to local filter. from_user_id=%s to_user_id=%s preview=%s",
            current_user.id,
            params.to_user_id,
            preview,
        )
        raise HTTPException(
            status_code=400,
            detail="Your message could not be sent because it may violate our community guidelines.",
        )

    if _has_term(normalized, RISKY_TERMS) or _has_phrase(normalized, RISKY_PHRASES):
        moderation = _moderate_message(content)
        if not moderation.get("allowed", False):
            preview = content[:120]
            logger.warning(
                "Blocked message due to moderation. from_user_id=%s to_user_id=%s category=%s severity=%s reason=%s preview=%s",
                current_user.id,
                params.to_user_id,
                moderation.get("category"),
                moderation.get("severity"),
                moderation.get("reason"),
                preview,
            )
            raise HTTPException(
                status_code=400,
                detail="Your message could not be sent because it may violate our community guidelines.",
            )

    message = MessageRepository.create(
        db,
        from_user_id=current_user.id,
        to_user_id=params.to_user_id,
        content=content,
    )

    payload = {
        "type": "new_message",
        "message": message.to_dict(),
        "from_user": {
            "id": current_user.id,
            "name": current_user.name,
        },
    }

    await manager.send_to_user(params.to_user_id, payload)

    return JSONResponse(content={"message": message.to_dict()}, status_code=201)


@router.get("/messages/conversations")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversations = MessageRepository.get_conversations(db, current_user.id)
    return JSONResponse(
        content={
            "conversations": conversations,
            "total_unread": MessageRepository.count_unread(db, current_user.id),
        },
        status_code=200,
    )


@router.get("/messages/thread/{other_user_id}")
async def get_thread(
    other_user_id: str,
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_thread_allowed(db, current_user.id, other_user_id)

    messages = MessageRepository.get_thread(db, current_user.id, other_user_id, limit=limit)
    return JSONResponse(content={"messages": [m.to_dict() for m in messages]}, status_code=200)


@router.put("/messages/thread/{other_user_id}/read")
async def mark_thread_as_read(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_thread_allowed(db, current_user.id, other_user_id)

    updated_count = MessageRepository.mark_thread_as_read(db, current_user.id, other_user_id)
    return JSONResponse(content={"updated_count": updated_count}, status_code=200)


@router.get("/messages/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JSONResponse(
        content={"unread_count": MessageRepository.count_unread(db, current_user.id)},
        status_code=200,
    )


def _get_user_from_ws_token(token: str):
    payload = Token.verify_token(token)
    if not payload or not payload.get("user_id"):
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        return user
    finally:
        db.close()


@router.websocket("/ws/messages")
async def messages_websocket(websocket: WebSocket, token: str = Query(default="")):
    user = _get_user_from_ws_token(token)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, websocket)

    try:
        await manager.send_to_user(
            user.id,
            {
                "type": "presence",
                "message": "Connected to chat server",
                "user_id": user.id,
            },
        )
        while True:
            # Keep connection alive. Client can send ping payloads if desired.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception:
        manager.disconnect(user.id, websocket)
        await websocket.close()
