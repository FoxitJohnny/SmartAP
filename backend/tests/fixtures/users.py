"""
User Test Fixtures

Provides sample user data, authentication helpers, and JWT token generation.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib
import base64
import json


# Default test password (used across all test users)
TEST_PASSWORD = "TestPassword123!"
TEST_PASSWORD_HASH = hashlib.sha256(TEST_PASSWORD.encode()).hexdigest()


# Sample users for various test scenarios
SAMPLE_USERS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "id": 1,
        "email": "user@smartap.test",
        "name": "Test User",
        "role": "user",
        "is_active": True,
        "department": "Finance",
        "approval_limit": 10000.00,
        "created_at": datetime(2025, 1, 1),
    },
    "admin": {
        "id": 2,
        "email": "admin@smartap.test",
        "name": "Admin User",
        "role": "admin",
        "is_active": True,
        "department": "IT",
        "approval_limit": float("inf"),
        "created_at": datetime(2024, 6, 1),
    },
    "reviewer": {
        "id": 3,
        "email": "reviewer@smartap.test",
        "name": "Reviewer User",
        "role": "reviewer",
        "is_active": True,
        "department": "Accounting",
        "approval_limit": 50000.00,
        "created_at": datetime(2025, 3, 1),
    },
    "approver": {
        "id": 4,
        "email": "approver@smartap.test",
        "name": "Approver User",
        "role": "approver",
        "is_active": True,
        "department": "Management",
        "approval_limit": 100000.00,
        "created_at": datetime(2024, 12, 1),
    },
    "readonly": {
        "id": 5,
        "email": "readonly@smartap.test",
        "name": "Read Only User",
        "role": "readonly",
        "is_active": True,
        "department": "Audit",
        "approval_limit": 0.0,
        "created_at": datetime(2025, 6, 1),
    },
    "inactive": {
        "id": 6,
        "email": "inactive@smartap.test",
        "name": "Inactive User",
        "role": "user",
        "is_active": False,
        "department": "Former Employee",
        "approval_limit": 0.0,
        "created_at": datetime(2024, 1, 1),
        "deactivated_at": datetime(2025, 9, 1),
    },
    "new_user": {
        "id": 7,
        "email": "newuser@smartap.test",
        "name": "New User",
        "role": "user",
        "is_active": True,
        "department": "Finance",
        "approval_limit": 1000.00,  # Limited until training complete
        "created_at": datetime.now() - timedelta(days=7),
    },
}


def create_test_user(
    scenario: str = "standard",
    **overrides,
) -> Dict[str, Any]:
    """
    Create a test user from a scenario.
    
    Args:
        scenario: Name of the scenario from SAMPLE_USERS
        **overrides: Fields to override from the scenario
    
    Returns:
        User data dictionary
    """
    if scenario not in SAMPLE_USERS:
        raise ValueError(f"Unknown scenario: {scenario}. Available: {list(SAMPLE_USERS.keys())}")
    
    user_data = {**SAMPLE_USERS[scenario], **overrides}
    user_data["password_hash"] = TEST_PASSWORD_HASH
    
    return user_data


def create_admin_user(**overrides) -> Dict[str, Any]:
    """Create an admin user for testing."""
    return create_test_user("admin", **overrides)


def create_reviewer_user(**overrides) -> Dict[str, Any]:
    """Create a reviewer user for testing."""
    return create_test_user("reviewer", **overrides)


def create_approver_user(**overrides) -> Dict[str, Any]:
    """Create an approver user for testing."""
    return create_test_user("approver", **overrides)


def create_custom_user(
    email: str,
    name: str = "Custom User",
    role: str = "user",
    **kwargs,
) -> Dict[str, Any]:
    """
    Create a custom test user.
    
    Args:
        email: User email
        name: User name
        role: User role
        **kwargs: Additional user attributes
    
    Returns:
        User data dictionary
    """
    return {
        "id": hash(email) % 10000,
        "email": email,
        "name": name,
        "role": role,
        "is_active": True,
        "password_hash": TEST_PASSWORD_HASH,
        "created_at": datetime.now(),
        **kwargs,
    }


def create_jwt_token(
    user_id: int,
    email: str,
    role: str = "user",
    expires_delta: timedelta = timedelta(hours=24),
    secret_key: str = "test-secret-key",
) -> str:
    """
    Create a mock JWT token for testing.
    
    Note: This is for testing only. In production, use proper JWT libraries.
    
    Args:
        user_id: User ID to encode
        email: User email
        role: User role
        expires_delta: Token expiration time
        secret_key: Secret key for signing
    
    Returns:
        JWT token string
    """
    # Create header
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    
    # Create payload
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    
    # Encode (simplified - not cryptographically secure)
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    # Create signature (simplified)
    message = f"{header_b64}.{payload_b64}"
    signature = hashlib.sha256(f"{message}{secret_key}".encode()).hexdigest()[:43]
    
    return f"{header_b64}.{payload_b64}.{signature}"


def create_auth_headers(
    user: Optional[Dict[str, Any]] = None,
    scenario: str = "standard",
    token_type: str = "Bearer",
) -> Dict[str, str]:
    """
    Create authorization headers for API testing.
    
    Args:
        user: User data dictionary (created from scenario if not provided)
        scenario: User scenario to use if user not provided
        token_type: Token type (Bearer, Basic, etc.)
    
    Returns:
        Dictionary with Authorization header
    """
    if user is None:
        user = create_test_user(scenario)
    
    token = create_jwt_token(
        user_id=user["id"],
        email=user["email"],
        role=user.get("role", "user"),
    )
    
    return {
        "Authorization": f"{token_type} {token}",
    }


def create_admin_headers() -> Dict[str, str]:
    """Create auth headers for admin user."""
    return create_auth_headers(scenario="admin")


def create_reviewer_headers() -> Dict[str, str]:
    """Create auth headers for reviewer user."""
    return create_auth_headers(scenario="reviewer")


def create_approver_headers() -> Dict[str, str]:
    """Create auth headers for approver user."""
    return create_auth_headers(scenario="approver")


def create_expired_headers() -> Dict[str, str]:
    """Create expired auth headers for testing token expiration."""
    user = create_test_user("standard")
    token = create_jwt_token(
        user_id=user["id"],
        email=user["email"],
        expires_delta=timedelta(hours=-1),  # Already expired
    )
    return {"Authorization": f"Bearer {token}"}


def create_invalid_headers() -> Dict[str, str]:
    """Create invalid auth headers for testing authentication failures."""
    return {"Authorization": "Bearer invalid.token.here"}


# Registration/login payloads
def get_registration_payload(
    email: str = "newuser@smartap.test",
    password: str = TEST_PASSWORD,
    name: str = "New Test User",
) -> Dict[str, str]:
    """Get a user registration payload for testing."""
    return {
        "email": email,
        "password": password,
        "name": name,
    }


def get_login_payload(
    email: str = "user@smartap.test",
    password: str = TEST_PASSWORD,
) -> Dict[str, str]:
    """Get a login payload for testing."""
    return {
        "email": email,
        "password": password,
    }


# User permission scenarios
USER_PERMISSIONS = {
    "user": {
        "can_view_invoices": True,
        "can_upload_invoices": True,
        "can_approve_invoices": False,
        "can_manage_users": False,
        "can_view_reports": False,
        "can_configure_system": False,
    },
    "reviewer": {
        "can_view_invoices": True,
        "can_upload_invoices": True,
        "can_approve_invoices": False,
        "can_manage_users": False,
        "can_view_reports": True,
        "can_configure_system": False,
    },
    "approver": {
        "can_view_invoices": True,
        "can_upload_invoices": True,
        "can_approve_invoices": True,
        "can_manage_users": False,
        "can_view_reports": True,
        "can_configure_system": False,
    },
    "admin": {
        "can_view_invoices": True,
        "can_upload_invoices": True,
        "can_approve_invoices": True,
        "can_manage_users": True,
        "can_view_reports": True,
        "can_configure_system": True,
    },
    "readonly": {
        "can_view_invoices": True,
        "can_upload_invoices": False,
        "can_approve_invoices": False,
        "can_manage_users": False,
        "can_view_reports": True,
        "can_configure_system": False,
    },
}


def get_user_permissions(role: str) -> Dict[str, bool]:
    """Get permissions for a user role."""
    return USER_PERMISSIONS.get(role, USER_PERMISSIONS["user"])
