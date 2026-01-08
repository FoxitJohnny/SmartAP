"""
SmartAP Authentication Module

JWT-based authentication with user registration, login, and token management.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt

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
# In-memory user store (replace with database in production)
# ============================================================================

# Simple in-memory store for development
_users_db: dict[str, dict] = {}
_refresh_tokens: dict[str, str] = {}  # token -> user_id


def _init_demo_user():
    """Initialize a demo user for testing."""
    if "demo@smartap.com" not in _users_db:
        user_id = "user_demo_001"
        _users_db["demo@smartap.com"] = {
            "id": user_id,
            "email": "demo@smartap.com",
            "full_name": "Demo User",
            "hashed_password": pwd_context.hash("Demo1234!"),
            "role": "finance_manager",
            "department": "Finance",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

# Initialize demo user
_init_demo_user()


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


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    _refresh_tokens[token] = user_id
    return token


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(token: Annotated[Optional[str], Depends(oauth2_scheme)]) -> User:
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
    
    user_data = _users_db.get(user_email)
    if user_data is None:
        raise credentials_exception
    
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return User(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        role=user_data["role"],
        department=user_data.get("department"),
        is_active=user_data["is_active"],
        created_at=datetime.fromisoformat(user_data["created_at"])
    )


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    if not token:
        return None
    try:
        return await get_current_user(token)
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
async def register(user_data: UserCreate) -> UserResponse:
    """Register a new user."""
    # Check if user already exists
    if user_data.email in _users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_id = f"user_{secrets.token_hex(8)}"
    user = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hash_password(user_data.password),
        "role": user_data.role,
        "department": user_data.department,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    _users_db[user_data.email] = user
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        is_active=user["is_active"]
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token",
    description="Authenticate with email and password to receive JWT tokens."
)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Authenticate user and return JWT tokens."""
    user_data = _users_db.get(form_data.username)  # OAuth2 uses 'username' field
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user_data["email"],
            "role": user_data["role"],
            "user_id": user_data["id"]
        }
    )
    refresh_token = create_refresh_token(user_data["id"])
    
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
async def login_json(credentials: UserLogin) -> Token:
    """Authenticate user with JSON body and return JWT tokens."""
    user_data = _users_db.get(credentials.email)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not verify_password(credentials.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user_data["email"],
            "role": user_data["role"],
            "user_id": user_data["id"]
        }
    )
    refresh_token = create_refresh_token(user_data["id"])
    
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
async def refresh_token(token_data: TokenRefresh) -> Token:
    """Refresh the access token using a refresh token."""
    payload = decode_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify token is in our store
    if token_data.refresh_token not in _refresh_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )
    
    user_id = payload.get("sub")
    
    # Find user by ID
    user_data = None
    for email, data in _users_db.items():
        if data["id"] == user_id:
            user_data = data
            break
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Revoke old refresh token
    del _refresh_tokens[token_data.refresh_token]
    
    # Create new tokens
    access_token = create_access_token(
        data={
            "sub": user_data["email"],
            "role": user_data["role"],
            "user_id": user_data["id"]
        }
    )
    new_refresh_token = create_refresh_token(user_data["id"])
    
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
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """Logout and revoke refresh token."""
    if token_data.refresh_token in _refresh_tokens:
        del _refresh_tokens[token_data.refresh_token]
    
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
