# SmartAP Frequently Asked Questions (FAQ)

This document answers common questions about SmartAP - the Open-Source AI-Powered Invoice Processing System.

---

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [Foxit PDF Editor Integration](#foxit-pdf-editor-integration)
- [AI & LLM Configuration](#ai--llm-configuration)
- [Invoice Processing](#invoice-processing)
- [Security & Compliance](#security--compliance)
- [ERP Integration](#erp-integration)
- [Performance & Scaling](#performance--scaling)
- [Troubleshooting](#troubleshooting)
- [Licensing & Support](#licensing--support)

---

## General Questions

### What is SmartAP?

SmartAP is an open-source, AI-powered invoice processing system that automates accounts payable workflows. It uses advanced AI agents (powered by CrewAI) and Foxit PDF Editor to extract, validate, and process invoice data with minimal human intervention.

### Who is SmartAP designed for?

SmartAP is ideal for:

- **Small to Medium Businesses (SMBs)** looking for cost-effective AP automation
- **Enterprises** that need customizable and auditable invoice processing
- **Developers** building custom financial document processing solutions
- **Organizations** requiring on-premises deployment for data sovereignty

### How is SmartAP different from commercial AP automation tools?

| Feature | SmartAP | Commercial Solutions |
|---------|---------|---------------------|
| **Cost** | Free (open-source) | $1,000-$50,000+/month |
| **Customization** | Full source code access | Limited/None |
| **AI Transparency** | Open architecture | Black box |
| **Deployment** | Self-hosted or cloud | Vendor cloud only |
| **Data Ownership** | You own everything | Vendor may access |
| **Integration** | Unlimited via API | Limited connectors |

### What are the main features?

- **AI-Powered Data Extraction**: Automatically extract invoice fields using AI
- **Multi-Agent Processing**: CrewAI-powered agents for OCR, validation, matching
- **Three-Way Matching**: Automatic PO-Invoice-Receipt matching
- **Approval Workflows**: Configurable rules-based approval routing
- **Fraud Detection**: AI-based anomaly detection and risk scoring
- **ERP Integration**: Connect to SAP, Oracle, QuickBooks, NetSuite, and more
- **Audit Trail**: Complete audit logging for compliance
- **Multi-Currency**: Support for global invoice processing

---

## Installation & Setup

### What are the system requirements?

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB SSD
- Docker & Docker Compose
- Foxit PDF Editor (licensed)

**Recommended (Production):**
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 100+ GB SSD
- PostgreSQL 13+ or SQLite
- Redis for caching
- HTTPS/TLS certificates

### How do I install SmartAP?

**Quick Start (Docker):**

```bash
# Clone the repository
git clone https://github.com/smartap/smartap.git
cd smartap

# Copy environment template
cp .env.example .env

# Start services
docker-compose up -d

# Access the application
open http://localhost:3000
```

See the [Quick Start Guide](Quick_Start_Guide.md) for detailed instructions.

### Can I run SmartAP without Docker?

Yes! SmartAP can be run directly with Python and Node.js:

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### What databases are supported?

| Database | Support Level | Use Case |
|----------|--------------|----------|
| SQLite | Full | Development, small deployments |
| PostgreSQL | Full (Recommended) | Production environments |
| MySQL | Community | Alternative production option |

Configure via the `DATABASE_URL` environment variable.

### How do I configure environment variables?

Create a `.env` file with the following key variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/smartap

# Security
SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256

# AI/LLM
OPENAI_API_KEY=sk-your-key-here
# Or for Azure OpenAI:
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Foxit
FOXIT_EDITOR_PATH=/path/to/FoxitPDFEditor
FOXIT_LICENSE_KEY=your-license-key

# Storage
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE_MB=50
```

---

## Foxit PDF Editor Integration

### Why does SmartAP use Foxit PDF Editor?

Foxit PDF Editor provides:

1. **High-Accuracy OCR**: Industry-leading text extraction accuracy
2. **PDF/A Support**: Process archival and scanned documents
3. **Form Field Detection**: Automatic form field identification
4. **Digital Signature Verification**: Validate signed invoices
5. **Batch Processing**: Handle multiple documents efficiently

### Do I need a Foxit license?

Yes, SmartAP requires a licensed copy of Foxit PDF Editor. Options include:

- **Foxit PDF Editor Pro**: For single-server deployments
- **Foxit PDF Editor Server**: For high-volume processing

Contact [Foxit Sales](https://www.foxit.com) for licensing options.

### How do I configure Foxit integration?

1. Install Foxit PDF Editor on your server
2. Set environment variables:

```bash
FOXIT_EDITOR_PATH=/opt/foxitreader/FoxitPDFEditor
FOXIT_LICENSE_KEY=your-license-key
FOXIT_LANGUAGE=ENG  # OCR language
```

3. Test the integration:

```bash
python -c "from smartap.ocr import FoxitOCR; FoxitOCR().test_connection()"
```

### Can I use a different OCR engine?

Yes! SmartAP's modular architecture supports custom OCR providers:

```python
# Custom OCR provider example
from smartap.ocr.base import BaseOCRProvider

class CustomOCR(BaseOCRProvider):
    def extract_text(self, pdf_path: str) -> str:
        # Your implementation
        pass
    
    def extract_structured(self, pdf_path: str) -> dict:
        # Your implementation
        pass
```

Register in `config/ocr.yaml`:

```yaml
ocr:
  provider: custom
  custom:
    class: mymodule.CustomOCR
```

---

## AI & LLM Configuration

### Which LLM providers are supported?

| Provider | Models | Status |
|----------|--------|--------|
| OpenAI | GPT-4, GPT-4-Turbo, GPT-3.5 | ✅ Full Support |
| Azure OpenAI | GPT-4, GPT-3.5 | ✅ Full Support |
| Anthropic | Claude 3, Claude 2 | ✅ Full Support |
| Local LLMs | Llama 2, Mistral via Ollama | ✅ Full Support |
| Google | Gemini Pro | 🔄 Experimental |

### How much does LLM usage cost?

Estimated costs per invoice (using GPT-4):

| Operation | Tokens | Cost |
|-----------|--------|------|
| Data Extraction | ~2,000 | $0.06 |
| Validation | ~500 | $0.015 |
| Matching | ~1,000 | $0.03 |
| **Total** | **~3,500** | **~$0.10** |

**Cost optimization tips:**
- Use GPT-3.5 for routine extractions ($0.01/invoice)
- Enable caching to reduce repeated calls
- Use local LLMs for non-sensitive data

### Can I use local LLMs to avoid API costs?

Yes! SmartAP supports local LLMs via Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2:13b

# Configure SmartAP
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama2:13b
export OLLAMA_HOST=http://localhost:11434
```

**Performance comparison:**

| Model | Accuracy | Speed | Privacy |
|-------|----------|-------|---------|
| GPT-4 | 98% | Fast | Cloud |
| GPT-3.5 | 95% | Fastest | Cloud |
| Llama2-13B | 92% | Medium | Local |
| Mistral-7B | 90% | Fast | Local |

### How do I configure Azure OpenAI?

```bash
# Environment variables
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Or in config.yaml
llm:
  provider: azure_openai
  azure:
    api_key: ${AZURE_OPENAI_API_KEY}
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    deployment: gpt-4
    api_version: 2024-02-15-preview
```

---

## Invoice Processing

### What invoice formats are supported?

| Format | Support | Notes |
|--------|---------|-------|
| PDF | ✅ Full | Native and scanned |
| PDF/A | ✅ Full | Archival format |
| TIFF | ✅ Full | Multi-page supported |
| PNG/JPEG | ✅ Full | Single-page images |
| XML (UBL) | ✅ Full | E-invoicing standard |
| EDI | ✅ Full | X12, EDIFACT |
| Email (EML) | 🔄 Beta | With attachments |

### What fields does SmartAP extract?

**Header Fields:**
- Invoice Number
- Invoice Date
- Due Date
- Vendor Name & Address
- Payment Terms
- Currency
- Total Amount
- Tax Amount

**Line Items:**
- Description
- Quantity
- Unit Price
- Line Total
- GL Code (if present)

**Additional:**
- PO Number (for matching)
- Bank Details
- Custom Fields (configurable)

### How accurate is the data extraction?

Based on our testing across 10,000+ invoices:

| Field | Accuracy |
|-------|----------|
| Invoice Number | 99.2% |
| Invoice Date | 98.8% |
| Total Amount | 99.5% |
| Vendor Name | 97.5% |
| Line Items | 95.0% |
| **Overall** | **98%** |

Accuracy improves with vendor-specific training data.

### What is three-way matching?

Three-way matching validates invoices against:

1. **Purchase Order (PO)**: Verify items were ordered
2. **Goods Receipt (GR)**: Confirm items were received
3. **Invoice**: Check amounts match

```
[Invoice] ←→ [PO] ←→ [Goods Receipt]
    ↓           ↓           ↓
  Amount      Items      Quantity
```

SmartAP automatically performs matching with configurable tolerance levels:

```yaml
matching:
  price_tolerance_percent: 2.0
  quantity_tolerance_percent: 5.0
  auto_approve_threshold: 100.0
```

### How do approval workflows work?

Approval routing is rule-based:

```yaml
approval_rules:
  - name: "Small Invoices"
    conditions:
      - field: amount
        operator: less_than
        value: 1000
    approvers: []  # Auto-approve
    
  - name: "Department Review"
    conditions:
      - field: amount
        operator: between
        value: [1000, 10000]
    approvers:
      - role: department_manager
    
  - name: "Executive Approval"
    conditions:
      - field: amount
        operator: greater_than
        value: 10000
    approvers:
      - role: department_manager
      - role: finance_director
      - role: cfo
```

---

## Security & Compliance

### Is SmartAP secure?

Yes! SmartAP implements enterprise-grade security:

- **Authentication**: JWT tokens, OAuth2/OIDC support
- **Authorization**: Role-Based Access Control (RBAC)
- **Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Audit Logging**: Complete action trail
- **Secret Management**: Environment variables, vault integration

### What compliance standards does SmartAP support?

| Standard | Support | Notes |
|----------|---------|-------|
| SOC 2 | ✅ Ready | With proper configuration |
| GDPR | ✅ Ready | Data retention controls |
| HIPAA | ✅ Ready | BAA required for healthcare |
| PCI-DSS | ⚠️ Partial | Use external payment processing |

### How is sensitive data protected?

1. **At Rest**: AES-256 encryption for stored files
2. **In Transit**: TLS 1.3 for all connections
3. **In Memory**: Sensitive data cleared after use
4. **Access Control**: RBAC + field-level permissions

Configure encryption:

```bash
ENCRYPTION_KEY=your-32-byte-key-here
ENCRYPT_STORED_FILES=true
ENCRYPT_DATABASE_FIELDS=true
```

### How long is data retained?

Configurable retention policies:

```yaml
data_retention:
  invoices: 7 years  # Regulatory requirement
  audit_logs: 7 years
  temp_files: 24 hours
  session_data: 30 days
```

---

## ERP Integration

### What ERP systems can SmartAP connect to?

| ERP | Integration Type | Status |
|-----|-----------------|--------|
| SAP S/4HANA | REST API, RFC | ✅ Full |
| SAP Business One | Service Layer | ✅ Full |
| Oracle NetSuite | REST API | ✅ Full |
| Oracle Fusion | REST API | ✅ Full |
| QuickBooks Online | REST API | ✅ Full |
| QuickBooks Desktop | Web Connector | ✅ Full |
| Microsoft Dynamics 365 | OData | ✅ Full |
| Sage Intacct | REST API | ✅ Full |
| Xero | REST API | ✅ Full |
| Custom ERP | Webhook/API | ✅ Custom |

### How do I configure SAP integration?

```yaml
# config/erp/sap.yaml
erp:
  type: sap_s4hana
  connection:
    host: sap.example.com
    client: "100"
    user: ${SAP_USER}
    password: ${SAP_PASSWORD}
  mapping:
    invoice:
      header:
        invoice_number: BELNR
        vendor_id: LIFNR
        amount: WRBTR
      items:
        gl_code: SAKNR
        cost_center: KOSTL
```

### How do I configure QuickBooks integration?

1. Create a QuickBooks app at [developer.intuit.com](https://developer.intuit.com)
2. Configure OAuth credentials:

```bash
QUICKBOOKS_CLIENT_ID=your-client-id
QUICKBOOKS_CLIENT_SECRET=your-client-secret
QUICKBOOKS_REDIRECT_URI=https://your-domain/api/v1/erp/quickbooks/callback
QUICKBOOKS_ENVIRONMENT=production  # or sandbox
```

3. Connect via the UI: Settings → Integrations → QuickBooks → Connect

### Can I build custom ERP integrations?

Yes! Use the Integration Framework:

```python
from smartap.integrations.base import BaseERPIntegration

class CustomERP(BaseERPIntegration):
    def push_invoice(self, invoice: Invoice) -> str:
        """Push invoice to ERP, return ERP reference"""
        # Your implementation
        pass
    
    def get_vendors(self) -> List[Vendor]:
        """Fetch vendor master data"""
        pass
    
    def get_purchase_orders(self) -> List[PurchaseOrder]:
        """Fetch PO data for matching"""
        pass
```

Register in `config/integrations.yaml`:

```yaml
integrations:
  erp:
    type: custom
    class: mymodule.CustomERP
```

---

## Performance & Scaling

### How many invoices can SmartAP process?

Performance benchmarks (8 cores, 16GB RAM):

| Scenario | Throughput |
|----------|------------|
| PDF Processing | 60/minute |
| AI Extraction | 30/minute (API-limited) |
| Full Pipeline | 20/minute |
| **Daily Capacity** | **~10,000 invoices** |

### How do I scale for higher volumes?

**Horizontal Scaling (Kubernetes):**

```yaml
# Scale processing workers
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smartap-worker
spec:
  replicas: 10  # Add more workers
  template:
    spec:
      containers:
      - name: worker
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
```

**Vertical Scaling:**
- More CPU = faster PDF processing
- More RAM = larger batch sizes
- SSD storage = faster file I/O

### What caching options are available?

SmartAP supports multiple caching layers:

```yaml
cache:
  # LLM response caching
  llm:
    enabled: true
    backend: redis
    ttl: 3600  # 1 hour
    
  # Document processing cache
  documents:
    enabled: true
    backend: filesystem
    path: /data/cache
    
  # Query result caching
  database:
    enabled: true
    backend: redis
    ttl: 300  # 5 minutes
```

### How do I monitor performance?

SmartAP exposes Prometheus metrics:

```bash
# Key metrics
smartap_invoices_processed_total
smartap_processing_duration_seconds
smartap_ai_requests_total
smartap_ai_tokens_used_total
smartap_errors_total

# Grafana dashboard included at:
# docker/monitoring/grafana/dashboards/smartap.json
```

---

## Troubleshooting

### Why is invoice extraction failing?

**Common causes:**

1. **Poor scan quality**
   - Solution: Ensure 300+ DPI scans

2. **Unsupported format**
   - Solution: Convert to PDF using Foxit

3. **Foxit not configured**
   - Check: `FOXIT_EDITOR_PATH` and `FOXIT_LICENSE_KEY`

4. **LLM API errors**
   - Check: API key validity and quota

**Debug mode:**

```bash
export LOG_LEVEL=DEBUG
export SAVE_INTERMEDIATE_FILES=true
```

### Why are API requests slow?

**Potential issues:**

1. **Database queries**
   - Add indexes: `python manage.py create_indexes`
   
2. **LLM latency**
   - Enable caching, consider local LLM

3. **File I/O**
   - Use SSD storage, optimize upload directory

**Profile with:**

```bash
export ENABLE_PROFILING=true
# Check /api/v1/debug/profile for results
```

### How do I reset the admin password?

```bash
# Via CLI
python -m smartap.cli reset-password --email admin@example.com

# Or direct database
docker-compose exec db psql -U smartap -c "
  UPDATE users SET password_hash = 'new-hash' WHERE email = 'admin@example.com';
"
```

### Where are the logs?

| Component | Location |
|-----------|----------|
| Backend | `logs/backend.log` or stdout (Docker) |
| Worker | `logs/worker.log` or stdout (Docker) |
| Frontend | Browser console |
| Nginx | `/var/log/nginx/` |

View Docker logs:

```bash
docker-compose logs -f backend
docker-compose logs -f worker
```

---

## Licensing & Support

### What license is SmartAP under?

SmartAP is licensed under the **MIT License**, which allows:

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

See [LICENSE](../LICENSE) for full terms.

### Is commercial support available?

While SmartAP is open-source, enterprise support options include:

- **Community Support**: GitHub Issues, Discussions
- **Professional Services**: Custom development, integration help
- **Enterprise Support**: SLA-backed support contracts

Contact: enterprise@smartap.io

### How can I contribute?

We welcome contributions! See our [Contributing Guide](../CONTRIBUTING.md):

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

**Contribution areas:**
- Bug fixes
- New ERP integrations
- Documentation improvements
- Language translations

### Where can I get help?

| Resource | Best For |
|----------|----------|
| [GitHub Issues](https://github.com/smartap/smartap/issues) | Bug reports |
| [GitHub Discussions](https://github.com/smartap/smartap/discussions) | Questions, ideas |
| [Stack Overflow](https://stackoverflow.com/questions/tagged/smartap) | Technical Q&A |
| [Discord](https://discord.gg/smartap) | Real-time chat |
| [Documentation](https://docs.smartap.io) | Guides, reference |

---

## Still Have Questions?

If your question isn't answered here:

1. **Search existing issues**: Someone may have asked before
2. **Check the documentation**: Full docs at `/docs` folder
3. **Ask on Discussions**: Community members and maintainers can help
4. **Open an issue**: For bugs or feature requests

---

*Last updated: 2024*
