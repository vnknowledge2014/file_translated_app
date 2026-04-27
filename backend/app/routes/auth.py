from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.database import db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str

@router.post("/register", response_model=UserResponse)
async def register_user(user_in: UserCreate) -> Any:
    # Check if user exists
    result = await db.query(
        "SELECT * FROM user WHERE username = $username LIMIT 1",
        {"username": user_in.username}
    )
    records = result[0].get("result", [])
    if records:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create new user
    user_obj = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        role="user"
    )
    
    created = await db.create("user", user_obj.model_dump(exclude={"id"}, mode="json"))
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create user")
        
    user = created[0] if isinstance(created, list) else created
    return UserResponse(
        id=user.get("id"),
        username=user.get("username"),
        role=user.get("role")
    )

@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # Authenticate user
    result = await db.query(
        "SELECT * FROM user WHERE username = $username LIMIT 1",
        {"username": form_data.username}
    )
    records = result[0].get("result", [])
    if not records:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    user = records[0]
    if not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user.get("id"),
        username=current_user.get("username"),
        role=current_user.get("role")
    )
