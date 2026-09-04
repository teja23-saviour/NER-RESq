from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = "USER"


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(
            (User.username == request.username) |
            (User.email == request.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"

    new_user = User(
        user_id=user_id,
        username=request.username,
        email=request.email,
        password_hash=pwd_context.hash(request.password),
        role=request.role.upper(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "message": "User registered successfully",
        "data": {
            "user_id": new_user.user_id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
        },
    }


@router.post("/login")
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )

    if not user or not pwd_context.verify(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token({
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
    })

    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "access_token": access_token,
            "token_type": "bearer",
        },
    }


@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.user_id == current_user.get("user_id"))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "success": True,
        "data": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    }
