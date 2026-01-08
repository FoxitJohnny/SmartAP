# Contributing to SmartAP

Thank you for your interest in contributing to SmartAP! 🎉

SmartAP is an open-source accounts payable automation platform, and we welcome contributions from developers, designers, technical writers, and finance professionals. Whether you're fixing bugs, adding features, improving documentation, or sharing ideas, your help makes SmartAP better for everyone.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Getting Started](#getting-started)
4. [Development Workflow](#development-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Community](#community)

---

## Code of Conduct

SmartAP has adopted the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@smartap.example.com](mailto:conduct@smartap.example.com).

**In short:**
- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards others

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Found a bug? Help us fix it!

1. **Check existing issues** to see if it's already reported
2. **Create a new issue** using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
3. **Provide details:**
   - Steps to reproduce
   - Expected vs. actual behavior
   - Screenshots (if applicable)
   - Environment (OS, Docker version, SmartAP version)
   - Logs (from `docker-compose logs`)

### 💡 Suggesting Features

Have an idea for a new feature?

1. **Check existing issues** and discussions
2. **Create a new issue** using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
3. **Describe:**
   - The problem you're trying to solve
   - Your proposed solution
   - Alternatives you've considered
   - Benefits for other users

### 📝 Improving Documentation

Documentation is crucial for community adoption!

- Fix typos, grammar, or unclear instructions
- Add examples or tutorials
- Translate docs to other languages
- Create video tutorials or blog posts

### 🔌 Building Custom Agents

Share your custom agents with the community!

- Create agents for specific use cases (e.g., carbon footprint, currency conversion)
- Document your agent's purpose and usage
- Add tests for your agent
- Submit a PR to add it to the `plugins/` directory

### 🔗 Adding ERP Integrations

Help us support more ERP systems!

Currently supported: QuickBooks, Xero, SAP, NetSuite

Missing integrations we'd love to see:
- Microsoft Dynamics 365
- Oracle NetSuite (advanced features)
- Sage Intacct
- Workday Financials
- Odoo

### 🎨 Improving the UI

Enhance the user experience:

- Fix UI bugs or inconsistencies
- Improve accessibility (WCAG compliance)
- Add new dashboards or visualizations
- Mobile responsiveness improvements

---

## Getting Started

### Prerequisites

- **Git** 2.40+
- **Docker** 24.0+ and **Docker Compose** 2.20+
- **Python** 3.12+ (for backend development)
- **Node.js** 18+ (for frontend development)
- **Foxit API Key** ([free trial](https://developers.foxit.com/))
- **AI API Key** (GitHub Models, OpenAI, or Anthropic)

### Fork and Clone

1. **Fork the repository** on GitHub (click "Fork" button)
2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/smartap.git
   cd smartap
   ```
3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/yourusername/smartap.git
   ```

### Environment Setup

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure `.env` with your API keys** (see [Quick Start Guide](docs/Quick_Start_Guide.md))

3. **Start development environment:**
   ```bash
   docker-compose up -d
   ```

### Verify Setup

```bash
# Check all containers are running
docker-compose ps

# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm test

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Branch naming conventions:
# - feature/add-carbon-footprint-agent
# - fix/invoice-upload-bug
# - docs/improve-quick-start-guide
# - refactor/simplify-matching-logic
```

### 2. Make Your Changes

**Backend (Python/FastAPI):**
```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Make changes to Python files
# Run tests frequently
pytest

# Format code
black .
flake8 .
```

**Frontend (TypeScript/Next.js):**
```bash
# Install dependencies
cd frontend
npm install

# Make changes to TypeScript/React files
# Run dev server
npm run dev

# Format code
npm run format
npm run lint
```

### 3. Write Tests

**Backend tests** (`backend/tests/`):
```python
# tests/test_invoice_service.py
import pytest
from src.services.invoice_service import InvoiceService

def test_create_invoice():
    """Test invoice creation."""
    service = InvoiceService()
    invoice = service.create_invoice({
        "invoice_number": "INV-001",
        "vendor_name": "Acme Corp",
        "total": 1000.00
    })
    assert invoice.invoice_number == "INV-001"
    assert invoice.total == 1000.00
```

**Frontend tests** (`frontend/__tests__/`):
```typescript
// __tests__/InvoiceUpload.test.tsx
import { render, screen } from '@testing-library/react';
import InvoiceUpload from '@/components/InvoiceUpload';

test('renders upload button', () => {
  render(<InvoiceUpload />);
  const uploadButton = screen.getByText(/upload invoice/i);
  expect(uploadButton).toBeInTheDocument();
});
```

### 4. Run Tests

```bash
# Backend tests (in backend/ directory)
pytest                     # Run all tests
pytest tests/test_file.py  # Run specific test file
pytest -v --cov            # Run with coverage report

# Frontend tests (in frontend/ directory)
npm test                   # Run all tests
npm test -- --coverage     # Run with coverage report
```

**Coverage requirements:**
- Backend: ≥80% code coverage
- Frontend: ≥70% code coverage

### 5. Commit Your Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
# Format:
# <type>(<scope>): <subject>
#
# Types: feat, fix, docs, style, refactor, test, chore
# Scope: Optional (e.g., backend, frontend, agents, docs)
# Subject: Imperative, lowercase, no period

git add .
git commit -m "feat(agents): add carbon footprint calculator agent"
git commit -m "fix(backend): resolve invoice upload timeout issue"
git commit -m "docs(quick-start): add troubleshooting section"
```

**Good commit messages:**
```
feat(backend): add NetSuite ERP integration
fix(frontend): fix invoice date picker timezone bug
docs(api): add examples for /invoices POST endpoint
refactor(agents): simplify fraud detection logic
test(backend): add tests for PO matching service
chore(deps): upgrade FastAPI to 0.110.0
```

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Open a Pull Request

1. Navigate to your fork on GitHub
2. Click "Compare & pull request"
3. Fill out the PR template (see below)
4. Submit PR

---

## Coding Standards

### Python (Backend)

**Style Guide:** [PEP 8](https://pep8.org/)

**Tools:**
- **Formatter:** [Black](https://black.readthedocs.io/) (line length: 100)
- **Linter:** [Flake8](https://flake8.pycqa.org/)
- **Type Checker:** [mypy](https://mypy.readthedocs.io/)

**Configuration** (`.flake8`):
```ini
[flake8]
max-line-length = 100
exclude = venv,.git,__pycache__
```

**Best Practices:**
- Use type hints for all function signatures
- Write docstrings for all public functions/classes (Google style)
- Use async/await for I/O operations
- Prefer dependency injection over global state

**Example:**
```python
from typing import Optional, List
from pydantic import BaseModel

class InvoiceService:
    """Service for managing invoices."""
    
    def __init__(self, db_session):
        """Initialize invoice service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
    
    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Retrieve invoice by ID.
        
        Args:
            invoice_id: Unique invoice identifier
            
        Returns:
            Invoice object if found, None otherwise
        """
        return await self.db_session.get(Invoice, invoice_id)
```

### TypeScript (Frontend)

**Style Guide:** [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) + [TypeScript ESLint](https://typescript-eslint.io/)

**Tools:**
- **Formatter:** [Prettier](https://prettier.io/)
- **Linter:** [ESLint](https://eslint.org/)

**Configuration** (`.prettierrc`):
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

**Best Practices:**
- Use functional components with hooks
- Prefer TypeScript interfaces over types
- Use React Query for server state
- Avoid prop drilling (use Context API or state management)

**Example:**
```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchInvoice } from '@/api/invoices';

interface InvoiceDetailProps {
  invoiceId: number;
}

const InvoiceDetail: React.FC<InvoiceDetailProps> = ({ invoiceId }) => {
  const { data: invoice, isLoading, error } = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => fetchInvoice(invoiceId),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>Invoice {invoice?.invoice_number}</h1>
      <p>Total: ${invoice?.total}</p>
    </div>
  );
};

export default InvoiceDetail;
```

---

## Testing Guidelines

### Backend Testing

**Framework:** pytest

**Test structure:**
```
backend/tests/
├── conftest.py           # Pytest fixtures
├── test_services/        # Service layer tests
├── test_agents/          # Agent tests
├── test_api/             # API endpoint tests
└── test_models/          # Database model tests
```

**Example test:**
```python
# tests/test_agents/test_extractor_agent.py
import pytest
from src.agents.extractor_agent import ExtractorAgent

@pytest.fixture
def sample_invoice_text():
    return """
    INVOICE
    Invoice #: INV-12345
    Date: 2026-01-08
    Total: $1,250.00
    """

async def test_extractor_agent(sample_invoice_text):
    """Test invoice data extraction."""
    agent = ExtractorAgent()
    result = await agent.extract(sample_invoice_text)
    
    assert result["invoice_number"] == "INV-12345"
    assert result["invoice_date"] == "2026-01-08"
    assert result["total"] == 1250.00
```

**Run tests:**
```bash
pytest                          # Run all tests
pytest tests/test_agents/       # Run specific directory
pytest -v                       # Verbose output
pytest --cov --cov-report=html  # Generate HTML coverage report
```

### Frontend Testing

**Frameworks:** Jest + React Testing Library

**Test structure:**
```
frontend/__tests__/
├── components/          # Component tests
├── hooks/               # Custom hook tests
├── utils/               # Utility function tests
└── integration/         # Integration tests
```

**Example test:**
```typescript
// __tests__/components/InvoiceUpload.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import InvoiceUpload from '@/components/InvoiceUpload';

describe('InvoiceUpload', () => {
  it('allows file selection', () => {
    render(<InvoiceUpload />);
    
    const fileInput = screen.getByLabelText(/choose file/i);
    const file = new File(['invoice content'], 'invoice.pdf', { type: 'application/pdf' });
    
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    expect(screen.getByText('invoice.pdf')).toBeInTheDocument();
  });
});
```

**Run tests:**
```bash
npm test                 # Run all tests
npm test -- --coverage   # Generate coverage report
npm test -- --watch      # Watch mode for development
```

---

## Documentation

### Code Documentation

**Python (Docstrings):**
```python
def calculate_total(line_items: List[LineItem]) -> Decimal:
    """Calculate invoice total from line items.
    
    Args:
        line_items: List of invoice line items
        
    Returns:
        Total amount as Decimal
        
    Raises:
        ValueError: If line_items is empty
        
    Example:
        >>> items = [LineItem(amount=100), LineItem(amount=200)]
        >>> calculate_total(items)
        Decimal('300.00')
    """
    if not line_items:
        raise ValueError("Line items cannot be empty")
    return sum(item.amount for item in line_items)
```

**TypeScript (JSDoc):**
```typescript
/**
 * Fetch invoice by ID from the API
 * @param invoiceId - Unique invoice identifier
 * @returns Promise resolving to Invoice object
 * @throws {Error} If invoice not found or API error
 */
export async function fetchInvoice(invoiceId: number): Promise<Invoice> {
  const response = await fetch(`/api/invoices/${invoiceId}`);
  if (!response.ok) throw new Error('Invoice not found');
  return response.json();
}
```

### User-Facing Documentation

Located in `docs/` directory:

- Update existing docs when changing features
- Add new docs for new features
- Include code examples and screenshots
- Test instructions step-by-step

### API Documentation

Backend uses FastAPI automatic docs:

- Add descriptions to endpoints:
  ```python
  @router.post("/invoices", response_model=InvoiceResponse)
  async def create_invoice(
      invoice: InvoiceCreate,
      db: Session = Depends(get_db)
  ):
      """
      Create a new invoice.
      
      - **invoice_number**: Unique invoice identifier
      - **vendor_name**: Name of the vendor
      - **total**: Invoice total amount
      """
      return await invoice_service.create(invoice, db)
  ```

- View docs at: `http://localhost:8000/docs`

---

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] Tests pass locally (`pytest` and `npm test`)
- [ ] Code follows style guidelines (Black, Flake8, Prettier, ESLint)
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] Commit messages follow Conventional Commits
- [ ] No merge conflicts with `main` branch

### PR Template

Fill out the [Pull Request template](.github/PULL_REQUEST_TEMPLATE.md):

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to break)
- [ ] Documentation update

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated checks** run on your PR:
   - Unit tests (backend + frontend)
   - Linting (Flake8, ESLint)
   - Coverage checks (≥80% backend, ≥70% frontend)
   - Build checks (Docker images)

2. **Code review** by maintainers:
   - Usually within 2-3 business days
   - Feedback provided as comments
   - Address comments and push updates

3. **Approval:**
   - At least 1 maintainer approval required
   - All CI checks must pass
   - No merge conflicts

4. **Merge:**
   - Maintainer merges PR via squash merge
   - Your contribution goes live! 🎉

---

## Community

### Communication Channels

- **GitHub Discussions:** [Ask questions, share ideas](https://github.com/yourusername/smartap/discussions)
- **Discord:** [Join our server](https://discord.gg/smartap) (coming soon)
- **Twitter:** [@smartap_ai](https://twitter.com/smartap_ai)
- **Email:** developers@smartap.example.com

### Getting Help

- **Documentation:** [docs.smartap.example.com](https://docs.smartap.example.com)
- **Quick Start:** [docs/Quick_Start_Guide.md](docs/Quick_Start_Guide.md)
- **Troubleshooting:** [docs/Troubleshooting.md](docs/Troubleshooting.md)
- **GitHub Issues:** [Report bugs or ask questions](https://github.com/yourusername/smartap/issues)

### Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md) file
- Release notes
- Social media shoutouts
- Monthly contributor highlights

---

## License

By contributing to SmartAP, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

**Thank you for contributing to SmartAP!** 🙏

Your efforts help make AP automation accessible to everyone. Together, we're building something amazing!

---

**Questions about contributing?**

Email: developers@smartap.example.com
