from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Response, HTTPException, Form
from pydantic import BaseModel, EmailStr, Field
from database import get_db
from repositories.user_repository.user_repository import UserRepository
from facade import register_user
from shared.token import Token
from typing import Optional

router = APIRouter()


class UserSignUp(BaseModel):
    name: str
    email: EmailStr
    password: str
    gender: str
    nid: str
    age: int
    religion: Optional[str] = None
    preferred_age_from: Optional[int] = None
    preferred_age_to: Optional[int] = None


@router.post("/sign_up")
async def sign_up(params: UserSignUp, db: Session = Depends(get_db)):
    try:
        new_user = register_user(params, db)
        # Generate access token for the new user
        token = Token.generate_and_sign(user_id=str(new_user.id))
        return JSONResponse(
            content={"access_token": token, "token_type": "bearer"}, 
            status_code=201
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e)) from e


class UserSignIn(BaseModel):
    # Login identifiers may include reserved development domains such as
    # ``quboolmatch.test``. Signup remains strictly validated with EmailStr.
    email: str = Field(min_length=3, max_length=320)
    password: str


@router.post("/sign_in")
async def sign_in(params: UserSignIn, db: Session = Depends(get_db)):
    user = UserRepository.get_by_email(db, params.email.strip().lower())

    if user and user.check_password(params.password):
        token = Token.generate_and_sign(user_id=str(user.id))
        return JSONResponse(content={"access_token": token}, status_code=200)

    raise HTTPException(status_code=401, detail="Incorrect email or password")


@router.post("/admin-login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Admin-specific login endpoint that only allows admin users
    """
    user = UserRepository.get_by_email(db, username)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.check_password(password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    token = Token.generate_and_sign(user_id=str(user.id))
    return JSONResponse(content={"access_token": token, "token_type": "bearer"}, status_code=200)
