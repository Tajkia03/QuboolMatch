import base64
from typing import Dict, List
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from models.message.message import Message
from repositories.block_repository import BlockRepository
from repositories.profile_repository.profile_repository import ProfileRepository
from repositories.user_repository.user_repository import UserRepository


class MessageRepository:
    @staticmethod
    def create(db: Session, from_user_id: str, to_user_id: str, content: str) -> Message:
        message = Message(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            content=content.strip(),
            is_read=False,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_thread(db: Session, user_id: str, other_user_id: str, limit: int = 100) -> List[Message]:
        return (
            db.query(Message)
            .filter(
                or_(
                    and_(Message.from_user_id == user_id, Message.to_user_id == other_user_id),
                    and_(Message.from_user_id == other_user_id, Message.to_user_id == user_id),
                )
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_thread_as_read(db: Session, user_id: str, other_user_id: str) -> int:
        updated = (
            db.query(Message)
            .filter(
                Message.from_user_id == other_user_id,
                Message.to_user_id == user_id,
                Message.is_read == False,
            )
            .update({"is_read": True}, synchronize_session=False)
        )
        db.commit()
        return updated

    @staticmethod
    def count_unread(db: Session, user_id: str) -> int:
        return (
            db.query(Message)
            .filter(Message.to_user_id == user_id, Message.is_read == False)
            .count()
        )

    @staticmethod
    def get_conversations(db: Session, user_id: str) -> List[Dict]:
        all_messages = (
            db.query(Message)
            .filter(or_(Message.from_user_id == user_id, Message.to_user_id == user_id))
            .order_by(Message.created_at.desc())
            .all()
        )

        seen_other_users = set()
        conversations: List[Dict] = []

        for msg in all_messages:
            other_user_id = msg.to_user_id if msg.from_user_id == user_id else msg.from_user_id
            if other_user_id in seen_other_users:
                continue
            seen_other_users.add(other_user_id)

            other_user = UserRepository.get_by_id(db, other_user_id)
            if not other_user:
                continue

            other_profile = ProfileRepository.get_by_user_id(db, other_user_id)
            profile_picture_base64 = None
            if other_profile and other_profile.profile_picture_data:
                try:
                    encoded = base64.b64encode(other_profile.profile_picture_data).decode("utf-8")
                    content_type = other_profile.profile_picture_content_type or "image/jpeg"
                    profile_picture_base64 = f"data:{content_type};base64,{encoded}"
                except Exception as e:
                    print(f"Error encoding profile picture: {e}")

            unread_count = (
                db.query(Message)
                .filter(
                    Message.from_user_id == other_user_id,
                    Message.to_user_id == user_id,
                    Message.is_read == False,
                )
                .count()
            )

            block_status = BlockRepository.get_status(db, user_id, other_user_id)

            conversations.append(
                {
                    "user": {
                        "id": other_user.id,
                        "name": other_user.name,
                        "age": other_user.age,
                        "religion": other_user.religion,
                        "profile_picture": profile_picture_base64,
                        "verification_status": other_user.verification_status,
                        "matching_percentage": other_user.matching_percentage,
                        "nid_verified": other_user.verification_status == "verified",
                        "photo_verified": other_user.matching_percentage is not None and other_user.matching_percentage >= 70,
                    },
                    "last_message": msg.to_dict(),
                    "unread_count": unread_count,
                    "block_status": block_status,
                }
            )

        return conversations
