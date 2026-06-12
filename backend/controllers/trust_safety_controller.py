from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models.user.user import User
from repositories.user_repository.user_repository import UserRepository
from repositories.block_repository import BlockRepository
from repositories.report_repository import ReportRepository
from shared.token import get_current_user

router = APIRouter()


class ReportUserRequest(BaseModel):
    reported_user_id: str
    reason: str
    details: Optional[str] = None
    context: Optional[str] = None


class BlockUserRequest(BaseModel):
    blocked_user_id: str


@router.post("/reports")
async def report_user(
    params: ReportUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id == params.reported_user_id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")

    reported_user = UserRepository.get_by_id(db, params.reported_user_id)
    if not reported_user:
        raise HTTPException(status_code=404, detail="User not found")

    report = ReportRepository.create(
        db,
        reporter_id=current_user.id,
        reported_id=params.reported_user_id,
        reason=params.reason,
        details=params.details,
        context=params.context,
    )

    return JSONResponse(
        content={"message": "Report submitted", "report": report.to_dict()},
        status_code=201,
    )


@router.post("/blocks")
async def block_user(
    params: BlockUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id == params.blocked_user_id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")

    blocked_user = UserRepository.get_by_id(db, params.blocked_user_id)
    if not blocked_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = BlockRepository.get(db, current_user.id, params.blocked_user_id)
    if existing:
        return JSONResponse(content={"message": "User already blocked"}, status_code=200)

    BlockRepository.create(db, current_user.id, params.blocked_user_id)
    return JSONResponse(content={"message": "User blocked"}, status_code=201)


@router.delete("/blocks/{blocked_user_id}")
async def unblock_user(
    blocked_user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    block = BlockRepository.get(db, current_user.id, blocked_user_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    BlockRepository.delete(db, block)
    return JSONResponse(content={"message": "User unblocked"}, status_code=200)