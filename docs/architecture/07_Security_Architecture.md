# SmartAP Security Architecture

**Section 7 of Architecture Documentation**

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication](#authentication)
3. [Authorization (RBAC)](#authorization-rbac)
4. [Data Protection](#data-protection)
5. [Network Security](#network-security)
6. [Secrets Management](#secrets-management)
7. [Compliance & Auditing](#compliance--auditing)
8. [Security Best Practices](#security-best-practices)

---

## Security Overview

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Security Layers Architecture                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  Layer 1: Network Security                                                   │
    │  ┌─────────────────────────────────────────────────────────────────────┐    │
    │  │  ● TLS 1.3 encryption for all traffic                               │    │
    │  │  ● WAF (Web Application Firewall)                                   │    │
    │  │  ● DDoS protection                                                  │    │
    │  │  ● IP whitelisting for admin access                                 │    │
    │  └─────────────────────────────────────────────────────────────────────┘    │
    │  ┌─────────────────────────────────────────────────────────────────────┐    │
    │  │  Layer 2: API Gateway Security                                      │    │
    │  │  ┌─────────────────────────────────────────────────────────────┐    │    │
    │  │  │  ● Rate limiting                                            │    │    │
    │  │  │  ● Request validation                                       │    │    │
    │  │  │  ● CORS policy enforcement                                  │    │    │
    │  │  │  ● API key validation                                       │    │    │
    │  │  └─────────────────────────────────────────────────────────────┘    │    │
    │  │  ┌─────────────────────────────────────────────────────────────┐    │    │
    │  │  │  Layer 3: Application Security                              │    │    │
    │  │  │  ┌─────────────────────────────────────────────────────┐    │    │    │
    │  │  │  │  ● JWT authentication                               │    │    │    │
    │  │  │  │  ● RBAC authorization                               │    │    │    │
    │  │  │  │  ● Input sanitization                               │    │    │    │
    │  │  │  │  ● XSS/CSRF protection                              │    │    │    │
    │  │  │  │  ● SQL injection prevention                         │    │    │    │
    │  │  │  └─────────────────────────────────────────────────────┘    │    │    │
    │  │  │  ┌─────────────────────────────────────────────────────┐    │    │    │
    │  │  │  │  Layer 4: Data Security                             │    │    │    │
    │  │  │  │  ┌─────────────────────────────────────────────┐    │    │    │    │
    │  │  │  │  │  ● Encryption at rest (AES-256)             │    │    │    │    │
    │  │  │  │  │  ● Encryption in transit (TLS 1.3)          │    │    │    │    │
    │  │  │  │  │  ● Key rotation                             │    │    │    │    │
    │  │  │  │  │  ● Data masking for sensitive fields        │    │    │    │    │
    │  │  │  │  └─────────────────────────────────────────────┘    │    │    │    │
    │  │  │  └─────────────────────────────────────────────────────┘    │    │    │
    │  │  └─────────────────────────────────────────────────────────────┘    │    │
    │  └─────────────────────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────────────────────┘
```

### Security Principles

| Principle | Implementation |
|-----------|----------------|
| **Least Privilege** | Users get minimum permissions needed |
| **Defense in Depth** | Multiple security layers |
| **Secure by Default** | Security features enabled by default |
| **Zero Trust** | Verify every request, trust nothing |
| **Fail Securely** | Errors don't expose sensitive data |

---

## Authentication

### JWT Token Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    JWT Authentication Flow                          │
└─────────────────────────────────────────────────────────────────────┘

   User            Frontend          Backend          Redis
    │                 │                 │               │
    │  Login          │                 │               │
    │ ───────────────►│                 │               │
    │                 │ POST /auth/login│               │
    │                 │ ───────────────►│               │
    │                 │                 │  Verify       │
    │                 │                 │  credentials  │
    │                 │                 │               │
    │                 │                 │  Generate     │
    │                 │                 │  JWT pair     │
    │                 │                 │               │
    │                 │                 │  Store refresh│
    │                 │                 │ ─────────────►│
    │                 │  {access_token, │               │
    │                 │   refresh_token}│               │
    │                 │ ◄───────────────│               │
    │  Store tokens   │                 │               │
    │ ◄───────────────│                 │               │
```

### Token Configuration

```python
# src/core/config.py
class SecuritySettings(BaseSettings):
    # JWT Settings
    JWT_SECRET_KEY: str  # From environment
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Settings
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Session Settings
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 60
```

### Token Structure

```python
# Access Token Payload
{
    "sub": "user_123",          # User ID
    "email": "user@example.com",
    "role": "finance_manager",
    "permissions": ["invoices:read", "invoices:write", "approvals:approve"],
    "department_id": 456,
    "iat": 1704729600,          # Issued at
    "exp": 1704731400,          # Expiration (30 min)
    "jti": "tok_abc123xyz"      # Unique token ID
}

# Refresh Token Payload
{
    "sub": "user_123",
    "type": "refresh",
    "iat": 1704729600,
    "exp": 1705334400,          # 7 days
    "jti": "ref_xyz789abc"
}
```

### Password Security

```python
# src/core/security.py
from passlib.context import CryptContext
import secrets

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(length)

def validate_password_strength(password: str) -> list[str]:
    """Validate password meets security requirements."""
    errors = []
    
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain special character")
    
    return errors
```

### Multi-Factor Authentication (MFA)

```python
# src/core/mfa.py
import pyotp
import qrcode
from io import BytesIO

class MFAService:
    def generate_totp_secret(self) -> str:
        """Generate TOTP secret for user."""
        return pyotp.random_base32()
    
    def get_totp_uri(self, email: str, secret: str) -> str:
        """Get TOTP URI for QR code."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name="SmartAP"
        )
    
    def generate_qr_code(self, uri: str) -> bytes:
        """Generate QR code image."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
```

---

## Authorization (RBAC)

### Permission Matrix

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              Permission Matrix                                        │
├───────────────────┬────────┬─────────────────┬──────────┬──────────┬─────────┬───────┤
│ Resource          │ admin  │ finance_manager │ ap_clerk │ approver │ auditor │viewer │
├───────────────────┼────────┼─────────────────┼──────────┼──────────┼─────────┼───────┤
│ invoices:create   │   ✓    │        ✓        │    ✓     │          │         │       │
│ invoices:read     │   ✓    │        ✓        │    ✓     │    ✓     │    ✓    │   ✓   │
│ invoices:update   │   ✓    │        ✓        │    ✓     │          │         │       │
│ invoices:delete   │   ✓    │        ✓        │          │          │         │       │
│ invoices:approve  │   ✓    │        ✓        │          │    ✓     │         │       │
├───────────────────┼────────┼─────────────────┼──────────┼──────────┼─────────┼───────┤
│ vendors:create    │   ✓    │        ✓        │          │          │         │       │
│ vendors:read      │   ✓    │        ✓        │    ✓     │    ✓     │    ✓    │   ✓   │
│ vendors:update    │   ✓    │        ✓        │          │          │         │       │
│ vendors:approve   │   ✓    │        ✓        │          │          │         │       │
├───────────────────┼────────┼─────────────────┼──────────┼──────────┼─────────┼───────┤
│ users:manage      │   ✓    │                 │          │          │         │       │
│ settings:manage   │   ✓    │                 │          │          │         │       │
│ audit:read        │   ✓    │        ✓        │          │          │    ✓    │       │
│ reports:view      │   ✓    │        ✓        │    ✓     │    ✓     │    ✓    │       │
│ reports:export    │   ✓    │        ✓        │          │          │    ✓    │       │
└───────────────────┴────────┴─────────────────┴──────────┴──────────┴─────────┴───────┘
```

### Permission Enforcement

```python
# src/core/auth.py
from functools import wraps
from fastapi import HTTPException, status

def require_permissions(permissions: list[str]):
    """Decorator to require specific permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            user_permissions = set(current_user.role.permissions)
            required = set(permissions)
            
            if not required.issubset(user_permissions):
                missing = required - user_permissions
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {', '.join(missing)}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/invoices/{id}")
@require_permissions(["invoices:delete"])
async def delete_invoice(id: int, current_user: User = Depends(get_current_user)):
    ...
```

### Row-Level Security

```python
# src/services/invoice_service.py
class InvoiceService:
    def get_invoices_for_user(self, user: User, filters: dict) -> list[Invoice]:
        """Get invoices based on user's access level."""
        query = self.db.query(Invoice)
        
        # Admins and auditors see all
        if user.role.name in ["admin", "auditor"]:
            pass
        
        # Finance managers see their department
        elif user.role.name == "finance_manager":
            query = query.join(User).filter(
                User.department_id == user.department_id
            )
        
        # Approvers see assigned invoices
        elif user.role.name == "approver":
            query = query.join(Approval).filter(
                Approval.approver_id == user.id
            )
        
        # Others see only their own invoices
        else:
            query = query.filter(Invoice.created_by == user.id)
        
        return query.filter_by(**filters).all()
```

---

## Data Protection

### Encryption Configuration

```python
# src/core/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class EncryptionService:
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance from master key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"smartap_salt",  # In production, use unique salt
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self._fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self._fernet.decrypt(encrypted_data.encode()).decode()

# Sensitive field encryption
class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted strings."""
    impl = String
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return encryption_service.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return encryption_service.decrypt(value)
        return value
```

### Data Classification

| Classification | Examples | Protection |
|----------------|----------|------------|
| **Public** | Company name, invoice status | Standard access control |
| **Internal** | Invoice amounts, vendor list | Role-based access |
| **Confidential** | Bank account numbers, tax IDs | Encrypted, audit logged |
| **Restricted** | Passwords, API keys, MFA secrets | Encrypted, never logged |

### Data Masking

```python
# src/core/masking.py
def mask_bank_account(account: str) -> str:
    """Mask bank account number."""
    if len(account) < 4:
        return "****"
    return "*" * (len(account) - 4) + account[-4:]

def mask_tax_id(tax_id: str) -> str:
    """Mask tax ID (e.g., EIN, SSN)."""
    if len(tax_id) < 4:
        return "***-**-****"
    return "***-**-" + tax_id[-4:]

def mask_email(email: str) -> str:
    """Mask email address."""
    local, domain = email.split("@")
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"

# Response serializer with masking
class VendorResponse(BaseModel):
    id: int
    name: str
    bank_account: str
    tax_id: str
    
    @validator("bank_account", pre=True)
    def mask_account(cls, v):
        return mask_bank_account(v) if v else None
    
    @validator("tax_id", pre=True)
    def mask_tax(cls, v):
        return mask_tax_id(v) if v else None
```

---

## Network Security

### TLS Configuration

```yaml
# nginx/ssl.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# HSTS
add_header Strict-Transport-Security "max-age=63072000" always;

# Certificate
ssl_certificate /etc/nginx/certs/smartap.crt;
ssl_certificate_key /etc/nginx/certs/smartap.key;
ssl_trusted_certificate /etc/nginx/certs/chain.pem;
```

### CORS Policy

```python
# src/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.smartap.io",
        "https://staging.smartap.io",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    max_age=3600,
)
```

### Security Headers

```python
# src/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.smartap.io;"
        )
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        
        return response
```

---

## Secrets Management

### Environment Variables

```bash
# .env.example (NEVER commit actual .env)
# Database
DATABASE_URL=postgresql://user:pass@localhost/smartap

# JWT
JWT_SECRET_KEY=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256

# Encryption
MASTER_ENCRYPTION_KEY=your-master-encryption-key

# External Services
FOXIT_API_KEY=your-foxit-api-key
OPENAI_API_KEY=your-openai-api-key
STRIPE_SECRET_KEY=your-stripe-secret-key

# Email
SMTP_PASSWORD=your-smtp-password

# Cloud Storage
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

### Azure Key Vault Integration

```python
# src/core/secrets.py
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class SecretManager:
    def __init__(self, vault_url: str):
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)
        self._cache = {}
    
    def get_secret(self, name: str) -> str:
        """Get secret from Key Vault with caching."""
        if name not in self._cache:
            secret = self.client.get_secret(name)
            self._cache[name] = secret.value
        return self._cache[name]
    
    def rotate_secret(self, name: str, new_value: str) -> None:
        """Rotate a secret value."""
        self.client.set_secret(name, new_value)
        self._cache.pop(name, None)  # Clear cache

# Usage
secret_manager = SecretManager("https://smartap-vault.vault.azure.net/")
db_password = secret_manager.get_secret("database-password")
```

### Kubernetes Secrets

```yaml
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: smartap-secrets
  namespace: smartap
type: Opaque
data:
  # Base64 encoded values
  database-url: cG9zdGdyZXNxbDovL3VzZXI6cGFzc0Bsb2NhbGhvc3Qvc21hcnRhcA==
  jwt-secret-key: eW91ci0yNTYtYml0LXNlY3JldC1rZXktaGVyZQ==
---
# Use in deployment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: smartap-api
          envFrom:
            - secretRef:
                name: smartap-secrets
```

---

## Compliance & Auditing

### Audit Log Implementation

```python
# src/services/audit_service.py
from datetime import datetime
import json

class AuditService:
    def __init__(self, db: Session):
        self.db = db
    
    async def log_action(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: int,
        old_values: dict = None,
        new_values: dict = None,
        request: Request = None
    ):
        """Create audit log entry."""
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            created_at=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        await self.db.commit()
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: int
    ) -> list[AuditLog]:
        """Get full audit history for an entity."""
        return await self.db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(AuditLog.created_at.desc()).all()
```

### Compliance Controls

| Framework | Requirement | Implementation |
|-----------|-------------|----------------|
| **SOC 2** | Access Control | RBAC, MFA, session management |
| **SOC 2** | Audit Logging | Comprehensive audit trail |
| **SOC 2** | Encryption | AES-256 at rest, TLS 1.3 in transit |
| **GDPR** | Data Minimization | Collect only necessary data |
| **GDPR** | Right to Access | Data export API |
| **GDPR** | Right to Erasure | Data deletion workflow |
| **PCI DSS** | Cardholder Data | No card data storage |
| **HIPAA** | PHI Protection | Encryption, access controls |

### Data Retention

```python
# src/services/retention_service.py
class DataRetentionService:
    RETENTION_PERIODS = {
        "invoices": 365 * 7,      # 7 years
        "audit_logs": 365 * 7,    # 7 years
        "notifications": 90,       # 90 days
        "sessions": 30,            # 30 days
        "temp_files": 7,           # 7 days
    }
    
    async def cleanup_expired_data(self):
        """Remove data past retention period."""
        for entity_type, days in self.RETENTION_PERIODS.items():
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            if entity_type == "invoices":
                # Archive instead of delete
                await self._archive_old_invoices(cutoff_date)
            elif entity_type == "sessions":
                await self._delete_old_sessions(cutoff_date)
```

---

## Security Best Practices

### Input Validation

```python
# src/schemas/invoice.py
from pydantic import BaseModel, validator, constr
import re

class InvoiceCreate(BaseModel):
    invoice_number: constr(min_length=1, max_length=100)
    vendor_id: int
    total: float
    notes: Optional[constr(max_length=2000)] = None
    
    @validator("invoice_number")
    def validate_invoice_number(cls, v):
        """Validate invoice number format."""
        if not re.match(r"^[A-Za-z0-9\-_]+$", v):
            raise ValueError("Invoice number contains invalid characters")
        return v.upper()
    
    @validator("total")
    def validate_total(cls, v):
        """Validate total amount."""
        if v <= 0:
            raise ValueError("Total must be positive")
        if v > 999999999.99:
            raise ValueError("Total exceeds maximum allowed")
        return round(v, 2)
    
    @validator("notes")
    def sanitize_notes(cls, v):
        """Sanitize notes to prevent XSS."""
        if v:
            # Remove potential HTML/script tags
            v = re.sub(r"<[^>]*>", "", v)
        return v
```

### SQL Injection Prevention

```python
# Always use parameterized queries
# ❌ Bad - SQL injection vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✓ Good - Parameterized query
query = select(User).where(User.email == email)

# ✓ Good - With SQLAlchemy ORM
user = db.query(User).filter(User.email == email).first()

# ✓ Good - Raw SQL with parameters
result = db.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)
```

### Security Checklist

```markdown
## Pre-Deployment Security Checklist

### Authentication & Authorization
- [ ] JWT tokens configured with secure secret
- [ ] Password policy enforced (12+ chars, complexity)
- [ ] MFA available and encouraged
- [ ] Session timeouts configured
- [ ] Account lockout after failed attempts

### Data Protection
- [ ] All sensitive data encrypted at rest
- [ ] TLS 1.3 for all connections
- [ ] Secrets stored in vault (not in code)
- [ ] Database credentials rotated regularly

### Application Security
- [ ] Input validation on all endpoints
- [ ] CORS policy configured
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] File upload validation

### Infrastructure
- [ ] WAF configured
- [ ] DDoS protection enabled
- [ ] Network segmentation in place
- [ ] Firewall rules reviewed
- [ ] SSH key access only (no passwords)

### Monitoring & Response
- [ ] Audit logging enabled
- [ ] Security alerts configured
- [ ] Incident response plan documented
- [ ] Backup and recovery tested
```

---

## Related Documentation

- **[Section 6: API Overview](./06_API_Overview.md)** - API authentication details
- **[Section 8: Scalability & Performance](./08_Scalability.md)** - Security at scale
- **[Deployment Guide](../Deployment_Guide.md)** - Secure deployment practices
- **[API Reference](../API_Reference.md)** - Auth endpoint documentation

---

*Continue to [Section 8: Scalability & Performance](./08_Scalability.md)*
