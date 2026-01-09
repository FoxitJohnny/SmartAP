# SmartAP - Phase 3 Implementation Plan
## Frontend Development & User Interface

**Phase:** 3 of 5  
**Duration:** 4 weeks (Weeks 9-12)  
**Status:** 📋 **PLANNED**  
**Prerequisites:** Phase 2 (Backend API & Agents) completed

---

## Overview

Phase 3 focuses on building a production-ready web application for SmartAP, providing finance teams with intuitive interfaces for invoice processing, validation, approval workflows, and system monitoring. The frontend will integrate Foxit Web SDK for PDF viewing and enable seamless human-in-the-loop operations.

### Core Objectives

1. **Professional Web Application**: Modern, responsive UI for finance teams
2. **PDF Viewer Integration**: Embedded Foxit Web SDK with visual validation
3. **Exception Handling**: Click-to-correct interface for AI uncertainties
4. **Approval Workflows**: Role-based approval UI with visual tracking
5. **Analytics Dashboard**: Real-time metrics and performance monitoring

---

## Sub-Phases & Tasks

### Phase 3.1: Project Setup & Infrastructure (Week 9, Days 1-5)

**Goal:** Establish frontend project structure with modern tooling

#### Tasks:

**3.1.1 - Initialize Next.js Project**
- [ ] Create Next.js 15+ project with App Router
- [ ] Configure TypeScript with strict mode
- [ ] Set up ESLint and Prettier
- [ ] Configure path aliases (@/components, @/lib, etc.)
- [ ] Set up environment variable management (.env.local)

**3.1.2 - Install Core Dependencies**
```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.3.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.50.0",
    "zod": "^3.22.0",
    "@hookform/resolvers": "^3.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

**3.1.3 - Configure UI Component Library**
- [ ] Install and configure shadcn/ui
- [ ] Set up Tailwind CSS with custom theme
- [ ] Create design tokens (colors, spacing, typography)
- [ ] Set up dark mode support

**3.1.4 - API Client Setup**
- [ ] Create Axios instance with interceptors
- [ ] Implement authentication token management
- [ ] Set up React Query for data fetching
- [ ] Create API client types from OpenAPI spec

**3.1.5 - Project Structure**
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # Auth layout group
│   │   ├── (dashboard)/       # Dashboard layout group
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── invoice/           # Invoice-specific components
│   │   ├── pdf-viewer/        # Foxit viewer wrapper
│   │   ├── approval/          # Approval workflow components
│   │   └── common/            # Shared components
│   ├── lib/
│   │   ├── api/               # API client
│   │   ├── hooks/             # Custom React hooks
│   │   ├── utils/             # Utility functions
│   │   └── types/             # TypeScript types
│   ├── stores/                # Zustand state stores
│   └── styles/                # Global styles
├── public/
│   ├── foxit-lib/             # Foxit Web SDK files
│   └── assets/
├── tests/
│   ├── components/
│   ├── integration/
│   └── e2e/
├── next.config.js
├── tailwind.config.js
└── package.json
```

**Deliverables:**
- ✅ Next.js project with TypeScript
- ✅ UI component library configured
- ✅ API client with authentication
- ✅ Project structure established

---

### Phase 3.2: Authentication & Layout (Week 9, Days 6-7 + Week 10, Days 1-2)

**Goal:** Implement user authentication and base application layout

#### Tasks:

**3.2.1 - Authentication Pages**
- [ ] Login page with form validation
- [ ] Registration page (if enabled)
- [ ] Password reset flow
- [ ] Session management with JWT
- [ ] Protected route middleware

**3.2.2 - Application Layout**
- [ ] Dashboard layout with sidebar navigation
- [ ] Top navigation bar with user menu
- [ ] Breadcrumb navigation
- [ ] Responsive mobile layout
- [ ] Loading states and error boundaries

**3.2.3 - Navigation Structure**
```typescript
// Navigation items
const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Invoices', href: '/invoices', icon: DocumentIcon },
  { name: 'Purchase Orders', href: '/purchase-orders', icon: ShoppingCartIcon },
  { name: 'Vendors', href: '/vendors', icon: BuildingOfficeIcon },
  { name: 'Approvals', href: '/approvals', icon: CheckCircleIcon },
  { name: 'Reports', href: '/reports', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
];
```

**3.2.4 - User Management**
- [ ] User profile component
- [ ] Role display (AP Clerk, Manager, Auditor)
- [ ] Logout functionality
- [ ] Session timeout handling

**Deliverables:**
- ✅ Authentication flow (login/logout)
- ✅ Protected routes
- ✅ Base application layout
- ✅ Responsive navigation

---

### Phase 3.3: Invoice Management UI (Week 10, Days 3-7)

**Goal:** Build core invoice listing, upload, and detail views

#### Tasks:

**3.3.1 - Invoice Upload Interface**
- [ ] Drag-and-drop file upload component
- [ ] File validation (PDF, size limits)
- [ ] Batch upload support (ZIP files)
- [ ] Upload progress indicators
- [ ] Success/error notifications

**3.3.2 - Invoice List View**
- [ ] Data table with sorting and filtering
- [ ] Status badges (Ingested, Extracted, Matched, etc.)
- [ ] Search functionality (invoice number, vendor, amount)
- [ ] Pagination with configurable page size
- [ ] Bulk actions (delete, export)

**3.3.3 - Invoice Detail View**
- [ ] Invoice header information display
- [ ] Line items table
- [ ] Status timeline visualization
- [ ] Matched PO information
- [ ] Risk assessment display
- [ ] Action buttons (approve, reject, request review)

**3.3.4 - Invoice Status Timeline**
```typescript
// Status timeline component
const statusSteps = [
  { status: 'INGESTED', label: 'Uploaded', icon: UploadIcon },
  { status: 'EXTRACTED', label: 'Data Extracted', icon: DocumentTextIcon },
  { status: 'MATCHED', label: 'PO Matched', icon: LinkIcon },
  { status: 'RISK_REVIEW', label: 'Risk Review', icon: ShieldCheckIcon },
  { status: 'APPROVED', label: 'Approved', icon: CheckCircleIcon },
  { status: 'READY_FOR_PAYMENT', label: 'Ready for Payment', icon: CreditCardIcon },
];
```

**3.3.5 - Invoice Filters**
- [ ] Status filter (multi-select)
- [ ] Date range picker
- [ ] Vendor filter (autocomplete)
- [ ] Amount range filter
- [ ] Risk level filter
- [ ] Save filter presets

**Deliverables:**
- ✅ Invoice upload interface
- ✅ Invoice list with filters
- ✅ Invoice detail view
- ✅ Status tracking visualization

---

### Phase 3.4: Foxit PDF Viewer Integration (Week 10, Day 7 + Week 11, Days 1-5)

**Goal:** Embed Foxit Web SDK for visual PDF validation

#### Tasks:

**3.4.1 - Foxit Web SDK Setup**
- [ ] Download and configure Foxit Web SDK
- [ ] Add SDK files to public directory
- [ ] Create React wrapper component for viewer
- [ ] Handle SDK initialization and cleanup
- [ ] Configure viewer permissions and features

**3.4.2 - PDF Viewer Component**
```typescript
// PDFViewer component structure
interface PDFViewerProps {
  documentUrl: string;
  extractedData?: ExtractedInvoiceData;
  onAnnotationCreate?: (annotation: Annotation) => void;
  onFieldCorrection?: (field: string, value: any) => void;
  readOnly?: boolean;
}

// Features:
// - Load PDF from URL
// - Display extracted field overlays
// - Highlight uncertain areas
// - Allow annotations and corrections
// - Support zoom, pan, rotate
```

**3.4.3 - Visual Validation Features**
- [ ] Overlay bounding boxes on extracted fields
- [ ] Color-code confidence levels (green, yellow, red)
- [ ] Click-to-edit field values directly on PDF
- [ ] Show tooltips with confidence scores
- [ ] Highlight risk flags on relevant areas

**3.4.4 - Field Correction Interface**
- [ ] Side panel with extracted data fields
- [ ] Compare original OCR vs. corrected values
- [ ] Validation errors and warnings
- [ ] Auto-save corrections
- [ ] Submit corrections API integration

**3.4.5 - PDF Annotation Tools**
- [ ] Sticky notes for reviewer comments
- [ ] Highlight tool for important areas
- [ ] Drawing tools for marking issues
- [ ] Annotation history and tracking
- [ ] Export annotations with invoice

**Deliverables:**
- ✅ Foxit Web SDK integrated
- ✅ PDF viewer with field overlays
- ✅ Click-to-correct functionality
- ✅ Annotation tools

---

### Phase 3.5: Approval Workflow UI (Week 11, Days 6-7 + Week 12, Days 1-3)

**Goal:** Build intuitive approval interfaces for finance teams

#### Tasks:

**3.5.1 - Approval Queue Dashboard**
- [ ] List of invoices pending approval
- [ ] Priority sorting (SLA, amount, risk level)
- [ ] Quick view cards with key details
- [ ] Bulk approval for low-risk items
- [ ] Assigned approver filtering

**3.5.2 - Approval Detail View**
- [ ] Invoice summary with PDF preview
- [ ] Matched PO comparison (side-by-side)
- [ ] Risk assessment display with explanations
- [ ] Vendor history and risk score
- [ ] Audit trail of previous actions

**3.5.3 - Approval Actions**
- [ ] Approve button with confirmation
- [ ] Reject with reason (dropdown + text)
- [ ] Request additional review (escalation)
- [ ] Add comments/notes
- [ ] eSign integration trigger (>$5K threshold)

**3.5.4 - Workflow Visualization**
```typescript
// Approval workflow display
interface ApprovalWorkflow {
  steps: [
    { role: 'AP_CLERK', status: 'COMPLETED', user: 'John Doe', timestamp: '...' },
    { role: 'MANAGER', status: 'PENDING', user: null, timestamp: null },
    { role: 'AUDITOR', status: 'NOT_REQUIRED', user: null, timestamp: null },
  ];
  currentStep: 1;
  escalationRules: { amount: 5000, requiresAuditor: true };
}
```

**3.5.5 - Role-Based Access Control**
- [ ] Show/hide actions based on user role
- [ ] AP Clerk: View, comment, recommend
- [ ] Manager: Approve, reject, escalate
- [ ] Auditor: Review, flag, require changes
- [ ] Admin: Override, delete, configure

**Deliverables:**
- ✅ Approval queue interface
- ✅ Approval detail view
- ✅ Role-based approval actions
- ✅ Workflow tracking

---

### Phase 3.6: Dashboard & Analytics (Week 12, Days 4-7)

**Goal:** Provide real-time insights and performance metrics

#### Tasks:

**3.6.1 - Dashboard Overview**
- [ ] Key metrics cards (invoices processed, STP rate, pending approvals)
- [ ] Recent activity feed
- [ ] Quick action buttons
- [ ] Alert notifications (high-risk, overdue)

**3.6.2 - Performance Metrics**
```typescript
// Dashboard metrics
const metrics = {
  totalInvoices: { value: 1234, change: +12.5 },
  stpRate: { value: 87.2, change: +3.1 },
  avgProcessingTime: { value: '4.2s', change: -0.8 },
  pendingApprovals: { value: 42, change: -5 },
  riskFlags: { value: 7, change: +2 },
  totalValue: { value: '$245,678', change: +8.3 },
};
```

**3.6.3 - Charts & Visualizations**
- [ ] Invoice volume over time (line chart)
- [ ] Status distribution (donut chart)
- [ ] Processing time trends (area chart)
- [ ] Risk level distribution (bar chart)
- [ ] Top vendors by volume (horizontal bar)
- [ ] STP rate by week (trend line)

**3.6.4 - Reports Page**
- [ ] Report templates (daily, weekly, monthly)
- [ ] Custom report builder
- [ ] Export options (PDF, Excel, CSV)
- [ ] Scheduled report configuration
- [ ] Audit log viewer

**3.6.5 - Real-Time Updates**
- [ ] WebSocket connection for live updates
- [ ] Toast notifications for status changes
- [ ] Auto-refresh dashboard data
- [ ] Live processing status indicators

**Deliverables:**
- ✅ Dashboard with key metrics
- ✅ Interactive charts
- ✅ Reports page
- ✅ Real-time updates

---

### Phase 3.7: Purchase Order & Vendor Management (Week 12, Day 7 + Buffer Time)

**Goal:** Build supporting interfaces for PO and vendor data

#### Tasks:

**3.7.1 - Purchase Order List**
- [ ] PO listing table with search/filter
- [ ] Status indicators (open, partially matched, closed)
- [ ] Matched invoices count
- [ ] Create/edit PO form
- [ ] Import PO from ERP

**3.7.2 - Purchase Order Detail**
- [ ] PO header and line items
- [ ] Linked invoices display
- [ ] Matching history
- [ ] Edit capabilities
- [ ] Close/cancel PO action

**3.7.3 - Vendor Management**
- [ ] Vendor list with search
- [ ] Vendor detail page
- [ ] Risk score display and history
- [ ] Invoice history by vendor
- [ ] Vendor performance metrics
- [ ] Add/edit vendor form

**3.7.4 - Vendor Risk Dashboard**
- [ ] Risk score breakdown
- [ ] Historical risk events
- [ ] Duplicate invoice attempts
- [ ] Price variance trends
- [ ] Payment history

**Deliverables:**
- ✅ PO management interface
- ✅ Vendor management interface
- ✅ Risk scoring display

---

## Technical Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 15+ | React framework with App Router |
| **React** | 18.3+ | UI library |
| **TypeScript** | 5.3+ | Type safety |
| **Tailwind CSS** | 3.4+ | Utility-first CSS |
| **shadcn/ui** | Latest | Component library |
| **Foxit Web SDK** | Latest | PDF viewer and annotation |

### State Management & Data Fetching

| Library | Purpose |
|---------|---------|
| **Zustand** | Global state management |
| **React Query** | Server state and caching |
| **React Hook Form** | Form state management |
| **Zod** | Schema validation |

### UI Components

| Component | Library/Approach |
|-----------|------------------|
| **Tables** | TanStack Table v8 |
| **Charts** | Recharts or Chart.js |
| **Date Picker** | react-day-picker |
| **File Upload** | react-dropzone |
| **Notifications** | sonner (toast) |
| **Modals** | Radix UI Dialog |

### Development Tools

| Tool | Purpose |
|------|---------|
| **ESLint** | Code linting |
| **Prettier** | Code formatting |
| **Vitest** | Unit testing |
| **Playwright** | E2E testing |
| **Storybook** | Component documentation |

---

## API Integration

### Backend Endpoints

**Authentication:**
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh token

**Invoices:**
- `GET /api/v1/invoices` - List invoices
- `POST /api/v1/invoices/upload` - Upload invoice
- `GET /api/v1/invoices/{id}` - Get invoice details
- `PATCH /api/v1/invoices/{id}` - Update invoice
- `DELETE /api/v1/invoices/{id}` - Delete invoice
- `POST /api/v1/invoices/{id}/approve` - Approve invoice
- `POST /api/v1/invoices/{id}/reject` - Reject invoice

**Purchase Orders:**
- `GET /api/v1/purchase-orders` - List POs
- `POST /api/v1/purchase-orders` - Create PO
- `GET /api/v1/purchase-orders/{id}` - Get PO details
- `PATCH /api/v1/purchase-orders/{id}` - Update PO

**Vendors:**
- `GET /api/v1/vendors` - List vendors
- `POST /api/v1/vendors` - Create vendor
- `GET /api/v1/vendors/{id}` - Get vendor details
- `GET /api/v1/vendors/{id}/risk-history` - Vendor risk data

**Analytics:**
- `GET /api/v1/analytics/dashboard` - Dashboard metrics
- `GET /api/v1/analytics/reports` - Generate reports

---

## Component Architecture

### Key Components

**1. InvoiceUploadZone**
```typescript
interface InvoiceUploadZoneProps {
  onUploadComplete: (invoices: Invoice[]) => void;
  onUploadError: (error: Error) => void;
  acceptedFileTypes?: string[];
  maxFileSize?: number;
  allowBatch?: boolean;
}
```

**2. InvoiceDataTable**
```typescript
interface InvoiceDataTableProps {
  invoices: Invoice[];
  onRowClick: (invoice: Invoice) => void;
  onBulkAction: (action: string, invoiceIds: string[]) => void;
  filters: InvoiceFilters;
  onFilterChange: (filters: InvoiceFilters) => void;
}
```

**3. PDFViewerWithValidation**
```typescript
interface PDFViewerWithValidationProps {
  documentUrl: string;
  extractedData: ExtractedInvoiceData;
  onFieldCorrection: (field: string, value: any) => Promise<void>;
  readOnly: boolean;
  highlightUncertain?: boolean;
}
```

**4. ApprovalWorkflowCard**
```typescript
interface ApprovalWorkflowCardProps {
  invoice: Invoice;
  currentUserRole: UserRole;
  onApprove: (invoiceId: string, comment?: string) => Promise<void>;
  onReject: (invoiceId: string, reason: string) => Promise<void>;
  onEscalate: (invoiceId: string, toRole: UserRole) => Promise<void>;
}
```

**5. DashboardMetricCard**
```typescript
interface DashboardMetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  onClick?: () => void;
}
```

---

## Responsive Design

### Breakpoints

```typescript
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px' // Extra large
};
```

### Mobile-First Approach

- Stack layout on mobile (<768px)
- Side-by-side on tablet (768px-1024px)
- Full desktop layout (>1024px)
- Touch-friendly buttons and inputs
- Swipe gestures for mobile navigation

---

## Testing Strategy

### Unit Tests
- Component rendering tests
- Form validation tests
- Utility function tests
- Custom hook tests
- 80%+ code coverage target

### Integration Tests
- API client integration
- Form submission flows
- Navigation and routing
- State management

### E2E Tests (Playwright)
```typescript
// Key user flows to test
const e2eFlows = [
  'User login and dashboard access',
  'Upload invoice and view extraction',
  'Correct extracted data on PDF',
  'Approve invoice workflow',
  'Search and filter invoices',
  'View reports and analytics',
];
```

---

## Performance Optimization

### Bundle Size Optimization
- Code splitting with Next.js dynamic imports
- Tree shaking unused code
- Optimize image assets
- Lazy load heavy components (PDF viewer)
- Target: <200KB initial bundle

### Runtime Performance
- Virtualize long lists (react-window)
- Debounce search inputs
- Optimize re-renders with React.memo
- Use Web Workers for heavy computations
- Target: <100ms interaction response

### Caching Strategy
- React Query caching for API data
- Service Worker for offline support
- Static asset caching (images, fonts)
- Optimistic UI updates

---

## Accessibility (a11y)

### WCAG 2.1 AA Compliance

- [ ] Semantic HTML elements
- [ ] ARIA labels and roles
- [ ] Keyboard navigation support
- [ ] Focus management
- [ ] Color contrast ratios (4.5:1 minimum)
- [ ] Screen reader compatibility
- [ ] Alt text for images
- [ ] Form error announcements

---

## Security Considerations

### Frontend Security

- [ ] XSS prevention (React built-in)
- [ ] CSRF token handling
- [ ] Secure token storage (httpOnly cookies)
- [ ] Input sanitization
- [ ] Content Security Policy (CSP)
- [ ] No sensitive data in localStorage
- [ ] HTTPS enforcement
- [ ] Rate limiting on actions

---

## Deployment

### Build Configuration

```javascript
// next.config.js
module.exports = {
  output: 'standalone',
  images: {
    domains: ['your-api-domain.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_FOXIT_LICENSE_KEY: process.env.NEXT_PUBLIC_FOXIT_LICENSE_KEY,
  },
};
```

### Docker Deployment

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### Environment Variables

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.smartap.company.com
NEXT_PUBLIC_FOXIT_LICENSE_KEY=your-foxit-license-key
NEXT_PUBLIC_APP_NAME=SmartAP
NEXT_PUBLIC_APP_VERSION=1.0.0
```

---

## Deliverables Checklist

### Week 9 (Project Setup)
- [ ] Next.js project initialized
- [ ] UI component library configured
- [ ] API client setup
- [ ] Authentication flow
- [ ] Base layout and navigation

### Week 10 (Core Features)
- [ ] Invoice upload interface
- [ ] Invoice list and filters
- [ ] Invoice detail view
- [ ] Foxit PDF viewer integration
- [ ] Field correction interface

### Week 11 (Approval Workflow)
- [ ] PDF visual validation features
- [ ] Approval queue dashboard
- [ ] Approval detail view
- [ ] Role-based approval actions
- [ ] Workflow tracking

### Week 12 (Analytics & Polish)
- [ ] Dashboard with metrics
- [ ] Charts and visualizations
- [ ] Reports page
- [ ] PO management UI
- [ ] Vendor management UI
- [ ] Real-time updates
- [ ] Final testing and bug fixes

---

## Success Metrics

### Functional Metrics

| Metric | Target |
|--------|--------|
| **Page Load Time** | <2 seconds |
| **Time to Interactive** | <3 seconds |
| **Bundle Size** | <200KB (initial) |
| **Lighthouse Score** | >90 (all categories) |
| **Test Coverage** | >80% |

### User Experience Metrics

| Metric | Target |
|--------|--------|
| **Invoice Upload Success Rate** | >99% |
| **Time to Correct Field** | <30 seconds |
| **Approval Action Time** | <1 minute |
| **Search Response Time** | <500ms |
| **Mobile Usability Score** | >85 |

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **Foxit SDK Integration Issues** | Test SDK early, have fallback PDF viewer |
| **Performance with Large PDFs** | Implement pagination, optimize rendering |
| **Browser Compatibility** | Test on Chrome, Firefox, Safari, Edge |
| **API Response Times** | Implement loading states, optimistic updates |

### Timeline Risks

| Risk | Mitigation |
|------|------------|
| **Foxit SDK Learning Curve** | Allocate extra time in Week 11 |
| **Scope Creep** | Lock features by Week 9 end |
| **Backend API Delays** | Mock API during development |
| **Design Iterations** | Finalize designs before Phase 3.3 |

---

## Documentation Requirements

### Developer Documentation

- [ ] Component API documentation
- [ ] Custom hooks documentation
- [ ] API client usage guide
- [ ] Deployment guide
- [ ] Contributing guidelines

### User Documentation

- [ ] User manual (admin, AP clerk, manager)
- [ ] Video tutorials
- [ ] FAQ section
- [ ] Troubleshooting guide

---

## Post-Phase 3 Handoff

### Deliverables to Phase 4

- ✅ Fully functional frontend application
- ✅ Integrated with Phase 2 backend APIs
- ✅ Foxit PDF viewer operational
- ✅ All core user flows tested
- ✅ Responsive design implemented
- ✅ Deployed to staging environment

### Ready for Phase 4 Integration

- eSign integration (Foxit eSign API)
- ERP connectors (QuickBooks, Xero, SAP)
- Payment system integration
- Email ingestion frontend monitoring

---

## Appendix A: Wireframe Concepts

### Invoice List View
```
┌─────────────────────────────────────────────────────────────┐
│ SmartAP          [Dashboard] [Invoices] [Approvals] [User▼]│
├─────────────────────────────────────────────────────────────┤
│ Invoices                                    [+ Upload Invoice]│
├─────────────────────────────────────────────────────────────┤
│ [Search...] [Filter: Status▼] [Date Range▼] [Export]       │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Invoice #  │ Vendor       │ Amount    │ Status  │ Date  │ │
│ ├────────────┼──────────────┼───────────┼─────────┼───────┤ │
│ │ INV-001    │ Acme Corp    │ $1,245.00 │ ●Matched│ 1/5   │ │
│ │ INV-002    │ Tech Suppliers│ $3,780.50 │ ⚠Review │ 1/5   │ │
│ │ INV-003    │ Office Plus  │ $524.75   │ ✓Approved│1/4   │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [< Previous] Page 1 of 45 [Next >]                          │
└─────────────────────────────────────────────────────────────┘
```

### Invoice Detail View with PDF
```
┌─────────────────────────────────────────────────────────────┐
│ Invoice INV-002 - Tech Suppliers          [Approve] [Reject]│
├──────────────────────────┬──────────────────────────────────┤
│ ┌──────────────────────┐ │ Invoice Details                  │
│ │                      │ │ ──────────────                   │
│ │     PDF VIEWER       │ │ Invoice #: INV-002               │
│ │                      │ │ Vendor: Tech Suppliers           │
│ │   [Foxit Web SDK]    │ │ Date: 2026-01-05                 │
│ │                      │ │ Amount: $3,780.50                │
│ │  (with field         │ │ Status: 🟡 Risk Review           │
│ │   overlays)          │ │ ──────────────                   │
│ │                      │ │ Matched PO: PO-456               │
│ │                      │ │ Match Score: 95%                 │
│ │                      │ │ ──────────────                   │
│ │                      │ │ Risk Flags:                      │
│ │                      │ │ ⚠ Price variance: +5.2%          │
│ │                      │ │ ──────────────                   │
│ └──────────────────────┘ │ Line Items:                      │
│                          │ 1. Widget A - $2,500             │
│                          │ 2. Service B - $1,280.50         │
└──────────────────────────┴──────────────────────────────────┘
```

---

## Appendix B: State Management Design

### Zustand Stores

```typescript
// authStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

// invoiceStore.ts
interface InvoiceState {
  invoices: Invoice[];
  selectedInvoice: Invoice | null;
  filters: InvoiceFilters;
  setFilters: (filters: InvoiceFilters) => void;
  selectInvoice: (id: string) => void;
}

// uiStore.ts
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  notifications: Notification[];
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addNotification: (notification: Notification) => void;
}
```

---

**Document Version:** 1.0  
**Last Updated:** January 7, 2026  
**Status:** Ready for Implementation  
**Estimated Effort:** 4 weeks (160 hours)

---

*This plan provides a comprehensive roadmap for Phase 3 frontend development, ensuring all user-facing features are implemented with modern best practices and integrated seamlessly with the Phase 2 backend.*
