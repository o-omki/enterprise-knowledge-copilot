import datetime
import os

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from apps.api.app.schemas import Token, UserLogin, UserRegister, UserResponse
from packages.shared.database import async_session_maker
from packages.shared.orm_models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if SECRET_KEY is None:
    raise ValueError("[ENCRYPTION ERROR] - JWT_SECRET_KEY is not set.")

ALGORITHM = os.getenv("JWT_ALGORITHM")

if ALGORITHM is None:
    raise ValueError("[ENCRYPTION ERROR] - JWT_ALGORITHM is not set.")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister):
    async with async_session_maker() as db:
        query = select(User).where(User.email == user.email)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user.password)
        new_user = User(email=user.email, password_hash=hashed_password)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return UserResponse(id=new_user.id, email=new_user.email)


@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    async with async_session_maker() as db:
        query = select(User).where(User.email == user.email)
        result = await db.execute(query)
        db_user = result.scalar_one_or_none()

        if not db_user or not verify_password(user.password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(data={"sub": db_user.id})
        return Token(access_token=access_token)
