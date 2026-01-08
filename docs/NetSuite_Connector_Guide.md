# NetSuite Connector Implementation Guide

## Overview

The NetSuite connector enables SmartAP to integrate with Oracle NetSuite ERP using Token-Based Authentication (TBA) and custom RESTlets for data synchronization.

## Architecture

### Authentication Method
- **OAuth 1.0a (Token-Based Authentication - TBA)**
- Uses consumer key/secret + token ID/secret
- No token expiration (permanent access)
- HMAC-SHA256 signature generation

### API Integration
- **Custom RESTlets**: NetSuite requires deploying custom SuiteScript RESTlets for data operations
- **RESTlet Base URL**: `https://{account_id}.restlets.api.netsuite.com/app/site/hosting/restlet.nl`
- **Query Parameters**: `script={script_id}&deploy={deploy_id}`

### Required RESTlets

You must deploy the following RESTlets in your NetSuite account:

1. **Vendor RESTlet** (`customscript_vendor_restlet` / `customdeploy_vendor_restlet`)
   - GET: List vendors with optional filters (lastModifiedDate, limit)
   - Returns: Array of vendor records with addresses, contacts, payment terms

2. **Purchase Order RESTlet** (`customscript_po_restlet` / `customdeploy_po_restlet`)
   - GET: List purchase orders with optional filters (lastModifiedDate, status, limit)
   - Returns: Array of PO records with line items, vendor references

3. **Vendor Bill RESTlet** (`customscript_bill_restlet` / `customdeploy_bill_restlet`)
   - POST: Create vendor bill from SmartAP invoice
   - GET: Retrieve bill details including payment status
   - Returns: Bill record with internal ID, status, amounts

4. **Account RESTlet** (`customscript_account_restlet` / `customdeploy_account_restlet`)
   - GET: List chart of accounts (expense accounts)
   - Returns: Array of account records with numbers, names, types

5. **Tax Code RESTlet** (`customscript_tax_restlet` / `customdeploy_tax_restlet`)
   - GET: List tax codes and tax groups
   - Returns: Array of tax code records with rates

## Setup Instructions

### Step 1: Enable Token-Based Authentication in NetSuite

1. **Navigate to Setup > Company > Enable Features**
   - Go to **SuiteCloud** tab
   - Check **"SuiteTalk (Web Services)"**
   - Check **"REST Web Services"**
   - Check **"Token-Based Authentication"**
   - Save changes

2. **Create Integration Record**
   - Navigate to **Setup > Integration > Manage Integrations > New**
   - Enter integration name: "SmartAP Integration"
   - Check **"Token-Based Authentication"**
   - Uncheck **"TBA: Authorization Flow"** (we use direct TBA)
   - Check **"User Credentials"**
   - Save and note down:
     - **Consumer Key**
     - **Consumer Secret**

3. **Create Access Token**
   - Navigate to **Setup > Users/Roles > Access Tokens > New**
   - Select the integration: "SmartAP Integration"
   - Select application: "SmartAP"
   - Select user with appropriate permissions
   - Save and note down:
     - **Token ID**
     - **Token Secret**
   - ⚠️ **Important**: Token secret is shown only once. Store it securely.

### Step 2: Deploy Required RESTlets

1. **Upload RESTlet Scripts**
   - Navigate to **Customization > Scripting > Scripts > New**
   - Upload SuiteScript 2.1 files for each RESTlet
   - Set script type: **RESTlet**
   - Define GET/POST entry points

2. **Deploy Scripts**
   - For each script, click **Deploy Script**
   - Select deployment status: **Released**
   - Set audience: **All Roles** or specific role
   - Note down **Script ID** and **Deploy ID** for each:
     - Vendor: `customscript_vendor_restlet` / `customdeploy_vendor_restlet`
     - Purchase Order: `customscript_po_restlet` / `customdeploy_po_restlet`
     - Vendor Bill: `customscript_bill_restlet` / `customdeploy_bill_restlet`
     - Account: `customscript_account_restlet` / `customdeploy_account_restlet`
     - Tax Code: `customscript_tax_restlet` / `customdeploy_tax_restlet`

3. **Get RESTlet Base URL**
   - Open any deployed RESTlet
   - Copy the **External URL**
   - Extract base URL (e.g., `https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl`)

### Step 3: Configure NetSuite Connection in SmartAP

1. **Navigate to ERP Connections page** in SmartAP frontend
2. **Click "Create Connection"**
3. **Step 1: System Selection**
   - Connection Name: "NetSuite Production"
   - ERP System: Select **"NetSuite"**
   - Click **"Next: Authentication"**

4. **Step 2: Enter Credentials**
   - **Account ID**: Your NetSuite account ID (e.g., "1234567")
   - **Consumer Key**: Integration consumer key
   - **Consumer Secret**: Integration consumer secret
   - **Token ID**: Access token ID
   - **Token Secret**: Access token secret
   - **RESTlet Base URL**: `https://{account_id}.restlets.api.netsuite.com/app/site/hosting/restlet.nl`
   - Click **"Next: Test Connection"**

5. **Step 3: Test Connection**
   - Click **"Test Connection"**
   - Verify successful connection
   - Click **"Complete Setup"**

## NetSuite Data Mapping

### Vendor Mapping

| NetSuite Field | SmartAP Field | Notes |
|----------------|---------------|-------|
| `id` (internalId) | `external_id` | Internal ID for API operations |
| `entityId` | `name` | Vendor display name |
| `companyName` | `name` | Company name (fallback) |
| `email` | `email` | Primary email |
| `phone` | `phone` | Primary phone |
| `defaultAddress` | `address` | Concatenated address fields |
| `taxIdNum` | `tax_id` | Tax identification number |
| `terms.name` | `payment_terms` | Payment terms reference |
| `currency.name` | `currency` | Currency code |
| `isInactive` | `is_active` | Inverted boolean |

### Purchase Order Mapping

| NetSuite Field | SmartAP Field | Notes |
|----------------|---------------|-------|
| `id` | `external_id` | Internal ID |
| `tranId` | `po_number` | PO document number |
| `entity.internalId` | `vendor_id` | Vendor reference |
| `entity.name` | `vendor_name` | Vendor name |
| `total` | `total_amount` | Converted to cents (x100) |
| `currency.name` | `currency` | Currency code |
| `status.name` | `status` | PO status |
| `tranDate` | `created_date` | Transaction date |
| `item.items[]` | `line_items` | Array of line items |

### Invoice (Vendor Bill) Mapping

| SmartAP Field | NetSuite Field | Notes |
|---------------|----------------|-------|
| `vendor_id` | `entity.internalId` | Vendor reference |
| `invoice_number` | `tranId` | External invoice number |
| `invoice_date` | `tranDate` | Invoice date (MM/DD/YYYY) |
| `due_date` | `dueDate` | Due date (MM/DD/YYYY) |
| `description` | `memo` | Invoice memo |
| `line_items[].item_id` | `item.items[].item.internalId` | Item reference |
| `line_items[].description` | `item.items[].description` | Line description |
| `line_items[].quantity` | `item.items[].quantity` | Quantity |
| `line_items[].unit_price` | `item.items[].rate` | Unit price (converted from cents) |
| `line_items[].amount` | `item.items[].amount` | Line total (converted from cents) |
| `line_items[].account_id` | `item.items[].account.internalId` | Expense account |

## Synchronization Flow

### 1. Vendor Sync (Every 60 minutes)

```
SmartAP → NetSuite GET /vendor → Parse vendors → Create/Update in SmartAP DB
```

- Fetches vendors from NetSuite
- Filters by `lastModifiedDate` for incremental sync
- Creates new vendors or updates existing based on `external_id` mapping
- Logs sync results in `erp_sync_logs` table

### 2. Purchase Order Sync (Every 30 minutes)

```
SmartAP → NetSuite GET /purchaseorder → Parse POs → Store in SmartAP DB
```

- Fetches purchase orders with optional status filter
- Parses line items and vendor references
- Stores for matching with incoming invoices
- Tracks sync status and errors

### 3. Invoice Export (On-demand or automated)

```
SmartAP Invoice → Build NetSuite Bill → POST /vendorbill → Store mapping
```

- Converts SmartAP invoice to NetSuite vendor bill format
- Posts to NetSuite via Bill RESTlet
- Stores invoice mapping with `external_invoice_id`
- Enables payment status tracking

### 4. Payment Status Sync (Every 15 minutes)

```
For each exported invoice: GET /vendorbill → Check payment status → Update SmartAP
```

- Queries NetSuite for bill payment status
- Updates SmartAP invoice status: unpaid, partial, paid
- Tracks paid amounts and remaining balances

## Rate Limiting

NetSuite enforces concurrency and governance limits:

- **Concurrency Limit**: 10 concurrent requests per account (configurable)
- **Governance Limit**: 10,000 units per hour (varies by record type)
- **SmartAP Implementation**:
  - Semaphore limiting to 5 concurrent requests
  - Automatic retry with exponential backoff
  - Request throttling to stay within limits

## Error Handling

### Common NetSuite Errors

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `INVALID_KEY_OR_REF` | Invalid record reference | Check vendor/item internal IDs |
| `INSUFFICIENT_PERMISSION` | User lacks permissions | Grant required permissions to token user |
| `SSS_REQUEST_LIMIT_EXCEEDED` | Rate limit exceeded | Reduce sync frequency or concurrent requests |
| `INVALID_LOGIN_CREDENTIALS` | Authentication failed | Verify consumer key/secret and token ID/secret |
| `INVALID_SIGNATURE` | OAuth signature mismatch | Check credential configuration |
| `USER_ERROR` | Validation error | Review record data and required fields |

### Error Logging

All errors are logged in:
- **`erp_sync_logs`** table with status `FAILED` or `PARTIAL`
- **Application logs** with detailed error messages and stack traces
- **Frontend UI** displays user-friendly error messages

## Testing Checklist

### Connection Testing
- [ ] Test connection creates successfully
- [ ] OAuth signature generation works
- [ ] RESTlet authentication succeeds
- [ ] Account information retrieved

### Vendor Sync Testing
- [ ] Vendor list retrieval works
- [ ] Vendor parsing handles all fields correctly
- [ ] Vendor creation in SmartAP succeeds
- [ ] Vendor updates work for existing records
- [ ] Incremental sync (since date) works
- [ ] Error handling logs failures

### Purchase Order Sync Testing
- [ ] PO list retrieval works
- [ ] Line item parsing correct
- [ ] Vendor references resolved
- [ ] Status filtering works
- [ ] Sync logs created properly

### Invoice Export Testing
- [ ] Invoice converts to vendor bill format
- [ ] Vendor reference mapping works
- [ ] Line items post correctly
- [ ] Account references valid
- [ ] External ID stored in mapping table
- [ ] Error handling for invalid data

### Payment Status Sync Testing
- [ ] Bill retrieval works
- [ ] Payment status detected correctly
- [ ] SmartAP invoice status updates
- [ ] Paid amounts calculated correctly
- [ ] Sync runs on schedule

### Rate Limiting Testing
- [ ] Concurrent request limiting works
- [ ] No rate limit errors under normal load
- [ ] Graceful handling when limits exceeded

## Security Considerations

1. **Credential Storage**
   - Consumer secret stored encrypted in database
   - Token secret stored encrypted in database
   - Never log credentials in plain text

2. **OAuth Signature**
   - HMAC-SHA256 signature ensures request integrity
   - Timestamp prevents replay attacks
   - Nonce ensures uniqueness

3. **SSL/TLS**
   - All API requests over HTTPS
   - Certificate verification enabled

4. **Role Permissions**
   - Grant minimum required permissions to token user
   - Recommended permissions:
     - Vendor: View, Create, Edit
     - Purchase Order: View
     - Vendor Bill: View, Create, Edit
     - Account: View
     - Tax Code: View

## Troubleshooting

### Authentication Issues

**Problem**: "INVALID_LOGIN_CREDENTIALS" error
- **Solution**: Verify consumer key/secret and token ID/secret are correct
- **Check**: Integration record enabled, token not deleted

**Problem**: "INVALID_SIGNATURE" error
- **Solution**: Check system clock synchronization (OAuth uses timestamp)
- **Check**: Verify credentials match integration record

### Sync Issues

**Problem**: Vendors not syncing
- **Solution**: Check RESTlet deployed and accessible
- **Check**: Verify script ID and deploy ID correct
- **Check**: User has vendor view permissions

**Problem**: Invoice export fails
- **Solution**: Validate vendor exists in NetSuite (check external_id)
- **Solution**: Verify all required fields provided (account, tax code)
- **Check**: User has vendor bill create permission

### Performance Issues

**Problem**: Sync takes too long
- **Solution**: Increase concurrent request limit (up to 10)
- **Solution**: Add filters to reduce data volume (status, date range)
- **Check**: RESTlet performance (optimize saved searches)

**Problem**: Rate limit exceeded
- **Solution**: Reduce sync frequency
- **Solution**: Decrease concurrent requests
- **Solution**: Optimize RESTlet queries

## Advanced Configuration

### Custom Fields

To sync custom fields from NetSuite:

1. **Update RESTlet**: Include custom fields in response JSON
2. **Update Connector**: Parse custom fields in `_parse_vendor()` or `_parse_purchase_order()`
3. **Store in SmartAP**: Use `custom_fields` JSONB column

Example:
```python
vendor.custom_fields = {
    'custentity_payment_method': vendor_data.get('custentity_payment_method'),
    'custentity_credit_limit': vendor_data.get('custentity_credit_limit')
}
```

### Field Mappings

Configure field mappings via `erp_field_mappings` table:

```sql
INSERT INTO erp_field_mappings (connection_id, entity_type, source_field, target_field, transformation)
VALUES (
    'connection-uuid',
    'vendor',
    'entityId',
    'name',
    NULL
);
```

### Webhook Integration

For real-time sync, configure NetSuite workflows to call SmartAP webhooks:

1. Create workflow in NetSuite (e.g., on vendor save)
2. Add action: Send HTTP request to SmartAP webhook
3. Configure SmartAP to process webhook and trigger sync

## References

- **NetSuite TBA Documentation**: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4389743623.html
- **SuiteScript 2.1 RESTlet**: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4618474877.html
- **NetSuite REST API**: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1558708800.html
- **OAuth 1.0a Specification**: https://oauth.net/core/1.0a/

## Support

For NetSuite connector issues:
1. Check application logs for detailed error messages
2. Review sync logs in ERP Sync Dashboard
3. Verify NetSuite configuration (TBA enabled, RESTlets deployed)
4. Test connection from SmartAP UI
5. Contact NetSuite support for account-specific issues
