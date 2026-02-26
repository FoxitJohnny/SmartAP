# Security Policy

## Supported Versions

SmartAP follows semantic versioning. Security updates are provided for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 3.x.x   | :white_check_mark: |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |
| < 1.0   | :x:                |

We recommend always running the latest stable version.

---

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** report security vulnerabilities through public GitHub issues.

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories** (Preferred)
   - Go to the [Security tab](../../security/advisories) of this repository
   - Click "Report a vulnerability"
   - Fill out the form with details

2. **Email**
   - Send details to: `security@smartap.example.com`
   - Use the PGP key below if you want to encrypt your report

### What to Include

Please include as much of the following information as possible:

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
- **Affected component** (e.g., `/api/v1/invoices`, authentication middleware)
- **Steps to reproduce** the vulnerability
- **Potential impact** (what an attacker could do)
- **Suggested fix** (if you have one)
- **Your environment** (OS, Python version, Docker version)

### What to Expect

| Timeframe | Action |
|-----------|--------|
| **24 hours** | Acknowledgment of your report |
| **72 hours** | Initial assessment and severity rating |
| **7 days** | Status update on fix progress |
| **30 days** | Target for public disclosure (negotiable) |

### Severity Ratings

We use the CVSS v3.1 scoring system:

| Severity | CVSS Score | Response Time |
|----------|------------|---------------|
| Critical | 9.0 - 10.0 | 24 hours |
| High | 7.0 - 8.9 | 72 hours |
| Medium | 4.0 - 6.9 | 1 week |
| Low | 0.1 - 3.9 | 2 weeks |

---

## Security Best Practices

When deploying SmartAP, follow these security best practices:

### Authentication & Authorization

- **Use strong JWT secrets** - Generate with `openssl rand -hex 32`
- **Enable HTTPS** - Never run production without TLS
- **Rotate tokens** - Set appropriate JWT expiration times
- **Use RBAC** - Assign minimal necessary permissions to users

### Database Security

- **Strong passwords** - Use unique, complex database passwords
- **Network isolation** - Run PostgreSQL in a private subnet
- **Encrypted connections** - Enable SSL for database connections
- **Regular backups** - Implement automated backup strategy

### API Security

- **Rate limiting** - Enabled by default, configure per your needs
- **CORS** - Restrict to your frontend domain in production
- **Input validation** - All inputs are validated via Pydantic models
- **SQL injection** - Protected via SQLAlchemy ORM

### Infrastructure Security

- **Container scanning** - Scan Docker images for vulnerabilities
- **Secrets management** - Use environment variables or secrets manager
- **Log sanitization** - Sensitive data is redacted from logs
- **Network policies** - Restrict pod-to-pod communication in Kubernetes

### Environment Variables

These sensitive variables should be kept secure:

```bash
# Critical secrets - never commit these
DATABASE_URL=            # Database connection string
JWT_SECRET_KEY=          # JWT signing key
GITHUB_TOKEN=            # AI model API token
REDIS_URL=               # Redis connection (if auth enabled)
FOXIT_LICENSE_KEY=       # Foxit SDK license
```

---

## Security Features

SmartAP includes several built-in security features:

### Authentication
- JWT-based authentication with refresh tokens
- Password hashing with bcrypt (12 rounds)
- Account lockout after failed attempts
- Session management and logout

### Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- API key authentication for service accounts
- Audit logging of all authorization decisions

### Data Protection
- Sensitive fields encrypted at rest
- TLS 1.3 for data in transit
- Database connection encryption
- Secure file upload handling

### Monitoring & Detection
- Failed login attempt tracking
- Anomaly detection for unusual access patterns
- Rate limiting with adaptive thresholds
- Real-time alerting for security events

### Compliance
- Audit trail for all invoice operations
- Data retention policies
- GDPR-ready data export/deletion
- SOC 2 Type II compatible controls

---

## Security Scanning

We perform regular security scanning:

### Automated Scans
- **Dependency scanning** - pip-audit runs on every PR
- **SAST** - Bandit scans Python code for vulnerabilities
- **Container scanning** - Trivy scans Docker images
- **Secret scanning** - Gitleaks prevents committed secrets

### Manual Reviews
- Code review required for all changes
- Security-focused review for auth/authz changes
- Penetration testing before major releases
- Third-party security audits annually

---

## Known Security Considerations

### File Uploads
- Invoice uploads are restricted to PDF, PNG, JPEG, TIFF
- Maximum file size: 50MB (configurable)
- Files are scanned before processing
- Uploaded files stored with randomized names

### API Tokens
- GitHub/OpenAI tokens should have minimal scopes
- Tokens are never logged or exposed in responses
- Token usage is monitored for anomalies

### Third-Party Dependencies
- Dependencies are pinned to specific versions
- Dependabot alerts are triaged weekly
- Critical vulnerabilities patched within 24 hours

---

## Acknowledgments

We appreciate the security researchers who help keep SmartAP secure:

| Researcher | Finding | Date |
|------------|---------|------|
| *Be the first!* | - | - |

If you report a valid vulnerability, you'll be acknowledged here (with your permission).

---

## PGP Key

For encrypted communications:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----
[PGP key would be added here in production]
-----END PGP PUBLIC KEY BLOCK-----
```

---

## Contact

- **Security issues**: security@smartap.example.com
- **General inquiries**: support@smartap.example.com
- **GitHub Security Advisories**: [Report here](../../security/advisories)
