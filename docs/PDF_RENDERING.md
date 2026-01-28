# PDF Rendering Guide

Complete guide to generating EICR PDFs using the ECIR Studio rendering engine.

## Overview

The PDF rendering system generates professional, visually accurate EICR forms that match the official layout. It uses **weasyprint** to convert HTML/CSS templates into PDF documents.

## Features

- ✅ Blank template generation for manual filling
- ✅ Filled template generation from JSON data
- ✅ Multi-page layout (6+ pages)
- ✅ Professional styling matching official forms
- ✅ Table layouts for Circuit Details and Test Results
- ✅ Checkbox/radio styling for Inspection Schedule
- ✅ Proper page breaks and headers/footers

## Quick Start

### Generate a Blank Template

```python
from rendering import generate_eicr_pdf

# Generate blank PDF
generate_eicr_pdf(
    output_path="blank_eicr.pdf",
    template_type="blank"
)
```

### Generate a Filled Report

```python
from rendering import generate_eicr_pdf

# Load your EICR data
data = {
    "report_id": "EICR-2026-001",
    "sections": {
        "section_a": {
            "client_name": "ABC Company Ltd",
            "client_address": "123 Business Park\nCity, County\nPOST CODE",
            "purpose_of_report": "Periodic inspection as per BS 7671"
        },
        "section_e": {
            "general_condition": "The installation is generally in satisfactory condition with minor observations noted.",
            "overall_assessment": "SATISFACTORY"
        },
        "section_g": {
            "inspector_name": "John Smith",
            "inspector_position": "Qualified Electrician",
            "date_of_inspection": "2026-01-28",
            "signature": "J. Smith",
            "next_inspection_date": "2031-01-28"
        }
    }
}

# Generate filled PDF
generate_eicr_pdf(
    output_path="filled_eicr.pdf",
    template_type="filled",
    data=data
)
```

## Using the CLI

### Generate Blank Template

```bash
python src/cli.py render generate --template blank --output blank_eicr.pdf
```

### Generate Filled Template

First, prepare your data in a JSON file (`report_data.json`):

```json
{
  "report_id": "EICR-2026-001",
  "sections": {
    "section_a": {
      "client_name": "ABC Company",
      "client_address": "123 Main Street",
      "purpose_of_report": "Periodic inspection"
    }
  }
}
```

Then generate the PDF:

```bash
python src/cli.py render generate \
  --template filled \
  --data report_data.json \
  --output filled_eicr.pdf
```

## Template Structure

### Page Layout

The EICR template consists of multiple pages:

1. **Page 1**: Sections A, B, C (Details and Installation Info)
2. **Page 2**: Sections D, E, F (Extent, Summary, Recommendations)
3. **Page 3**: Sections G, H (Declaration, Schedule Reference)
4. **Page 4**: Sections I, J (Supply Characteristics, Particulars)
5. **Page 5**: Section K (Observations)
6. **Page 6**: Schedule of Circuit Details (table)
7. **Page 7**: Schedule of Test Results (table)
8. **Pages 8-9**: Inspection Schedule (checklist)

### Styling Features

- **Headers**: Professional headers with report number and page numbers
- **Sections**: Clearly marked section headers with gray backgrounds
- **Form Fields**: Underlined fields or bordered boxes for input
- **Tables**: Properly formatted tables with borders and alternating row colors
- **Checkboxes**: Square checkboxes for inspection schedule
- **Radio Buttons**: Circular radio buttons for selections
- **Evidence References**: Highlighted boxes for evidence links

## Advanced Usage

### Custom Styling

The rendering engine uses three files:

1. `templates/eicr_template.html` - HTML structure
2. `styles/eicr.css` - Visual styling
3. `pdf_renderer.py` - Rendering logic

To customize styling, modify `styles/eicr.css`:

```css
/* Custom header color */
.section h2 {
    background-color: #3b82f6;  /* Blue instead of gray */
    color: white;
}

/* Larger font for observations */
.observation-item {
    font-size: 11pt;
}
```

### Adding Custom Sections

To add custom sections, modify `templates/eicr_template.html`:

```html
<!-- Custom section -->
<div class="section">
    <h2>Custom Section: Additional Notes</h2>
    <div class="form-field">
        <label>Notes:</label>
        <div class="field-value multiline">{{custom_notes}}</div>
    </div>
</div>
```

## Data Format

### Required Fields

For a valid filled template, include these required fields:

```python
{
    "report_id": "EICR-YYYY-NNN",  # Format: EICR-2026-001
    "sections": {
        "section_g": {  # Declaration is required
            "inspector_name": "string",
            "date_of_inspection": "YYYY-MM-DD"
        }
    }
}
```

### Optional Sections

All other sections are optional. If not provided, fields will be left blank.

### Observations with Evidence

To include observations with evidence references:

```python
{
    "sections": {
        "section_k": {
            "observations": [
                {
                    "item": "5.18",
                    "description": "Damaged socket-outlet observed in kitchen",
                    "classification": "C2",
                    "evidence_refs": [
                        {
                            "id": "EVD-20260128-ABC123",
                            "nice_ref": "NICE-20260128-XYZ",
                            "description": "Photo of damaged socket",
                            "captured_at": "2026-01-28T14:30:00Z"
                        }
                    ]
                }
            ]
        }
    }
}
```

**Note**: Evidence is REFERENCED, not embedded. Full images are stored in NICE system.

## Troubleshooting

### Common Issues

#### PDF Not Generating

**Problem**: `FileNotFoundError` when generating PDF

**Solution**: Ensure template and style files exist:
```bash
ls src/rendering/templates/eicr_template.html
ls src/rendering/styles/eicr.css
```

#### Missing Data in Filled Template

**Problem**: Some fields appear blank in filled template

**Solution**: Check your data structure matches the expected format:
```python
# Use the correct nested structure
data = {
    "sections": {
        "section_a": {  # Note: nested under "sections"
            "client_name": "John Doe"
        }
    }
}
```

#### Styling Issues

**Problem**: PDF doesn't look right

**Solution**: 
1. Check CSS file is valid
2. Ensure weasyprint is properly installed: `pip install weasyprint`
3. On Linux, install system dependencies: `apt-get install libpango-1.0-0 libpangoft2-1.0-0`

### System Requirements

- Python 3.8+
- weasyprint 60.0+
- Pillow 10.0+ (for image handling)

On Ubuntu/Debian:
```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
```

On macOS:
```bash
brew install pango cairo
```

## Best Practices

### 1. Validate Data Before Rendering

```python
from ecir_studio.contracts import ValidationRules

# Validate report ID
if not ValidationRules.validate_report_id(data["report_id"]):
    raise ValueError("Invalid report ID format")

# Validate observations
for obs in data.get("sections", {}).get("section_k", {}).get("observations", []):
    errors = ValidationRules.validate_observation(obs)
    if errors:
        print(f"Observation errors: {errors}")
```

### 2. Use Descriptive File Names

```python
# Good
output_path = f"EICR_{report_id}_{date}.pdf"

# Better
output_path = f"EICR_{report_id}_{client_name}_{date}.pdf"
```

### 3. Store PDFs Securely

```python
import os
from pathlib import Path

# Create secure directory
output_dir = Path("/secure/reports")
output_dir.mkdir(parents=True, exist_ok=True)

# Set restrictive permissions
os.chmod(output_dir, 0o700)

# Save PDF
output_path = output_dir / f"{report_id}.pdf"
generate_eicr_pdf(str(output_path), "filled", data)
```

### 4. Include Audit Trail

```python
from ecir_studio.contracts import AuditTrail

# Create audit entry
audit = AuditTrail.create_audit_entry(
    action="PDF_GENERATED",
    user="john.smith@example.com",
    data={"report_id": data["report_id"], "output_path": output_path}
)
```

## Integration Examples

### With Web Application

```python
from flask import Flask, request, send_file
import tempfile

app = Flask(__name__)

@app.route('/api/eicr/pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    
    # Generate PDF in temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        generate_eicr_pdf(tmp.name, "filled", data)
        return send_file(tmp.name, as_attachment=True, 
                        download_name=f"{data['report_id']}.pdf")
```

### Batch Generation

```python
import os
from pathlib import Path

def batch_generate_pdfs(reports_dir, output_dir):
    """Generate PDFs for all JSON reports in a directory"""
    reports = Path(reports_dir).glob("*.json")
    
    for report_file in reports:
        with open(report_file) as f:
            data = json.load(f)
        
        output_path = Path(output_dir) / f"{data['report_id']}.pdf"
        generate_eicr_pdf(str(output_path), "filled", data)
        print(f"Generated: {output_path}")
```

## Next Steps

- [Evidence Ingestion Guide](EVIDENCE_PIPELINE.md)
- [React UI Guide](REACT_UI.md)
- [Complete API Reference](API.md)
