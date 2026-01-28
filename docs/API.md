# ECIR Studio API Documentation

Complete API reference for the ECIR Studio system.

## Table of Contents

- [PDF Rendering API](#pdf-rendering-api)
- [Evidence Ingestion API](#evidence-ingestion-api)
- [CLI Reference](#cli-reference)
- [Data Schemas](#data-schemas)

---

## PDF Rendering API

### `generate_eicr_pdf()`

Generate an EICR PDF document.

**Module:** `src.rendering.pdf_renderer`

**Signature:**
```python
def generate_eicr_pdf(
    output_path: str,
    template_type: str = "blank",
    data: Optional[Dict] = None
) -> str
```

**Parameters:**
- `output_path` (str): Path where PDF will be saved
- `template_type` (str): Type of template - "blank" or "filled"
- `data` (Dict, optional): EICR data dictionary (required for "filled" template)

**Returns:**
- str: Path to generated PDF file

**Raises:**
- `ValueError`: If template_type is invalid or data is missing for filled template
- `FileNotFoundError`: If template or style files are missing

**Example:**
```python
from rendering import generate_eicr_pdf

# Generate blank template
blank_pdf = generate_eicr_pdf(
    output_path="blank_eicr.pdf",
    template_type="blank"
)

# Generate filled template
data = {
    "report_id": "EICR-2026-001",
    "sections": {
        "section_a": {
            "client_name": "John Doe",
            "client_address": "123 Main St",
            "purpose_of_report": "Periodic inspection"
        },
        # ... more sections
    }
}

filled_pdf = generate_eicr_pdf(
    output_path="filled_eicr.pdf",
    template_type="filled",
    data=data
)
```

### `ECIRPDFRenderer`

PDF rendering class with advanced options.

**Constructor:**
```python
renderer = ECIRPDFRenderer()
```

**Methods:**

#### `generate_pdf()`
```python
def generate_pdf(
    self,
    output_path: str,
    template_type: str = "blank",
    data: Optional[Dict] = None
) -> str
```

Generate PDF with full control over rendering process.

---

## Evidence Ingestion API

### `EvidenceIngestionPipeline`

Main orchestrator for evidence ingestion workflow.

**Module:** `src.ingestion.evidence_pipeline`

**Constructor:**
```python
from ingestion import EvidenceIngestionPipeline

pipeline = EvidenceIngestionPipeline(
    storage_path="/path/to/storage",  # Optional
    nice_config={                      # Optional
        "api_url": "https://nice-api.example.com",
        "api_key": "your-api-key"
    }
)
```

**Parameters:**
- `storage_path` (str, optional): Path for local evidence storage. Defaults to `~/.ecir_evidence_store`
- `nice_config` (dict, optional): NICE system configuration. If not provided, uses mock mode.

### Methods

#### `ingest_image()`

Ingest a single evidence image.

```python
def ingest_image(
    self,
    image_path: Optional[str] = None,
    image_data: Optional[bytes] = None,
    description: str = "",
    location: str = "",
    inspector: str = "",
    metadata: Optional[Dict] = None
) -> Dict
```

**Parameters:**
- `image_path` (str, optional): Path to image file
- `image_data` (bytes, optional): Raw image data (alternative to image_path)
- `description` (str): Description of the evidence
- `location` (str): Location where evidence was captured
- `inspector` (str): Name of inspector
- `metadata` (dict, optional): Additional metadata

**Returns:**
```python
{
    "evidence_id": "EVD-20260128-ABC123",
    "nice_reference": "NICE-20260128-XYZ",
    "timestamp": "2026-01-28T14:30:00Z",
    "description": "Damaged socket-outlet",
    "location": "Kitchen",
    "inspector": "John Smith",
    "metadata": {...},
    "storage_path": "s3://evidence/...",
    "thumbnail_path": "/path/to/thumbnail.jpg",
    "created_at": "2026-01-28T14:30:00Z"
}
```

**Example:**
```python
evidence = pipeline.ingest_image(
    image_path="/path/to/photo.jpg",
    description="Damaged socket-outlet in kitchen",
    location="Ground floor - Kitchen",
    inspector="John Smith"
)

print(f"Evidence ID: {evidence['evidence_id']}")
print(f"NICE Reference: {evidence['nice_reference']}")
```

#### `link_evidence()`

Link evidence to an EICR observation.

```python
def link_evidence(
    self,
    eicr_id: str,
    observation_item: str,
    evidence_ids: List[str]
) -> Dict
```

**Parameters:**
- `eicr_id` (str): EICR report ID (format: `EICR-YYYY-NNN`)
- `observation_item` (str): Observation item number (e.g., "5.18")
- `evidence_ids` (List[str]): List of evidence IDs to link

**Returns:**
```python
{
    "eicr_id": "EICR-2026-001",
    "observation_item": "5.18",
    "evidence_ids": ["EVD-20260128-ABC123", "EVD-20260128-DEF456"],
    "linked_at": "2026-01-28T14:35:00Z"
}
```

**Example:**
```python
link_result = pipeline.link_evidence(
    eicr_id="EICR-2026-001",
    observation_item="5.18",
    evidence_ids=["EVD-20260128-ABC123"]
)
```

#### `list_evidence()`

List evidence with optional filters.

```python
def list_evidence(
    self,
    eicr_id: Optional[str] = None,
    inspector: Optional[str] = None,
    location: Optional[str] = None
) -> List[Dict]
```

**Example:**
```python
# List all evidence
all_evidence = pipeline.list_evidence()

# Filter by EICR
eicr_evidence = pipeline.list_evidence(eicr_id="EICR-2026-001")

# Filter by inspector
inspector_evidence = pipeline.list_evidence(inspector="John Smith")
```

---

## CLI Reference

### PDF Rendering Commands

#### Generate Blank Template
```bash
python src/cli.py render generate --template blank --output blank_eicr.pdf
```

#### Generate Filled Template
```bash
python src/cli.py render generate --template filled --data report_data.json --output filled_eicr.pdf
```

### Evidence Commands

#### Ingest Evidence
```bash
python src/cli.py evidence ingest photo.jpg \
  --description "Damaged socket-outlet" \
  --location "Kitchen" \
  --inspector "John Smith"
```

#### Link Evidence
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

#### Get Evidence Info
```bash
python src/cli.py evidence info EVD-20260128-ABC123
```

---

## Data Schemas

### EICR Report Structure

```json
{
  "report_id": "EICR-2026-001",
  "version": "1.0",
  "created_at": "2026-01-28T12:00:00Z",
  "sections": {
    "section_a": {
      "client_name": "string",
      "client_address": "string",
      "purpose_of_report": "string"
    },
    "section_b": {
      "reason": "periodic_inspection | change_of_occupancy | ...",
      "other_reason": "string?"
    },
    "section_c": {
      "occupier": "string",
      "installation_address": "string",
      "type_of_installation": "string",
      "estimated_age": "string?"
    },
    "section_d": {
      "extent_of_inspection": "string",
      "limitations": ["string"],
      "percentage_inspected": 0-100
    },
    "section_e": {
      "general_condition": "string",
      "overall_assessment": "SATISFACTORY | UNSATISFACTORY"
    },
    "section_f": {
      "recommendations": [
        {
          "code": "C1 | C2 | C3 | FI",
          "description": "string",
          "reference": "string"
        }
      ]
    },
    "section_g": {
      "inspector_name": "string",
      "inspector_position": "string",
      "date_of_inspection": "YYYY-MM-DD",
      "signature": "string",
      "next_inspection_date": "YYYY-MM-DD?"
    },
    "section_k": {
      "observations": [
        {
          "item": "string",
          "description": "string",
          "classification": "C1 | C2 | C3 | FI",
          "evidence_refs": [
            {
              "id": "EVD-...",
              "nice_ref": "NICE-...",
              "description": "string",
              "captured_at": "ISO8601"
            }
          ]
        }
      ]
    }
  },
  "schedules": {
    "circuit_details": [...],
    "test_results": [...],
    "inspection_schedule": {...}
  }
}
```

### Evidence Record Structure

```json
{
  "evidence_id": "EVD-20260128-ABC123",
  "nice_reference": "NICE-20260128-XYZ",
  "description": "string",
  "location": "string",
  "inspector": "string",
  "timestamp": "ISO8601",
  "metadata": {
    "format": "JPEG",
    "width": 4032,
    "height": 3024,
    "exif": {...}
  },
  "storage_path": "s3://...",
  "thumbnail_path": "/path/to/thumbnail",
  "created_at": "ISO8601"
}
```

---

## Authority Boundaries

### Critical Constraints

**DO NOT:**
- Auto-assign C1/C2/C3/FI classification codes
- Auto-select "SATISFACTORY" or "UNSATISFACTORY"
- Generate AI-written observations
- Embed full evidence images in ECIR JSON or PDF

**DO:**
- Require explicit human assertion for all critical fields
- Reference evidence by ID only
- Provide clear UI for manual input
- Validate data formats only, not compliance

---

## Error Handling

### Common Errors

#### PDF Generation
- `ValueError`: Invalid template type or missing data
- `FileNotFoundError`: Template or style files missing

#### Evidence Ingestion
- `ValueError`: Invalid image format or validation failure
- `ValidationError`: Image doesn't meet requirements

### Error Response Format

```python
{
    "error": "Error message",
    "code": "ERROR_CODE",
    "details": {...}
}
```

---

## Security Considerations

1. **Evidence Storage**: Full images stored in NICE system only
2. **Validation**: All inputs validated before processing
3. **Authority**: Critical fields protected from auto-assignment
4. **Audit Trail**: All actions logged with timestamps

---

For more information, see:
- [PDF Rendering Guide](PDF_RENDERING.md)
- [Evidence Pipeline Guide](EVIDENCE_PIPELINE.md)
- [React UI Guide](REACT_UI.md)
