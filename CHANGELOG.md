# Changelog

All notable changes to SmartAP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- V3.5.1 Documentation completion (SECURITY.md, CHANGELOG.md, architecture docs)
- V3.5.2 Security hardening workflow (planned)
- V3.5.3 Release automation workflow (planned)

---

## [3.0.0] - 2026-01-10

### Added

#### Testing Infrastructure (V3.1-V3.3)
- Comprehensive pytest infrastructure with async fixtures
- Unit tests for all core services (extraction, matching, fraud detection)
- Integration tests for API endpoints with httpx AsyncClient
- E2E tests with Playwright for critical user flows
- Test coverage increased from ~40% to 80%+
- GitHub Actions CI/CD pipeline for automated testing

#### Performance Optimization (V3.4)
- Query optimization with batch loading and eager loading
- Redis caching layer for dashboard and analytics endpoints
- API performance benchmarks with SLA validation
- Response time improvements: Dashboard <500ms, Pagination <200ms
- Concurrent request handling: 10+ simultaneous requests

#### Documentation (V3.5)
- Security policy documentation (SECURITY.md)
- Changelog tracking (CHANGELOG.md)
- Updated architecture documentation
- API documentation improvements

### Changed
- Upgraded to Python 3.12 compatibility
- Improved error handling across all API endpoints
- Enhanced logging with structured JSON format
- Optimized database indexes for common queries

### Fixed
- Rate limiting middleware configuration for high-traffic scenarios
- Invoice status enum consistency across the application
- Database session management in async contexts

### Security
- Added rate limiting middleware (60 req/min, 1000 req/hour)
- Implemented request logging with sensitive data redaction
- Added circuit breaker pattern for external service calls
- Enhanced JWT token validation and refresh mechanism

---

## [2.0.0] - 2025-12-15

### Added

#### Workflow & Approval System (V2.3)
- Multi-level approval chains with configurable rules
- Amount-based, role-based, and department-based routing
- Email notifications for pending approvals
- Delegation and escalation support
- Approval audit trail

#### eSignature Integration (V2.4)
- Foxit eSign integration for digital signatures
- Multi-signer workflow support
- Webhook callbacks for signature events
- Audit log generation for compliance

#### ERP Integrations (V2.5)
- QuickBooks Online connector
- Xero integration
- SAP S/4HANA connector
- NetSuite SuiteConnect integration
- Bi-directional sync for vendors, invoices, and payments

#### Document Archival (V2.6)
- Automated retention policies
- Compliance-ready document storage
- Search and retrieval capabilities
- Bulk export functionality

### Changed
- Refactored agent architecture for better extensibility
- Improved vendor matching algorithm accuracy
- Enhanced dashboard with real-time analytics
- Optimized PDF processing pipeline

### Fixed
- Memory leak in long-running PDF processing
- Duplicate detection false positives
- Vendor matching edge cases with similar names

---

## [1.0.0] - 2025-10-01

### Added

#### Core Invoice Processing (V1.1)
- PDF upload and ingestion pipeline
- Foxit PDF SDK integration for text extraction
- OCR support for scanned documents
- Multi-format support (PDF, TIFF, PNG, JPEG)

#### AI Data Extraction (V1.2)
- GPT-4o powered extraction agent
- Structured data extraction (vendor, amounts, line items)
- Confidence scoring for extracted fields
- Human review queue for low-confidence items

#### 3-Way Matching (V1.3)
- Purchase order matching engine
- Line item comparison with tolerance
- Price and quantity variance detection
- Exception flagging and routing

#### Fraud Detection (V1.4)
- Duplicate invoice detection
- Vendor validation against master list
- Anomaly scoring based on historical patterns
- Risk-based approval routing

#### User Interface (V1.5)
- Next.js dashboard with TypeScript
- Invoice list with filtering and sorting
- Detail view with extracted data display
- Approval workflow interface

#### API Foundation (V1.6)
- FastAPI backend with async support
- JWT authentication system
- Role-based access control (RBAC)
- OpenAPI documentation (Swagger/ReDoc)

### Security
- JWT-based authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation with Pydantic

---

## [0.1.0] - 2025-08-01

### Added
- Initial project scaffolding
- Basic FastAPI application structure
- PostgreSQL database setup
- Docker development environment
- Initial documentation

---

## Migration Guides

### Upgrading to 3.0.0

No breaking changes. Upgrade steps:

1. Pull latest code: `git pull origin main`
2. Update dependencies: `pip install -r requirements.txt --upgrade`
3. Run database migrations: `alembic upgrade head`
4. Restart services: `docker-compose restart`

### Upgrading to 2.0.0

Breaking changes in API:
- `/api/v1/invoice/` → `/api/v1/invoices/`
- `/api/v1/vendor/` → `/api/v1/vendors/`

Migration steps:
1. Update API client to use new endpoints
2. Run database migrations for new tables
3. Configure ERP integration settings
4. Review approval chain configurations

---

## Version History

| Version | Release Date | Highlights |
|---------|--------------|------------|
| 3.0.0 | 2026-01-10 | Testing, Performance, OSS Launch |
| 2.0.0 | 2025-12-15 | Workflow, eSign, ERP Integration |
| 1.0.0 | 2025-10-01 | Core Processing, AI Extraction |
| 0.1.0 | 2025-08-01 | Initial Release |

---

[Unreleased]: https://github.com/your-org/smartap/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/your-org/smartap/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/your-org/smartap/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/your-org/smartap/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/your-org/smartap/releases/tag/v0.1.0
