"""
SmartAP Authentication Module

JWT-based authentication with user registration, login, and token management.
Users are persisted to the PostgreSQL database.
"""

import os
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db.database import get_session
from .db.models import UserDB, RefreshTokenDB

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# JWT Settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Router
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ============================================================================
# Models
# ============================================================================

class UserRole(str):
    """User roles for RBAC."""
    ADMIN = "admin"
    FINANCE_MANAGER = "finance_manager"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=100)
    department: Optional[str] = None
    role: str = Field(default="viewer", description="User role")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class User(BaseModel):
    """User model."""
    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class UserResponse(BaseModel):
    """User response (without sensitive data)."""
    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_active: bool


# ============================================================================
# Database Helper Functions
# ============================================================================

async def get_user_by_email(session: AsyncSession, email: str) -> Optional[UserDB]:
    """Get a user by email from the database."""
    result = await session.execute(
        select(UserDB).where(UserDB.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[UserDB]:
    """Get a user by user_id from the database."""
    result = await session.execute(
        select(UserDB).where(UserDB.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user_in_db(session: AsyncSession, user_data: dict) -> UserDB:
    """Create a new user in the database."""
    user = UserDB(
        user_id=user_data["user_id"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        hashed_password=user_data["hashed_password"],
        role=user_data.get("role", "viewer"),
        department=user_data.get("department"),
        is_active=True,
        is_verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def store_refresh_token(session: AsyncSession, token: str, user_id: str, expires_at: datetime) -> RefreshTokenDB:
    """Store a refresh token in the database."""
    refresh_token = RefreshTokenDB(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    await session.commit()
    return refresh_token


async def get_refresh_token(session: AsyncSession, token: str) -> Optional[RefreshTokenDB]:
    """Get a refresh token from the database."""
    result = await session.execute(
        select(RefreshTokenDB).where(
            RefreshTokenDB.token == token,
            RefreshTokenDB.revoked == False,
            RefreshTokenDB.expires_at > datetime.now(timezone.utc)
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(session: AsyncSession, token: str) -> None:
    """Revoke a refresh token."""
    result = await session.execute(
        select(RefreshTokenDB).where(RefreshTokenDB.token == token)
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        db_token.revoked_at = datetime.now(timezone.utc)
        await session.commit()


async def ensure_demo_user(session: AsyncSession) -> None:
    """Ensure demo user exists in database."""
    existing = await get_user_by_email(session, "demo@smartap.com")
    if not existing:
        await create_user_in_db(session, {
            "user_id": "user_demo_001",
            "email": "demo@smartap.com",
            "full_name": "Demo User",
            "hashed_password": pwd_context.hash("Demo1234!"),
            "role": "finance_manager",
            "department": "Finance",
        })
        logger.info("Demo user created in database")


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token_jwt(user_id: str) -> tuple[str, datetime]:
    """Create a JWT refresh token. Returns (token, expires_at) with naive datetime for DB."""
    # Use timezone-aware for JWT exp claim
    expires_at_utc = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    # Use naive datetime for database storage
    expires_at_naive = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "exp": expires_at_utc,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_at_naive


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_email = payload.get("sub")
    if user_email is None:
        raise credentials_exception
    
    user_db = await get_user_by_email(session, user_email)
    if user_db is None:
        raise credentials_exception
    
    if not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return User(
        id=user_db.user_id,
        email=user_db.email,
        full_name=user_db.full_name,
        role=user_db.role,
        department=user_db.department,
        is_active=user_db.is_active,
        created_at=user_db.created_at
    )


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    if not token:
        return None
    try:
        return await get_current_user(token, session)
    except HTTPException:
        return None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password."
)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """Register a new user."""
    # Check if user already exists
    existing = await get_user_by_email(session, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_id = f"user_{secrets.token_hex(8)}"
    user_db = await create_user_in_db(session, {
        "user_id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hash_password(user_data.password),
        "role": user_data.role,
        "department": user_data.department,
    })
    
    return UserResponse(
        id=user_db.user_id,
        email=user_db.email,
        full_name=user_db.full_name,
        role=user_db.role,
        department=user_db.department,
        is_active=user_db.is_active
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token",
    description="Authenticate with email and password to receive JWT tokens."
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session)
) -> Token:
    """Authenticate user and return JWT tokens."""
    # Ensure demo user exists
    await ensure_demo_user(session)
    
    user_db = await get_user_by_email(session, form_data.username)  # OAuth2 uses 'username' field
    
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login (use naive datetime for PostgreSQL compatibility)
    user_db.last_login = datetime.utcnow()
    await session.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user_db.email,
            "role": user_db.role,
            "user_id": user_db.user_id
        }
    )
    refresh_token, expires_at = create_refresh_token_jwt(user_db.user_id)
    
    # Store refresh token in database
    await store_refresh_token(session, refresh_token, user_db.user_id, expires_at)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/login/json",
    response_model=Token,
    summary="Login with JSON body",
    description="Authenticate with JSON payload instead of form data."
)
async def login_json(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session)
) -> Token:
    """Authenticate user with JSON body and return JWT tokens."""
    # Ensure demo user exists
    await ensure_demo_user(session)
    
    user_db = await get_user_by_email(session, credentials.email)
    
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not verify_password(credentials.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login (use naive datetime for PostgreSQL compatibility)
    user_db.last_login = datetime.utcnow()
    await session.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user_db.email,
            "role": user_db.role,
            "user_id": user_db.user_id
        }
    )
    refresh_token, expires_at = create_refresh_token_jwt(user_db.user_id)
    
    # Store refresh token in database
    await store_refresh_token(session, refresh_token, user_db.user_id, expires_at)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token."
)
async def refresh_token_endpoint(
    token_data: TokenRefresh,
    session: AsyncSession = Depends(get_session)
) -> Token:
    """Refresh the access token using a refresh token."""
    payload = decode_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify token is in database and not revoked
    stored_token = await get_refresh_token(session, token_data.refresh_token)
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )
    
    user_id = payload.get("sub")
    
    # Find user by ID
    user_db = await get_user_by_id(session, user_id)
    
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Revoke old refresh token
    await revoke_refresh_token(session, token_data.refresh_token)
    
    # Create new tokens
    access_token = create_access_token(
        data={
            "sub": user_db.email,
            "role": user_db.role,
            "user_id": user_db.user_id
        }
    )
    new_refresh_token, expires_at = create_refresh_token_jwt(user_db.user_id)
    
    # Store new refresh token
    await store_refresh_token(session, new_refresh_token, user_db.user_id, expires_at)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and revoke tokens",
    description="Revoke the current refresh token."
)
async def logout(
    token_data: TokenRefresh,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Logout and revoke refresh token."""
    await revoke_refresh_token(session, token_data.refresh_token)
    
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the profile of the currently authenticated user."
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
) -> UserResponse:
    """Get the current user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active
    )


@router.get(
    "/verify",
    summary="Verify token",
    description="Verify if the current access token is valid."
)
async def verify_token(
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """Verify the current token is valid."""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
