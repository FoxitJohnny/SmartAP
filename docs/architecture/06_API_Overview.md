# SmartAP API Overview

**Section 6 of Architecture Documentation**

---

## Table of Contents

1. [API Architecture](#api-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Endpoint Categories](#endpoint-categories)
4. [Request/Response Formats](#requestresponse-formats)
5. [Webhooks](#webhooks)
6. [Rate Limiting](#rate-limiting)
7. [API Versioning](#api-versioning)

---

## API Architecture

### Design Principles

SmartAP follows REST API best practices with JSON payloads:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API Architecture Overview                              │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │   Web App    │     │   Mobile     │     │   External   │
    │  (Next.js)   │     │    Apps      │     │   Systems    │
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                     │
           └────────────────────┼─────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     API Gateway       │
                    │  (Rate Limit/Auth)    │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    FastAPI Router     │
                    │  /api/v1/...          │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
    ┌─────▼─────┐         ┌─────▼─────┐        ┌─────▼─────┐
    │  Invoices │         │  Vendors  │        │ Approvals │
    │   Router  │         │   Router  │        │   Router  │
    └─────┬─────┘         └─────┬─────┘        └─────┬─────┘
          │                     │                    │
          └─────────────────────┼────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Service Layer      │
                    │   (Business Logic)    │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Repository Layer    │
                    │    (Data Access)      │
                    └───────────────────────┘
```

### Base URL

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8000/api/v1` |
| Staging | `https://staging-api.smartap.io/api/v1` |
| Production | `https://api.smartap.io/api/v1` |

---

## Authentication & Authorization

### JWT Authentication

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Authentication Flow                            │
└─────────────────────────────────────────────────────────────────────┘

    Client                      API Server                    Database
       │                            │                            │
       │ POST /auth/login           │                            │
       │  {email, password}         │                            │
       │ ──────────────────────────►│                            │
       │                            │  Verify credentials        │
       │                            │ ──────────────────────────►│
       │                            │◄───────────────────────────│
       │                            │                            │
       │  {access_token,            │                            │
       │   refresh_token}           │                            │
       │◄──────────────────────────│                            │
       │                            │                            │
       │ GET /invoices              │                            │
       │ Authorization: Bearer xxx  │                            │
       │ ──────────────────────────►│                            │
       │                            │  Validate JWT              │
       │                            │  Check permissions         │
       │                            │                            │
       │  {invoices: [...]}         │                            │
       │◄──────────────────────────│                            │
```

### Auth Endpoints

```
POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
GET  /api/v1/auth/me
```

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| `admin` | Full system access, user management, settings |
| `finance_manager` | Invoice management, vendor approval, reports |
| `ap_clerk` | Upload invoices, basic edits, view reports |
| `approver` | Review and approve/reject invoices |
| `auditor` | Read-only access to all data and audit logs |
| `viewer` | Read-only access to assigned invoices |

### Permission Decorator

```python
from src.core.auth import require_permissions

@router.post("/invoices")
@require_permissions(["invoices:create"])
async def create_invoice(
    request: InvoiceCreate,
    current_user: User = Depends(get_current_user)
):
    ...
```

---

## Endpoint Categories

### Invoices

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Invoice Endpoints                               │
└─────────────────────────────────────────────────────────────────────┘

GET    /api/v1/invoices                 # List all invoices (paginated)
GET    /api/v1/invoices/{id}            # Get single invoice
POST   /api/v1/invoices                 # Create invoice
POST   /api/v1/invoices/upload          # Upload PDF invoice
PUT    /api/v1/invoices/{id}            # Update invoice
DELETE /api/v1/invoices/{id}            # Delete invoice
POST   /api/v1/invoices/{id}/reprocess  # Trigger reprocessing
GET    /api/v1/invoices/{id}/history    # Get invoice audit history
GET    /api/v1/invoices/{id}/pdf        # Download original PDF
POST   /api/v1/invoices/{id}/match      # Manual PO matching
POST   /api/v1/invoices/bulk-upload     # Bulk upload (ZIP)
GET    /api/v1/invoices/export          # Export to CSV/Excel

Query Parameters:
  - status: Filter by status (e.g., pending_approval)
  - vendor_id: Filter by vendor
  - date_from, date_to: Date range filter
  - amount_min, amount_max: Amount range filter
  - page, limit: Pagination
  - sort, order: Sorting
  - search: Full-text search
```

### Vendors

```
GET    /api/v1/vendors                  # List all vendors
GET    /api/v1/vendors/{id}             # Get single vendor
POST   /api/v1/vendors                  # Create vendor
PUT    /api/v1/vendors/{id}             # Update vendor
DELETE /api/v1/vendors/{id}             # Delete vendor
POST   /api/v1/vendors/{id}/approve     # Approve vendor
GET    /api/v1/vendors/{id}/invoices    # Get vendor's invoices
GET    /api/v1/vendors/{id}/pos         # Get vendor's POs
POST   /api/v1/vendors/import           # Bulk import from CSV
GET    /api/v1/vendors/export           # Export to CSV
```

### Purchase Orders

```
GET    /api/v1/purchase-orders          # List all POs
GET    /api/v1/purchase-orders/{id}     # Get single PO
POST   /api/v1/purchase-orders          # Create PO
PUT    /api/v1/purchase-orders/{id}     # Update PO
DELETE /api/v1/purchase-orders/{id}     # Delete PO
POST   /api/v1/purchase-orders/{id}/approve  # Approve PO
GET    /api/v1/purchase-orders/{id}/lines    # Get PO line items
POST   /api/v1/purchase-orders/import   # Import from ERP
```

### Approvals

```
GET    /api/v1/approvals                # List pending approvals for user
GET    /api/v1/approvals/{id}           # Get approval details
POST   /api/v1/approvals/{id}/approve   # Approve invoice
POST   /api/v1/approvals/{id}/reject    # Reject invoice
POST   /api/v1/approvals/{id}/delegate  # Delegate to another user
GET    /api/v1/approval-rules           # List approval rules
POST   /api/v1/approval-rules           # Create approval rule
PUT    /api/v1/approval-rules/{id}      # Update approval rule
DELETE /api/v1/approval-rules/{id}      # Delete approval rule
```

### Users & Roles

```
GET    /api/v1/users                    # List users (admin only)
GET    /api/v1/users/{id}               # Get user details
POST   /api/v1/users                    # Create user
PUT    /api/v1/users/{id}               # Update user
DELETE /api/v1/users/{id}               # Delete/deactivate user
PUT    /api/v1/users/{id}/role          # Update user role
GET    /api/v1/roles                    # List all roles
GET    /api/v1/roles/{id}/permissions   # Get role permissions
```

### Reports & Analytics

```
GET    /api/v1/reports/dashboard        # Dashboard summary
GET    /api/v1/reports/invoice-status   # Invoice status breakdown
GET    /api/v1/reports/processing-time  # Average processing times
GET    /api/v1/reports/vendor-spend     # Spend by vendor
GET    /api/v1/reports/approval-metrics # Approval workflow metrics
GET    /api/v1/reports/aging            # Invoice aging report
GET    /api/v1/reports/export/{type}    # Export report to PDF/Excel
```

### System & Integration

```
GET    /api/v1/health                   # Health check
GET    /api/v1/health/detailed          # Detailed health status
GET    /api/v1/settings                 # Get system settings
PUT    /api/v1/settings                 # Update settings
GET    /api/v1/audit-logs               # View audit logs
GET    /api/v1/webhooks                 # List webhooks
POST   /api/v1/webhooks                 # Create webhook
DELETE /api/v1/webhooks/{id}            # Delete webhook
GET    /api/v1/integrations             # List ERP integrations
POST   /api/v1/integrations/{type}/sync # Sync with ERP
```

---

## Request/Response Formats

### Standard Request Format

```json
// POST /api/v1/invoices/upload
{
    "vendor_id": 123,
    "po_number": "PO-2026-001",
    "invoice_date": "2026-01-08",
    "notes": "Monthly supplies order"
}

// File upload with multipart/form-data
// Field: file (PDF file)
// Field: metadata (JSON string with above fields)
```

### Standard Response Format

```json
// Success Response
{
    "success": true,
    "data": {
        "id": 456,
        "invoice_number": "INV-2026-001",
        "status": "extracting",
        "vendor": {
            "id": 123,
            "name": "Acme Corp"
        },
        "total": 1500.00,
        "created_at": "2026-01-08T10:30:00Z"
    },
    "meta": {
        "request_id": "req_abc123xyz"
    }
}

// List Response (Paginated)
{
    "success": true,
    "data": [...],
    "meta": {
        "page": 1,
        "limit": 20,
        "total": 156,
        "total_pages": 8,
        "has_next": true,
        "has_prev": false
    }
}

// Error Response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid invoice data",
        "details": [
            {
                "field": "vendor_id",
                "message": "Vendor not found"
            }
        ]
    },
    "meta": {
        "request_id": "req_abc123xyz"
    }
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful GET, PUT |
| `201` | Created | Successful POST |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Validation error |
| `401` | Unauthorized | Missing/invalid token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Duplicate resource |
| `422` | Unprocessable Entity | Business logic error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |

---

## Webhooks

### Webhook Events

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Webhook Event Flow                             │
└─────────────────────────────────────────────────────────────────────┘

     SmartAP                         Your Server
        │                                │
        │  POST /your-webhook-url        │
        │  X-Webhook-Signature: xxx      │
        │  {                             │
        │    "event": "invoice.approved",│
        │    "data": {...}               │
        │  }                             │
        │ ─────────────────────────────► │
        │                                │
        │         200 OK                 │
        │ ◄───────────────────────────── │
```

### Available Events

| Event | Trigger |
|-------|---------|
| `invoice.created` | New invoice uploaded |
| `invoice.extracted` | OCR extraction complete |
| `invoice.matched` | PO matching complete |
| `invoice.pending_approval` | Ready for approval |
| `invoice.approved` | Invoice approved |
| `invoice.rejected` | Invoice rejected |
| `invoice.paid` | Invoice marked as paid |
| `vendor.created` | New vendor added |
| `vendor.approved` | Vendor approved |
| `approval.requested` | Approval requested |
| `approval.reminder` | Approval reminder sent |

### Webhook Payload

```json
{
    "id": "evt_abc123xyz",
    "event": "invoice.approved",
    "created_at": "2026-01-08T15:30:00Z",
    "data": {
        "invoice_id": 456,
        "invoice_number": "INV-2026-001",
        "vendor_id": 123,
        "vendor_name": "Acme Corp",
        "total": 1500.00,
        "approved_by": {
            "id": 789,
            "name": "Jane Smith"
        },
        "approved_at": "2026-01-08T15:30:00Z"
    }
}
```

### Webhook Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature using HMAC-SHA256."""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

---

## Rate Limiting

### Rate Limit Tiers

| Tier | Requests/Minute | Requests/Hour | Burst |
|------|-----------------|---------------|-------|
| Standard | 60 | 1,000 | 100 |
| Premium | 300 | 10,000 | 500 |
| Enterprise | 1,000 | 50,000 | 2,000 |

### Rate Limit Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704729600
X-RateLimit-Retry-After: 30
```

### Handling Rate Limits

```python
import time

def make_api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('X-RateLimit-Retry-After', 60))
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

---

## API Versioning

### Version Strategy

SmartAP uses URL-based versioning:

```
/api/v1/invoices    # Current stable version
/api/v2/invoices    # Next major version (when available)
```

### Deprecation Policy

1. **Announcement**: 6 months notice before deprecation
2. **Sunset Header**: `Sunset: Sat, 01 Jan 2027 00:00:00 GMT`
3. **Migration Guide**: Detailed upgrade documentation
4. **Parallel Operation**: Old version runs 3 months after new release

### Version Headers

```
API-Version: 2026-01-01
Deprecation: true
Sunset: 2027-01-01
Link: <https://docs.smartap.io/migration/v2>; rel="successor-version"
```

---

## OpenAPI Specification

Interactive API documentation available at:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Example: OpenAPI Schema

```yaml
openapi: 3.1.0
info:
  title: SmartAP API
  version: 1.0.0
  description: AI-Powered Accounts Payable Automation

servers:
  - url: https://api.smartap.io/api/v1
    description: Production
  - url: https://staging-api.smartap.io/api/v1
    description: Staging

security:
  - bearerAuth: []

paths:
  /invoices:
    get:
      summary: List invoices
      operationId: listInvoices
      tags: [Invoices]
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [uploaded, extracting, pending_approval, approved]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: List of invoices
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InvoiceList'
```

---

## Related Documentation

- **[API Reference](../API_Reference.md)** - Complete endpoint documentation
- **[Section 5: Data Model](./05_Data_Model.md)** - Database schema
- **[Section 7: Security Architecture](./07_Security_Architecture.md)** - Authentication details
- **[SDK Documentation](../sdk/)** - Client SDKs for various languages

---

*Continue to [Section 7: Security Architecture](./07_Security_Architecture.md)*
