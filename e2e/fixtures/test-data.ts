/**
 * E2E Test Fixtures and Helpers
 * Provides shared test data, authentication helpers, and common utilities
 */

export const TEST_USERS = {
  admin: {
    email: 'admin@smartap.test',
    password: 'TestAdmin123!',
    name: 'Admin User',
    role: 'admin',
  },
  approver: {
    email: 'approver@smartap.test',
    password: 'TestApprover123!',
    name: 'Approver User',
    role: 'approver',
  },
  viewer: {
    email: 'viewer@smartap.test',
    password: 'TestViewer123!',
    name: 'Viewer User',
    role: 'viewer',
  },
} as const;

export const TEST_INVOICES = {
  standard: {
    vendor: 'Acme Corporation',
    invoiceNumber: 'INV-2024-001',
    amount: 1500.00,
    currency: 'USD',
    dueDate: '2024-02-15',
  },
  highValue: {
    vendor: 'Tech Supplies Inc',
    invoiceNumber: 'INV-2024-002',
    amount: 50000.00,
    currency: 'USD',
    dueDate: '2024-02-20',
  },
  international: {
    vendor: 'Global Parts Ltd',
    invoiceNumber: 'INV-2024-003',
    amount: 2500.00,
    currency: 'EUR',
    dueDate: '2024-02-25',
  },
} as const;

export const TEST_VENDORS = {
  acme: {
    name: 'Acme Corporation',
    taxId: '12-3456789',
    address: '123 Business Ave, New York, NY 10001',
    contact: 'John Smith',
    email: 'invoices@acme.com',
  },
  techSupplies: {
    name: 'Tech Supplies Inc',
    taxId: '98-7654321',
    address: '456 Tech Blvd, San Francisco, CA 94105',
    contact: 'Jane Doe',
    email: 'billing@techsupplies.com',
  },
} as const;

export const TEST_PURCHASE_ORDERS = {
  standard: {
    poNumber: 'PO-2024-001',
    vendor: 'Acme Corporation',
    amount: 1500.00,
    status: 'open',
  },
  completed: {
    poNumber: 'PO-2024-002',
    vendor: 'Tech Supplies Inc',
    amount: 5000.00,
    status: 'completed',
  },
} as const;

/**
 * Selectors for common UI elements
 */
export const SELECTORS = {
  // Authentication
  auth: {
    emailInput: '[id="email"]',
    passwordInput: '[id="password"]',
    loginButton: 'button[type="submit"]',
    registerLink: 'a[href="/register"]',
    logoutButton: '[data-testid="logout-button"]',
  },
  
  // Navigation
  nav: {
    dashboard: 'a[href="/dashboard"]',
    invoices: 'a[href="/invoices"]',
    approvals: 'a[href="/approvals"]',
    vendors: 'a[href="/vendors"]',
    purchaseOrders: 'a[href="/purchase-orders"]',
    analytics: 'a[href="/analytics"]',
  },
  
  // Dashboard
  dashboard: {
    totalInvoices: '[data-testid="total-invoices"]',
    pendingApprovals: '[data-testid="pending-approvals"]',
    riskFlags: '[data-testid="risk-flags"]',
    stpRate: '[data-testid="stp-rate"]',
    recentActivity: '[data-testid="recent-activity"]',
  },
  
  // Invoice List
  invoices: {
    uploadButton: 'a[href="/invoices/upload"]',
    invoiceTable: 'table',
    invoiceRow: 'table tbody tr',
    statusFilter: '[data-testid="status-filter"]',
    vendorFilter: '[data-testid="vendor-filter"]',
    searchInput: '[data-testid="search-input"]',
    pagination: '[data-testid="pagination"]',
  },
  
  // Invoice Upload
  upload: {
    dropzone: '[data-testid="upload-dropzone"]',
    fileInput: 'input[type="file"]',
    uploadProgress: '[data-testid="upload-progress"]',
    uploadSuccess: '[data-testid="upload-success"]',
    uploadError: '[data-testid="upload-error"]',
  },
  
  // Invoice Detail
  invoiceDetail: {
    statusBadge: '[data-testid="status-badge"]',
    approveButton: '[data-testid="approve-button"]',
    rejectButton: '[data-testid="reject-button"]',
    editButton: '[data-testid="edit-button"]',
    deleteButton: '[data-testid="delete-button"]',
    approvalNotes: '[data-testid="approval-notes"]',
    rejectionReason: '[data-testid="rejection-reason"]',
    confirmApproval: '[data-testid="confirm-approval"]',
    confirmRejection: '[data-testid="confirm-rejection"]',
  },
  
  // Approvals
  approvals: {
    approvalQueue: '[data-testid="approval-queue"]',
    selectAll: '[data-testid="select-all"]',
    bulkApprove: '[data-testid="bulk-approve"]',
    bulkReject: '[data-testid="bulk-reject"]',
    invoiceCheckbox: '[data-testid="invoice-checkbox"]',
  },
  
  // Common
  common: {
    loadingSpinner: '[data-testid="loading"]',
    errorMessage: '[data-testid="error-message"]',
    successMessage: '[data-testid="success-message"]',
    confirmDialog: '[data-testid="confirm-dialog"]',
    cancelButton: '[data-testid="cancel-button"]',
    submitButton: '[data-testid="submit-button"]',
    toast: '[data-sonner-toast]',
  },
} as const;

/**
 * API endpoints for test setup/teardown
 */
export const API_ENDPOINTS = {
  auth: {
    login: '/api/v1/auth/login',
    logout: '/api/v1/auth/logout',
    register: '/api/v1/auth/register',
    me: '/api/v1/auth/me',
  },
  invoices: {
    list: '/api/v1/invoices',
    upload: '/api/v1/invoices/upload',
    detail: (id: string) => `/api/v1/invoices/${id}`,
    approve: (id: string) => `/api/v1/invoices/${id}/approve`,
    reject: (id: string) => `/api/v1/invoices/${id}/reject`,
  },
  vendors: {
    list: '/api/v1/vendors',
    detail: (id: string) => `/api/v1/vendors/${id}`,
  },
  purchaseOrders: {
    list: '/api/v1/purchase-orders',
    detail: (id: string) => `/api/v1/purchase-orders/${id}`,
  },
  dashboard: {
    metrics: '/api/v1/dashboard/metrics',
    activity: '/api/v1/dashboard/activity',
  },
} as const;

/**
 * Test file paths
 */
export const TEST_FILES = {
  sampleInvoicePdf: 'fixtures/sample-invoice.pdf',
  sampleInvoiceImage: 'fixtures/sample-invoice.png',
  invalidFile: 'fixtures/invalid-file.txt',
  largePdf: 'fixtures/large-invoice.pdf',
} as const;

/**
 * Wait times for various operations
 */
export const TIMEOUTS = {
  short: 1000,
  medium: 5000,
  long: 10000,
  upload: 30000,
  processing: 60000,
} as const;
