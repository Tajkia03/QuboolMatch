from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.block import Block


class BlockRepository:
    @staticmethod
    def create(db: Session, blocker_id: str, blocked_id: str) -> Block:
        block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
        db.add(block)
        db.commit()
        db.refresh(block)
        return block

    @staticmethod
    def get(db: Session, blocker_id: str, blocked_id: str) -> Optional[Block]:
        return db.query(Block).filter(
            Block.blocker_id == blocker_id,
            Block.blocked_id == blocked_id
        ).first()

    @staticmethod
    def has_blocked(db: Session, blocker_id: str, blocked_id: str) -> bool:
        return BlockRepository.get(db, blocker_id, blocked_id) is not None

    @staticmethod
    def get_status(db: Session, user_id: str, other_user_id: str) -> Dict[str, bool]:
        blocked_by_me = BlockRepository.has_blocked(db, user_id, other_user_id)
        blocked_me = BlockRepository.has_blocked(db, other_user_id, user_id)
        return {
            "blocked_by_me": blocked_by_me,
            "blocked_me": blocked_me,
            "blocked": blocked_by_me or blocked_me,
        }

    @staticmethod
    def delete(db: Session, block: Block) -> None:
        db.delete(block)
        db.commit()

    @staticmethod
    def is_blocked_between(db: Session, user_id: str, other_user_id: str) -> bool:
        return db.query(Block).filter(
            or_(
                and_(Block.blocker_id == user_id, Block.blocked_id == other_user_id),
                and_(Block.blocker_id == other_user_id, Block.blocked_id == user_id)
            )
        ).first() is not None

    @staticmethod
    def get_blocked_user_ids(db: Session, user_id: str) -> Set[str]:
        blocked = db.query(Block).filter(Block.blocker_id == user_id).all()
        blocked_by = db.query(Block).filter(Block.blocked_id == user_id).all()

        blocked_ids = {b.blocked_id for b in blocked}
        blocked_by_ids = {b.blocker_id for b in blocked_by}
        return blocked_ids.union(blocked_by_ids)