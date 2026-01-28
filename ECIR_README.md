# ECIR Studio

**Electrical Installation Condition Report System**

A complete toolkit for creating, managing, and documenting EICR (Electrical Installation Condition Report) forms with PDF generation, evidence management, and a modern React UI.

## 🎯 Features

### 1. **Styled PDF Generation**
- Generate blank EICR templates for manual completion
- Create filled PDFs from JSON data
- Professional layout matching official EICR forms
- Multi-page documents with proper formatting
- Table layouts for Circuit Details and Test Results
- Inspection Schedule checklists

### 2. **React UI Components**
- Complete form interface for all EICR sections (A-K)
- Client-side validation matching EICR schema
- Responsive design for desktop, tablet, and mobile
- Auto-save functionality
- Progress tracking
- Accessibility compliant (WCAG 2.1 AA)

### 3. **Evidence Ingestion Pipeline**
- Image upload and validation (JPG, PNG, HEIC)
- Integration with NICE evidence management system
- Evidence linking to EICR observations
- Thumbnail generation
- Metadata extraction (EXIF)
- Reference-based storage (no embedded images)

## 🔒 Authority Boundaries

This system enforces critical authority boundaries to maintain compliance:

- ❌ **NO** auto-assignment of C1/C2/C3/FI classification codes
- ❌ **NO** auto-selection of "SATISFACTORY/UNSATISFACTORY" assessment
- ❌ **NO** AI-generated observations or descriptions
- ❌ **NO** embedded images in ECIR documents
- ✅ **YES** Human assertion required for all critical fields
- ✅ **YES** Evidence referenced by ID only
- ✅ **YES** Complete audit trails

## 📋 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ (for React UI)
- pip and npm

### Installation

```bash
# Clone the repository
git clone https://github.com/zebadiee/ai-cli-sphere.git
cd ai-cli-sphere

# Install Python dependencies
pip install -r requirements.txt

# Install React dependencies (optional)
cd frontend
npm install
cd ..
```

### Quick Demo

Run the complete system demonstration:

```bash
python demo.py
```

This will demonstrate:
1. PDF generation (blank and filled templates)
2. Evidence ingestion
3. Evidence linking
4. Evidence retrieval

## 🚀 Usage

### 1. PDF Generation

#### Generate Blank Template

```bash
python src/cli.py render generate --template blank --output blank_eicr.pdf
```

#### Generate Filled Report

```bash
python src/cli.py render generate \
  --template filled \
  --data report_data.json \
  --output filled_eicr.pdf
```

#### Python API

```python
from rendering import generate_eicr_pdf

# Generate blank template
generate_eicr_pdf("blank.pdf", "blank")

# Generate filled report
data = {
    "report_id": "EICR-2026-001",
    "sections": {
        "section_a": {
            "client_name": "ABC Company",
            "client_address": "123 Main St",
            "purpose_of_report": "Periodic inspection"
        },
        # ... more sections
    }
}
generate_eicr_pdf("filled.pdf", "filled", data)
```

### 2. Evidence Management

#### Ingest Evidence

```bash
python src/cli.py evidence ingest photo.jpg \
  --description "Damaged socket-outlet" \
  --location "Kitchen" \
  --inspector "John Smith"
```

#### Link Evidence to Observation

```bash
python src/cli.py evidence link EVD-20260128-ABC123 \
  --eicr EICR-2026-001 \
  --item 5.18
```

#### List Evidence

```bash
# List all evidence
python src/cli.py evidence list

# Filter by EICR
python src/cli.py evidence list --eicr EICR-2026-001

# JSON output
python src/cli.py evidence list --format json
```

#### Python API

```python
from ingestion import EvidenceIngestionPipeline

pipeline = EvidenceIngestionPipeline()

# Ingest image
evidence = pipeline.ingest_image(
    image_path="/path/to/photo.jpg",
    description="Damaged socket",
    location="Kitchen",
    inspector="John Smith"
)

# Link to EICR
pipeline.link_evidence(
    eicr_id="EICR-2026-001",
    observation_item="5.18",
    evidence_ids=[evidence["evidence_id"]]
)
```

### 3. React UI

Start the development server:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

Build for production:

```bash
cd frontend
npm run build
```

## 📁 Project Structure

```
.
├── src/
│   ├── ecir_studio/          # Core ECIR system
│   │   ├── contracts.py      # Authority contracts (LOCKED)
│   │   ├── ecir_schema.json  # ECIR schema (LOCKED)
│   │   ├── ecir_template.md  # Human-readable template
│   │   └── ecir_layout_contract.yaml  # Layout definition
│   ├── rendering/            # PDF generation
│   │   ├── pdf_renderer.py
│   │   ├── templates/        # HTML templates
│   │   └── styles/           # CSS styles
│   ├── ingestion/            # Evidence pipeline
│   │   ├── evidence_pipeline.py
│   │   ├── image_processor.py
│   │   ├── nice_adapter.py
│   │   ├── evidence_store.py
│   │   └── linking.py
│   └── cli.py                # Command-line interface
├── frontend/                 # React UI
│   ├── src/
│   │   ├── components/
│   │   │   ├── forms/        # ECIR form sections
│   │   │   └── ui/           # Reusable UI components
│   │   ├── schemas/          # Validation schemas
│   │   └── App.tsx
│   └── package.json
├── tests/                    # Test suite
│   ├── test_pdf_rendering.py
│   └── test_evidence_ingestion.py
├── docs/                     # Documentation
│   ├── API.md
│   ├── PDF_RENDERING.md
│   ├── EVIDENCE_PIPELINE.md
│   └── REACT_UI.md
├── demo.py                   # Complete demo script
└── requirements.txt
```

## 🧪 Testing

Run the test suite:

```bash
# PDF rendering tests
python tests/test_pdf_rendering.py

# Evidence ingestion tests
python tests/test_evidence_ingestion.py
```

## 📚 Documentation

- [Complete API Reference](docs/API.md)
- [PDF Rendering Guide](docs/PDF_RENDERING.md)
- [Evidence Pipeline Guide](docs/EVIDENCE_PIPELINE.md)
- [React UI Guide](docs/REACT_UI.md)

## 🔐 Security & Compliance

### Data Storage
- Full images stored in NICE system only
- Local storage contains only metadata and thumbnails
- Evidence referenced by ID, never embedded

### Authority Enforcement
- Critical fields protected from auto-assignment
- Human assertion required for compliance codes
- Complete audit trails for all actions
- Validation of data formats only, not compliance

### Best Practices
- Validate all inputs before processing
- Use secure file permissions for generated PDFs
- Store API keys in environment variables
- Enable audit logging in production

## 🛠️ Development

### System Requirements

**For PDF Generation:**
- Python 3.8+
- weasyprint 60.0+
- Pillow 10.0+

On Ubuntu/Debian:
```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
```

On macOS:
```bash
brew install pango cairo
```

**For React UI:**
- Node.js 18+
- npm or yarn

### Adding New Form Sections

1. Create component in `frontend/src/components/forms/`
2. Add to schema in `frontend/src/schemas/eicr-validation.ts`
3. Register in `ECIRForm.tsx`
4. Update PDF template if needed

### Extending Evidence Types

1. Add validation in `image_processor.py`
2. Update NICE adapter if needed
3. Add CLI commands in `cli.py`

## 🤝 Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Documentation is updated
- Authority boundaries are respected
- Security best practices are followed

## 📄 License

See LICENSE file in the repository.

## 🙏 Acknowledgments

- BS 7671 electrical safety standards
- NICE evidence management system
- React and TypeScript communities

---

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-01-28
