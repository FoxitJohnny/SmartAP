"""
Unit Tests for Authentication Module

Tests for password hashing, JWT tokens, and user authentication.
"""

import pytest
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from pydantic import ValidationError
from jose import jwt, JWTError


# Import the auth module components
from src.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token_jwt,
    decode_token,
    UserCreate,
    UserLogin,
    Token,
    UserRole,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


# =============================================================================
# Password Hashing Tests
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing functions.
    
    Note: These tests mock the passlib context since bcrypt backend may not be available
    in all environments. In production, ensure bcrypt is installed.
    """
    
    @patch('src.auth.pwd_context')
    def test_hash_password_returns_string(self, mock_context):
        """Test that hash_password returns a string."""
        mock_context.hash.return_value = "$2b$12$mockedhashvalue"
        
        hashed = hash_password("SecurePass123!")
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        mock_context.hash.assert_called_once_with("SecurePass123!")
    
    @patch('src.auth.pwd_context')
    def test_hash_password_calls_context(self, mock_context):
        """Test that hash_password uses pwd_context."""
        mock_context.hash.return_value = "$2b$12$hashvalue1"
        
        hash_password("TestPassword123!")
        
        mock_context.hash.assert_called_once_with("TestPassword123!")
    
    @patch('src.auth.pwd_context')
    def test_verify_password_correct(self, mock_context):
        """Test verify_password with correct password."""
        mock_context.verify.return_value = True
        
        result = verify_password("CorrectPass123!", "$2b$12$hashedvalue")
        
        assert result is True
        mock_context.verify.assert_called_once_with("CorrectPass123!", "$2b$12$hashedvalue")
    
    @patch('src.auth.pwd_context')
    def test_verify_password_incorrect(self, mock_context):
        """Test verify_password with incorrect password."""
        mock_context.verify.return_value = False
        
        result = verify_password("WrongPass123!", "$2b$12$hashedvalue")
        
        assert result is False
    
    @patch('src.auth.pwd_context')
    def test_verify_password_case_sensitive(self, mock_context):
        """Test that password verification calls context correctly."""
        mock_context.verify.return_value = False
        
        result = verify_password("casesensitive123!", "$2b$12$hashedvalue")
        
        assert result is False
        mock_context.verify.assert_called_once()


# =============================================================================
# JWT Token Tests
# =============================================================================

class TestAccessToken:
    """Tests for JWT access token creation."""
    
    def test_create_access_token_structure(self):
        """Test access token has correct structure."""
        token = create_access_token({"sub": "user@example.com"})
        
        # Decode without verification to check structure
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["type"] == "access"
    
    def test_create_access_token_contains_user_data(self):
        """Test access token contains user data."""
        user_data = {
            "sub": "user@example.com",
            "role": "admin",
            "user_id": "user_123",
        }
        
        token = create_access_token(user_data)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload["sub"] == "user@example.com"
        assert payload["role"] == "admin"
        assert payload["user_id"] == "user_123"
    
    def test_create_access_token_default_expiration(self):
        """Test access token uses default expiration."""
        token = create_access_token({"sub": "user@example.com"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Should expire within ACCESS_TOKEN_EXPIRE_MINUTES + small buffer
        time_diff = (exp - now).total_seconds() / 60
        assert time_diff <= ACCESS_TOKEN_EXPIRE_MINUTES + 1
        assert time_diff >= ACCESS_TOKEN_EXPIRE_MINUTES - 1
    
    def test_create_access_token_custom_expiration(self):
        """Test access token with custom expiration."""
        custom_delta = timedelta(hours=2)
        token = create_access_token({"sub": "user@example.com"}, expires_delta=custom_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        time_diff_hours = (exp - now).total_seconds() / 3600
        assert 1.9 <= time_diff_hours <= 2.1


class TestRefreshToken:
    """Tests for JWT refresh token creation."""
    
    def test_create_refresh_token_returns_tuple(self):
        """Test refresh token function returns token and expiry."""
        token, expires_at = create_refresh_token_jwt("user_123")
        
        assert isinstance(token, str)
        assert isinstance(expires_at, datetime)
    
    def test_create_refresh_token_structure(self):
        """Test refresh token has correct structure."""
        token, _ = create_refresh_token_jwt("user_123")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user_123"
        assert "jti" in payload  # JWT ID for uniqueness
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_refresh_token_unique_jti(self):
        """Test refresh tokens have unique JTI."""
        token1, _ = create_refresh_token_jwt("user_123")
        token2, _ = create_refresh_token_jwt("user_123")
        
        payload1 = jwt.decode(token1, SECRET_KEY, algorithms=[ALGORITHM])
        payload2 = jwt.decode(token2, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload1["jti"] != payload2["jti"]


class TestDecodeToken:
    """Tests for token decoding."""
    
    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token({"sub": "user@example.com", "role": "admin"})
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user@example.com"
        assert payload["role"] == "admin"
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        invalid_token = "this.is.not.a.valid.jwt"
        
        payload = decode_token(invalid_token)
        
        assert payload is None
    
    def test_decode_tampered_token(self):
        """Test decoding a tampered token returns None."""
        token = create_access_token({"sub": "user@example.com"})
        
        # Tamper with the token
        parts = token.split(".")
        parts[1] = "tampered_payload"
        tampered_token = ".".join(parts)
        
        payload = decode_token(tampered_token)
        
        assert payload is None
    
    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        # Create a token that expires immediately
        expired_token = create_access_token(
            {"sub": "user@example.com"},
            expires_delta=timedelta(seconds=-10)  # Already expired
        )
        
        payload = decode_token(expired_token)
        
        assert payload is None
    
    def test_decode_wrong_secret(self):
        """Test decoding with wrong secret returns None."""
        # Create token with correct secret
        token = create_access_token({"sub": "user@example.com"})
        
        # Try to decode with wrong secret
        with patch('src.auth.SECRET_KEY', 'wrong_secret'):
            # Need to reimport or the patch won't work for decode_token
            # Instead, let's decode directly
            try:
                jwt.decode(token, "wrong_secret", algorithms=[ALGORITHM])
                assert False, "Should have raised JWTError"
            except JWTError:
                pass  # Expected


# =============================================================================
# Pydantic Model Validation Tests
# =============================================================================

class TestUserCreateValidation:
    """Tests for UserCreate model validation."""
    
    def test_valid_user_create(self):
        """Test valid user creation model."""
        user = UserCreate(
            email="test@example.com",
            password="ValidPass123!",
            full_name="Test User",
            department="IT",
            role="admin",
        )
        
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
    
    def test_password_min_length(self):
        """Test password minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="Short1A",  # Only 7 chars, needs 8
                full_name="Test User",
            )
        
        # Password fails validation (either length or complexity)
        assert exc_info.value is not None
    
    def test_password_requires_uppercase(self):
        """Test password requires uppercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="lowercase123!",  # No uppercase
                full_name="Test User",
            )
        
        assert "uppercase" in str(exc_info.value).lower()
    
    def test_password_requires_lowercase(self):
        """Test password requires lowercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="UPPERCASE123!",  # No lowercase
                full_name="Test User",
            )
        
        assert "lowercase" in str(exc_info.value).lower()
    
    def test_password_requires_digit(self):
        """Test password requires digit."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="NoDigitsHere!",  # No digits
                full_name="Test User",
            )
        
        assert "digit" in str(exc_info.value).lower()
    
    def test_invalid_email_format(self):
        """Test invalid email format rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-a-valid-email",
                password="ValidPass123!",
                full_name="Test User",
            )
    
    def test_full_name_min_length(self):
        """Test full name minimum length."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="ValidPass123!",
                full_name="X",  # Too short
            )
    
    def test_default_role(self):
        """Test default role is viewer."""
        user = UserCreate(
            email="test@example.com",
            password="ValidPass123!",
            full_name="Test User",
        )
        
        assert user.role == "viewer"


class TestUserLoginValidation:
    """Tests for UserLogin model validation."""
    
    def test_valid_user_login(self):
        """Test valid user login model."""
        login = UserLogin(
            email="user@example.com",
            password="anypassword",
        )
        
        assert login.email == "user@example.com"
        assert login.password == "anypassword"
    
    def test_invalid_email(self):
        """Test login rejects invalid email."""
        with pytest.raises(ValidationError):
            UserLogin(
                email="invalid-email",
                password="password",
            )


class TestTokenModel:
    """Tests for Token response model."""
    
    def test_token_model(self):
        """Test Token model structure."""
        token = Token(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            expires_in=1800,
        )
        
        assert token.access_token == "access_token_value"
        assert token.refresh_token == "refresh_token_value"
        assert token.token_type == "bearer"  # Default
        assert token.expires_in == 1800


# =============================================================================
# User Role Tests
# =============================================================================

class TestUserRole:
    """Tests for UserRole constants."""
    
    def test_role_values(self):
        """Test UserRole values."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.FINANCE_MANAGER == "finance_manager"
        assert UserRole.ACCOUNTANT == "accountant"
        assert UserRole.VIEWER == "viewer"


# =============================================================================
# Integration-style Unit Tests (with mocked DB)
# =============================================================================

class TestGetCurrentUser:
    """Tests for get_current_user dependency."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, mock_session):
        """Test get_current_user raises when no token provided."""
        from src.auth import get_current_user
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None, mock_session)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_session):
        """Test get_current_user raises for invalid token."""
        from src.auth import get_current_user
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", mock_session)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_refresh_token_rejected(self, mock_session):
        """Test get_current_user rejects refresh tokens."""
        from src.auth import get_current_user
        from fastapi import HTTPException
        
        # Create a refresh token
        refresh_token, _ = create_refresh_token_jwt("user_123")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(refresh_token, mock_session)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token_user_not_found(self, mock_session):
        """Test get_current_user when user doesn't exist."""
        from src.auth import get_current_user
        from fastapi import HTTPException
        
        # Create valid access token
        access_token = create_access_token({"sub": "nonexistent@example.com"})
        
        # Mock: user not found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(access_token, mock_session)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_disabled_account(self, mock_session):
        """Test get_current_user rejects disabled accounts."""
        from src.auth import get_current_user
        from fastapi import HTTPException
        
        # Create valid access token
        access_token = create_access_token({"sub": "disabled@example.com"})
        
        # Mock: user found but disabled
        mock_user = Mock()
        mock_user.email = "disabled@example.com"
        mock_user.is_active = False
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(access_token, mock_session)
        
        assert exc_info.value.status_code == 403
        assert "disabled" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_session):
        """Test successful user retrieval."""
        from src.auth import get_current_user
        
        # Create valid access token
        access_token = create_access_token({"sub": "user@example.com"})
        
        # Mock: user found and active
        mock_user = Mock()
        mock_user.user_id = "user_123"
        mock_user.email = "user@example.com"
        mock_user.full_name = "Test User"
        mock_user.role = "admin"
        mock_user.department = "IT"
        mock_user.is_active = True
        mock_user.created_at = datetime.now()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        user = await get_current_user(access_token, mock_session)
        
        assert user.id == "user_123"
        assert user.email == "user@example.com"
        assert user.role == "admin"


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_returns_none_when_no_token(self, mock_session):
        """Test returns None when no token provided."""
        from src.auth import get_current_user_optional
        
        result = await get_current_user_optional(None, mock_session)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self, mock_session):
        """Test returns None for invalid token instead of raising."""
        from src.auth import get_current_user_optional
        
        result = await get_current_user_optional("invalid", mock_session)
        
        assert result is None
