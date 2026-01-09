# SmartAP API Reference

**Version:** 1.0  
**Base URL:** `https://api.smartap.io/api/v1` (Production)  
**Local URL:** `http://localhost:8000/api/v1`  
**OpenAPI Spec:** `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [Invoices](#invoices)
4. [Vendors](#vendors)
5. [Purchase Orders](#purchase-orders)
6. [Approvals](#approvals)
7. [Users & Roles](#users--roles)
8. [Reports & Analytics](#reports--analytics)
9. [Webhooks](#webhooks)
10. [System](#system)
11. [Error Codes](#error-codes)

---

## Authentication

SmartAP uses JWT (JSON Web Token) authentication. All API requests require a valid access token in the `Authorization` header.

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "finance_manager"
  }
}
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Using the Token

Include the access token in all subsequent requests:

```http
GET /api/v1/invoices
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Expiration

| Token Type | Default Expiration | Configurable |
|------------|-------------------|--------------|
| Access Token | 30 minutes | Yes (`ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Refresh Token | 7 days | Yes (`REFRESH_TOKEN_EXPIRE_DAYS`) |

### Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

### Get Current User

```http
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "finance_manager",
  "department": "Finance",
  "permissions": ["invoices:read", "invoices:write", "approvals:approve"],
  "created_at": "2026-01-01T00:00:00Z",
  "last_login": "2026-01-08T10:30:00Z"
}
```

---

## Common Patterns

### Request Format

All request bodies should be JSON:

```http
Content-Type: application/json
```

### Response Format

All responses follow a consistent structure:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "req_abc123xyz",
    "timestamp": "2026-01-08T10:30:00Z"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
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

### Pagination

List endpoints support pagination:

```http
GET /api/v1/invoices?page=1&limit=20
```

**Parameters:**
| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | integer | 1 | - | Page number (1-indexed) |
| `limit` | integer | 20 | 100 | Items per page |

**Paginated Response:**
```json
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
```

### Sorting

```http
GET /api/v1/invoices?sort=created_at&order=desc
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort` | string | `created_at` | Field to sort by |
| `order` | string | `desc` | Sort order (`asc` or `desc`) |

### Filtering

```http
GET /api/v1/invoices?status=pending_approval&vendor_id=123&date_from=2026-01-01
```

### Rate Limiting

Rate limits are enforced per API key:

| Tier | Requests/Minute | Requests/Hour |
|------|-----------------|---------------|
| Standard | 60 | 1,000 |
| Premium | 300 | 10,000 |
| Enterprise | 1,000 | 50,000 |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704729600
```

---

## Invoices

### List Invoices

```http
GET /api/v1/invoices
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `vendor_id` | integer | Filter by vendor |
| `date_from` | date | Start date (YYYY-MM-DD) |
| `date_to` | date | End date (YYYY-MM-DD) |
| `amount_min` | decimal | Minimum amount |
| `amount_max` | decimal | Maximum amount |
| `search` | string | Search invoice number |
| `page` | integer | Page number |
| `limit` | integer | Items per page |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "invoice_number": "INV-2026-001",
      "vendor": {
        "id": 123,
        "name": "Acme Corp"
      },
      "status": "pending_approval",
      "invoice_date": "2026-01-05",
      "due_date": "2026-02-04",
      "subtotal": 1000.00,
      "tax_amount": 100.00,
      "total": 1100.00,
      "currency": "USD",
      "confidence_score": 0.95,
      "created_at": "2026-01-08T10:00:00Z",
      "updated_at": "2026-01-08T10:30:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 156
  }
}
```

### Get Invoice

```http
GET /api/v1/invoices/{id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "invoice_number": "INV-2026-001",
    "vendor": {
      "id": 123,
      "name": "Acme Corp",
      "tax_id": "12-3456789",
      "payment_terms": "Net 30"
    },
    "purchase_order": {
      "id": 456,
      "po_number": "PO-2026-100"
    },
    "status": "pending_approval",
    "invoice_date": "2026-01-05",
    "due_date": "2026-02-04",
    "subtotal": 1000.00,
    "tax_amount": 100.00,
    "total": 1100.00,
    "currency": "USD",
    "line_items": [
      {
        "id": 1,
        "description": "Widget A",
        "quantity": 10,
        "unit_price": 100.00,
        "amount": 1000.00,
        "category": "Office Supplies"
      }
    ],
    "extracted_data": {
      "raw_text": "...",
      "structured_data": {...},
      "confidence_scores": {...}
    },
    "match_result": {
      "matched": true,
      "match_score": 0.98,
      "discrepancies": []
    },
    "fraud_result": {
      "risk_level": "LOW",
      "risk_score": 0.12,
      "flags": []
    },
    "approvals": [
      {
        "id": 1,
        "level": 1,
        "approver": {
          "id": 789,
          "name": "Jane Smith"
        },
        "status": "pending",
        "created_at": "2026-01-08T10:30:00Z"
      }
    ],
    "pdf_url": "/api/v1/invoices/1/pdf",
    "created_by": {
      "id": 100,
      "name": "John Doe"
    },
    "created_at": "2026-01-08T10:00:00Z",
    "updated_at": "2026-01-08T10:30:00Z"
  }
}
```

### Upload Invoice

```http
POST /api/v1/invoices/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: (binary PDF file)
vendor_id: 123
po_number: PO-2026-100 (optional)
notes: Monthly supplies order (optional)
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "invoice_number": null,
    "status": "uploaded",
    "message": "Invoice uploaded successfully. Processing will begin shortly.",
    "estimated_processing_time": "30-60 seconds"
  }
}
```

### Create Invoice (Manual)

```http
POST /api/v1/invoices
Authorization: Bearer {token}
Content-Type: application/json

{
  "invoice_number": "INV-2026-002",
  "vendor_id": 123,
  "po_id": 456,
  "invoice_date": "2026-01-08",
  "due_date": "2026-02-07",
  "subtotal": 500.00,
  "tax_amount": 50.00,
  "total": 550.00,
  "currency": "USD",
  "line_items": [
    {
      "description": "Service Fee",
      "quantity": 1,
      "unit_price": 500.00,
      "amount": 500.00
    }
  ],
  "notes": "Monthly service invoice"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "invoice_number": "INV-2026-002",
    "status": "created"
  }
}
```

### Update Invoice

```http
PUT /api/v1/invoices/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "invoice_number": "INV-2026-002-R",
  "total": 600.00,
  "notes": "Updated amount after correction"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "invoice_number": "INV-2026-002-R",
    "status": "updated"
  }
}
```

### Delete Invoice

```http
DELETE /api/v1/invoices/{id}
Authorization: Bearer {token}
```

**Response (204 No Content)**

### Reprocess Invoice

```http
POST /api/v1/invoices/{id}/reprocess
Authorization: Bearer {token}
Content-Type: application/json

{
  "agents": ["extractor", "matcher", "fraud"]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "reprocessing",
    "message": "Invoice reprocessing started"
  }
}
```

### Get Invoice History

```http
GET /api/v1/invoices/{id}/history
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "action": "created",
      "user": {"id": 100, "name": "John Doe"},
      "changes": null,
      "created_at": "2026-01-08T10:00:00Z"
    },
    {
      "id": 2,
      "action": "extracted",
      "user": null,
      "changes": {"status": ["uploaded", "extracted"]},
      "created_at": "2026-01-08T10:01:00Z"
    },
    {
      "id": 3,
      "action": "approved",
      "user": {"id": 789, "name": "Jane Smith"},
      "changes": {"status": ["pending_approval", "approved"]},
      "created_at": "2026-01-08T10:30:00Z"
    }
  ]
}
```

### Download Invoice PDF

```http
GET /api/v1/invoices/{id}/pdf
Authorization: Bearer {token}
```

**Response (200 OK):**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="INV-2026-001.pdf"

(binary PDF data)
```

### Bulk Upload

```http
POST /api/v1/invoices/bulk-upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: (ZIP file containing PDFs)
vendor_id: 123
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_abc123",
    "files_detected": 10,
    "status": "processing",
    "message": "Bulk upload started. You will be notified when complete."
  }
}
```

### Export Invoices

```http
GET /api/v1/invoices/export?format=csv&status=approved&date_from=2026-01-01
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Options | Description |
|-----------|------|---------|-------------|
| `format` | string | `csv`, `xlsx`, `json` | Export format |
| `status` | string | - | Filter by status |
| `date_from` | date | - | Start date |
| `date_to` | date | - | End date |

**Response (200 OK):**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="invoices_export_2026-01-08.csv"

invoice_number,vendor_name,total,status,created_at
INV-2026-001,Acme Corp,1100.00,approved,2026-01-08
...
```

---

## Vendors

### List Vendors

```http
GET /api/v1/vendors
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search by name |
| `is_approved` | boolean | Filter by approval status |
| `page` | integer | Page number |
| `limit` | integer | Items per page |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "name": "Acme Corp",
      "tax_id": "12-3456789",
      "email": "ap@acmecorp.com",
      "phone": "+1-555-123-4567",
      "payment_terms": "Net 30",
      "risk_score": 0.15,
      "is_approved": true,
      "invoice_count": 25,
      "total_spend": 125000.00,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 50
  }
}
```

### Get Vendor

```http
GET /api/v1/vendors/{id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "Acme Corp",
    "tax_id": "12-3456789",
    "address": "123 Business St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA",
    "email": "ap@acmecorp.com",
    "phone": "+1-555-123-4567",
    "payment_terms": "Net 30",
    "bank_name": "Chase Bank",
    "bank_account": "****1234",
    "bank_routing": "****5678",
    "risk_score": 0.15,
    "is_approved": true,
    "approved_by": {"id": 1, "name": "Admin User"},
    "approved_at": "2025-01-15T10:00:00Z",
    "notes": "Preferred supplier for office supplies",
    "stats": {
      "invoice_count": 25,
      "total_spend": 125000.00,
      "average_invoice": 5000.00,
      "last_invoice_date": "2026-01-05"
    },
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2026-01-08T10:00:00Z"
  }
}
```

### Create Vendor

```http
POST /api/v1/vendors
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Vendor Inc",
  "tax_id": "98-7654321",
  "address": "456 Commerce Ave",
  "city": "Los Angeles",
  "state": "CA",
  "postal_code": "90001",
  "country": "USA",
  "email": "billing@newvendor.com",
  "phone": "+1-555-987-6543",
  "payment_terms": "Net 45",
  "bank_name": "Bank of America",
  "bank_account": "123456789",
  "bank_routing": "987654321"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 124,
    "name": "New Vendor Inc",
    "is_approved": false,
    "message": "Vendor created. Awaiting approval."
  }
}
```

### Update Vendor

```http
PUT /api/v1/vendors/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "payment_terms": "Net 60",
  "notes": "Updated payment terms per agreement"
}
```

### Delete Vendor

```http
DELETE /api/v1/vendors/{id}
Authorization: Bearer {token}
```

### Approve Vendor

```http
POST /api/v1/vendors/{id}/approve
Authorization: Bearer {token}
Content-Type: application/json

{
  "notes": "Verified tax ID and bank details"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 124,
    "is_approved": true,
    "approved_at": "2026-01-08T11:00:00Z"
  }
}
```

### Get Vendor Invoices

```http
GET /api/v1/vendors/{id}/invoices
Authorization: Bearer {token}
```

### Get Vendor Purchase Orders

```http
GET /api/v1/vendors/{id}/pos
Authorization: Bearer {token}
```

---

## Purchase Orders

### List Purchase Orders

```http
GET /api/v1/purchase-orders
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `vendor_id` | integer | Filter by vendor |
| `date_from` | date | Order date start |
| `date_to` | date | Order date end |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 456,
      "po_number": "PO-2026-100",
      "vendor": {
        "id": 123,
        "name": "Acme Corp"
      },
      "status": "approved",
      "order_date": "2025-12-15",
      "expected_date": "2026-01-15",
      "total": 5000.00,
      "currency": "USD",
      "invoiced_amount": 1100.00,
      "remaining_amount": 3900.00,
      "created_at": "2025-12-15T10:00:00Z"
    }
  ]
}
```

### Get Purchase Order

```http
GET /api/v1/purchase-orders/{id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "po_number": "PO-2026-100",
    "vendor": {...},
    "status": "approved",
    "order_date": "2025-12-15",
    "expected_date": "2026-01-15",
    "subtotal": 4545.45,
    "tax_amount": 454.55,
    "total": 5000.00,
    "currency": "USD",
    "shipping_address": "123 Main St, New York, NY 10001",
    "billing_address": "456 Finance Blvd, New York, NY 10002",
    "line_items": [
      {
        "id": 1,
        "description": "Widget A",
        "quantity": 50,
        "unit_price": 90.91,
        "amount": 4545.45,
        "received_qty": 10
      }
    ],
    "linked_invoices": [
      {
        "id": 1,
        "invoice_number": "INV-2026-001",
        "total": 1100.00
      }
    ],
    "created_by": {...},
    "approved_by": {...},
    "created_at": "2025-12-15T10:00:00Z"
  }
}
```

### Create Purchase Order

```http
POST /api/v1/purchase-orders
Authorization: Bearer {token}
Content-Type: application/json

{
  "vendor_id": 123,
  "order_date": "2026-01-08",
  "expected_date": "2026-02-08",
  "shipping_address": "123 Main St, New York, NY 10001",
  "line_items": [
    {
      "description": "Widget B",
      "quantity": 100,
      "unit_price": 50.00
    }
  ],
  "notes": "Rush order"
}
```

### Import from ERP

```http
POST /api/v1/purchase-orders/import
Authorization: Bearer {token}
Content-Type: application/json

{
  "erp_type": "netsuite",
  "po_numbers": ["PO-2026-101", "PO-2026-102"],
  "sync_line_items": true
}
```

---

## Approvals

### List Pending Approvals

```http
GET /api/v1/approvals
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `pending`, `approved`, `rejected` |

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "invoice": {
        "id": 1,
        "invoice_number": "INV-2026-001",
        "vendor_name": "Acme Corp",
        "total": 1100.00
      },
      "level": 1,
      "status": "pending",
      "due_date": "2026-01-10T17:00:00Z",
      "created_at": "2026-01-08T10:30:00Z"
    }
  ]
}
```

### Approve Invoice

```http
POST /api/v1/approvals/{id}/approve
Authorization: Bearer {token}
Content-Type: application/json

{
  "comment": "Approved. Amounts verified against PO."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "approved",
    "decision": "approve",
    "decided_at": "2026-01-08T11:00:00Z",
    "next_approval": {
      "level": 2,
      "approver": "Finance Director"
    }
  }
}
```

### Reject Invoice

```http
POST /api/v1/approvals/{id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "comment": "Amount exceeds approved PO by 15%. Please clarify.",
  "reason_code": "AMOUNT_MISMATCH"
}
```

### Delegate Approval

```http
POST /api/v1/approvals/{id}/delegate
Authorization: Bearer {token}
Content-Type: application/json

{
  "delegate_to_user_id": 456,
  "comment": "Out of office. Delegating to backup approver."
}
```

### Approval Rules

#### List Rules

```http
GET /api/v1/approval-rules
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Manager Approval > $1000",
      "condition_type": "amount",
      "condition_operator": "greater_than",
      "condition_value": "1000",
      "approver": {"id": 789, "name": "Department Manager"},
      "priority": 1,
      "is_active": true
    },
    {
      "id": 2,
      "name": "Director Approval > $5000",
      "condition_type": "amount",
      "condition_operator": "greater_than",
      "condition_value": "5000",
      "approver": {"id": 101, "name": "Finance Director"},
      "priority": 2,
      "is_active": true
    }
  ]
}
```

#### Create Rule

```http
POST /api/v1/approval-rules
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Vendor Approval",
  "condition_type": "vendor_status",
  "condition_operator": "equals",
  "condition_value": "new",
  "approver_id": 789,
  "priority": 3
}
```

---

## Users & Roles

### List Users

```http
GET /api/v1/users
Authorization: Bearer {token}
```

**Required Permission:** `users:read`

### Get User

```http
GET /api/v1/users/{id}
Authorization: Bearer {token}
```

### Create User

```http
POST /api/v1/users
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "newuser@example.com",
  "full_name": "New User",
  "password": "SecurePassword123!",
  "role_id": 3,
  "department_id": 1
}
```

**Required Permission:** `users:create`

### Update User Role

```http
PUT /api/v1/users/{id}/role
Authorization: Bearer {token}
Content-Type: application/json

{
  "role_id": 2
}
```

### List Roles

```http
GET /api/v1/roles
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "admin",
      "display_name": "Administrator",
      "permissions": ["*"]
    },
    {
      "id": 2,
      "name": "finance_manager",
      "display_name": "Finance Manager",
      "permissions": ["invoices:*", "vendors:*", "approvals:approve", "reports:*"]
    },
    {
      "id": 3,
      "name": "ap_clerk",
      "display_name": "AP Clerk",
      "permissions": ["invoices:read", "invoices:create", "vendors:read"]
    }
  ]
}
```

---

## Reports & Analytics

### Dashboard Summary

```http
GET /api/v1/reports/dashboard
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "invoices": {
      "total": 156,
      "pending_approval": 12,
      "approved_today": 8,
      "rejected_today": 1
    },
    "amounts": {
      "total_pending": 45000.00,
      "total_approved_mtd": 125000.00,
      "average_processing_time_hours": 4.5
    },
    "trends": {
      "invoices_this_week": [10, 12, 8, 15, 11, 9, 14],
      "approval_rate": 0.92
    }
  }
}
```

### Invoice Status Report

```http
GET /api/v1/reports/invoice-status?date_from=2026-01-01&date_to=2026-01-31
Authorization: Bearer {token}
```

### Processing Time Report

```http
GET /api/v1/reports/processing-time?period=month
Authorization: Bearer {token}
```

### Vendor Spend Report

```http
GET /api/v1/reports/vendor-spend?top=10&period=quarter
Authorization: Bearer {token}
```

### Export Report

```http
GET /api/v1/reports/export/vendor-spend?format=pdf
Authorization: Bearer {token}
```

---

## Webhooks

### List Webhooks

```http
GET /api/v1/webhooks
Authorization: Bearer {token}
```

### Create Webhook

```http
POST /api/v1/webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["invoice.created", "invoice.approved", "invoice.rejected"],
  "secret": "your-webhook-secret"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "url": "https://your-server.com/webhook",
    "events": ["invoice.created", "invoice.approved", "invoice.rejected"],
    "is_active": true,
    "created_at": "2026-01-08T12:00:00Z"
  }
}
```

### Available Events

| Event | Description |
|-------|-------------|
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

### Webhook Payload

```json
{
  "id": "evt_abc123xyz",
  "event": "invoice.approved",
  "created_at": "2026-01-08T15:30:00Z",
  "data": {
    "invoice_id": 1,
    "invoice_number": "INV-2026-001",
    "vendor_id": 123,
    "vendor_name": "Acme Corp",
    "total": 1100.00,
    "approved_by": {
      "id": 789,
      "name": "Jane Smith"
    },
    "approved_at": "2026-01-08T15:30:00Z"
  }
}
```

### Verifying Webhooks

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## System

### Health Check

```http
GET /api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "smartap-api",
  "version": "0.1.0"
}
```

### Detailed Health

```http
GET /api/v1/health/detailed
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "smartap-api",
  "version": "0.1.0",
  "timestamp": "2026-01-09T12:00:00Z",
  "components": {
    "database": {"status": "healthy", "type": "postgresql"},
    "cache": {"status": "healthy", "type": "redis"},
    "ai": {"status": "configured", "provider": "github_models", "model": "openai/gpt-4.1"},
    "ocr": {"status": "configured", "provider": "foxit"},
    "storage": {"status": "healthy", "path": "./uploads"}
  },
  "issues": null
}
```

### Full Health Check

```http
GET /api/v1/health/full
```

Comprehensive health check including ERP integrations, eSign, and circuit breakers.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "smartap-api",
  "version": "0.1.0",
  "timestamp": "2026-01-09T12:00:00Z",
  "components": {
    "database": {"status": "healthy", "type": "postgresql", "latency_ms": 5.2},
    "cache": {"status": "healthy", "type": "redis", "latency_ms": 1.8, "memory_used_mb": 24.5},
    "ai": {"status": "configured", "provider": "github_models", "model": "openai/gpt-4.1"},
    "ocr": {"status": "configured", "provider": "foxit"},
    "erp": {"status": "configured", "providers": {"xero": {"status": "configured"}, "quickbooks": {"status": "configured"}}, "sync_enabled": true},
    "esign": {"status": "configured", "provider": "foxit_esign"},
    "circuit_breakers": {"status": "healthy", "breakers": {"foxit_ocr": "closed", "erp_sync": "closed", "ai_service": "closed"}, "open_count": 0},
    "storage": {"status": "healthy", "upload_dir": "./uploads", "disk_free_gb": 45.2, "disk_used_percent": 32.5}
  },
  "issues": null
}
```

**Response Status Codes:**
| Status | Health Status | Description |
|--------|--------------|-------------|
| `200` | `healthy` | All components operational |
| `200` | `degraded` | Some non-critical components failing |
| `503` | `unhealthy` | Critical components (database, storage) failing |

### Application Metrics

```http
GET /api/v1/metrics?minutes=60
```

Get application performance metrics for the specified time window.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minutes` | integer | 60 | Time window in minutes |

**Response (200 OK):**
```json
{
  "window_minutes": 60,
  "total_requests": 1523,
  "total_errors": 12,
  "error_rate": 0.79,
  "avg_duration_ms": 145.32,
  "top_endpoints": [
    {"endpoint": "GET /api/v1/invoices", "count": 450},
    {"endpoint": "POST /api/v1/upload", "count": 125},
    {"endpoint": "GET /api/v1/dashboard/stats", "count": 98}
  ],
  "slowest_endpoints": [
    {"endpoint": "POST /api/v1/process", "avg_ms": 2345.67},
    {"endpoint": "POST /api/v1/upload", "avg_ms": 890.45}
  ],
  "service_calls": {
    "foxit_ocr": {"total": 45, "success": 43, "failure": 2, "total_duration_ms": 12500.0},
    "ai_extraction": {"total": 45, "success": 45, "failure": 0, "total_duration_ms": 8900.0}
  },
  "uptime_seconds": 86400.5
}
```

### Endpoint Metrics

```http
GET /api/v1/metrics/endpoints
```

Get detailed per-endpoint statistics.

**Response (200 OK):**
```json
{
  "endpoints": {
    "GET /api/v1/invoices": {
      "total_requests": 450,
      "total_errors": 3,
      "error_rate": 0.67,
      "avg_duration_ms": 45.2,
      "min_duration_ms": 12.5,
      "max_duration_ms": 234.8,
      "status_codes": {"200": 447, "500": 3}
    },
    "POST /api/v1/upload": {
      "total_requests": 125,
      "total_errors": 5,
      "error_rate": 4.0,
      "avg_duration_ms": 890.45,
      "min_duration_ms": 250.0,
      "max_duration_ms": 3500.0,
      "status_codes": {"201": 120, "400": 3, "500": 2}
    }
  }
}
```

### Circuit Breaker Status

```http
GET /api/v1/metrics/circuit-breakers
```

Get current state of all circuit breakers for external service integrations.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "open_count": 0,
  "breakers": {
    "foxit_ocr": "closed",
    "foxit_esign": "closed",
    "erp_sync": "closed",
    "ai_service": "closed"
  }
}
```

**Circuit Breaker States:**
| State | Description |
|-------|-------------|
| `closed` | Normal operation - requests passing through |
| `open` | Service failing - requests blocked, retry after timeout |
| `half_open` | Testing - limited requests allowed to test recovery |

### System Settings

```http
GET /api/v1/settings
Authorization: Bearer {token}
```

**Required Permission:** `settings:read`

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request succeeded |
| `201` | Created | Resource created |
| `202` | Accepted | Request accepted for processing |
| `204` | No Content | Success with no response body |
| `400` | Bad Request | Invalid request syntax |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `409` | Conflict | Resource conflict (duplicate) |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Application Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Authentication failed |
| `AUTHORIZATION_ERROR` | 403 | Permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CIRCUIT_BREAKER_OPEN` | 503 | External service unavailable (circuit open) |
| `EXTERNAL_SERVICE_ERROR` | 502 | External service call failed |
| `PROCESSING_ERROR` | 500 | Invoice processing failed |
| `EXTRACTION_ERROR` | 500 | AI extraction failed |
| `MATCHING_ERROR` | 500 | PO matching failed |
| `ERP_SYNC_ERROR` | 502 | ERP synchronization failed |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Error Response Format

All errors follow a consistent format:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "detail": "vendor_id must be a valid UUID",
  "suggestions": [
    "Verify the vendor_id format is a valid UUID",
    "Check that the vendor exists in the system"
  ],
  "path": "/api/v1/invoices"
}
```

**Error Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `error_code` | string | Machine-readable error code |
| `message` | string | Human-readable error message |
| `detail` | string/null | Additional error details (when available) |
| `suggestions` | array/null | Suggested actions to resolve the error |
| `path` | string | Request path that caused the error |

### Circuit Breaker Error

When a circuit breaker is open, the response includes a `Retry-After` header:

```http
HTTP/1.1 503 Service Unavailable
Retry-After: 30
Content-Type: application/json

{
  "error_code": "CIRCUIT_BREAKER_OPEN",
  "message": "Service foxit_ocr is temporarily unavailable",
  "detail": "Circuit breaker is open due to repeated failures",
  "suggestions": [
    "Wait 30 seconds before retrying",
    "Check service status at /api/v1/metrics/circuit-breakers"
  ],
  "path": "/api/v1/upload"
}
```

### Error Response Example

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      },
      {
        "field": "total",
        "message": "Total must be a positive number"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123xyz",
    "timestamp": "2026-01-08T12:00:00Z"
  }
}
```

---

## SDK Examples

### Python

```python
import httpx

class SmartAPClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.client = httpx.Client()
        self._login(email, password)
    
    def _login(self, email: str, password: str):
        response = self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"
    
    def list_invoices(self, **params):
        response = self.client.get(f"{self.base_url}/invoices", params=params)
        return response.json()
    
    def upload_invoice(self, file_path: str, vendor_id: int):
        with open(file_path, "rb") as f:
            response = self.client.post(
                f"{self.base_url}/invoices/upload",
                files={"file": f},
                data={"vendor_id": vendor_id}
            )
        return response.json()

# Usage
client = SmartAPClient(
    "http://localhost:8000/api/v1",
    "user@example.com",
    "password"
)
invoices = client.list_invoices(status="pending_approval")
```

### JavaScript/TypeScript

```typescript
class SmartAPClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    this.token = data.access_token;
  }

  async listInvoices(params?: Record<string, string>): Promise<any> {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${this.baseUrl}/invoices?${query}`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    return response.json();
  }

  async uploadInvoice(file: File, vendorId: number): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('vendor_id', vendorId.toString());

    const response = await fetch(`${this.baseUrl}/invoices/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.token}` },
      body: formData,
    });
    return response.json();
  }
}

// Usage
const client = new SmartAPClient('http://localhost:8000/api/v1');
await client.login('user@example.com', 'password');
const invoices = await client.listInvoices({ status: 'pending_approval' });
```

---

## Related Documentation

- [Architecture Overview](./01_Architecture_Overview.md)
- [API Overview (Section 6)](./architecture/06_API_Overview.md)
- [Security Architecture](./architecture/07_Security_Architecture.md)
- [Quick Start Guide](./Quick_Start_Guide.md)

---

*Last Updated: January 2026*  
*API Version: 1.0*
