# EICR CLI Usage Guide

## Overview

The EICR CLI provides a comprehensive terminal-based interface for creating, managing, and validating Electrical Installation Condition Reports (EICRs) compliant with BS 7671:2018+A2:2022.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Interactive Mode](#interactive-mode)
4. [Data-Driven Mode](#data-driven-mode)
5. [Command Reference](#command-reference)
6. [Examples](#examples)

---

## Installation

### Requirements

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
cd /path/to/ai-cli-sphere
pip install -r requirements.txt
```

### Verify Installation

```bash
python src/cli.py --help
```

---

## Quick Start

### Create EICR Interactively

```bash
python src/cli.py create --interactive
```

This launches the interactive terminal interface with dropdown menus, prompts, and automatic calculations.

### Create EICR from Measurement Data

```bash
python src/cli.py create --from-data measurements.json --output report.json
```

### Look Up BS 7671 Values

```bash
# Maximum Zs for Type B 6A MCB
python src/cli.py lookup max-zs --device "BS EN 60898" --type B --rating 6

# Cable rating for 2.5mm² cable
python src/cli.py lookup cable-rating --type thermoplastic_70c --csa 2.5 --method C

# Voltage drop
python src/cli.py lookup voltage-drop --type thermoplastic_copper --csa 2.5 --length 20 --current 10
```

---

## Interactive Mode

### Starting Interactive Mode

```bash
python src/cli.py create --interactive
```

### User Interface Flow

The interactive mode guides you through completing an EICR form with the following sections:

#### 1. Report Number

```
Report Number: EICR-2026-01-28_
```

#### 2. Section A: Client Details

```
━━━ SECTION A: DETAILS OF PERSON ORDERING REPORT ━━━

? Name: John Smith
? Address Line 1: 123 Example Street
? Address Line 2 (optional): 
? City: London
? Postcode: SW1A 1AA
? Telephone (optional): 020 1234 5678
```

#### 3. Section B: Installation Details

```
━━━ SECTION B: DETAILS OF THE INSTALLATION ━━━

? Occupier: John Smith
? Installation Address: 123 Example Street, London, SW1A 1AA
? Description of Premises: Domestic dwelling
? Do you know the estimated age? Yes
? Estimated Age (years): 15
? Evidence of Alterations or Additions? No
```

#### 4. Section C: Extent of Inspection

```
━━━ SECTION C: EXTENT AND LIMITATIONS OF INSPECTION ━━━

? Extent of Electrical Installation Covered: Complete installation
? Limitations (if any): None
? Agreed with Client? Yes
```

#### 5. Section D: Summary

```
━━━ SECTION D: SUMMARY OF THE INSPECTION ━━━

? Date(s) of Inspection: 2026-01-28
? Overall Assessment:
  ◉ Satisfactory
  ○ Unsatisfactory
```

#### 6. Section E: Supply Characteristics

```
━━━ SECTION E: SUPPLY CHARACTERISTICS AND EARTHING ARRANGEMENTS ━━━

? Earthing arrangement:
  ◉ TN-S
  ○ TN-C-S
  ○ TT
  ○ IT

? Number of live conductors:
  ◉ 1-phase, 2-wire
  ○ 1-phase, 3-wire
  ○ 3-phase, 4-wire

? Nominal voltage U0 (V): 230
? Auto-calculate prospective fault current from measurements? No
? Prospective fault current (kA): 1.2
? External loop impedance Ze (Ω): 0.35

✓ Ze recorded: 0.35 Ω
```

#### 7. Section F: Particulars of Installation

```
━━━ SECTION F: PARTICULARS OF INSTALLATION AT THE ORIGIN ━━━

? Means of Earthing:
  ◉ Supplier's facility
  ○ Installation earth electrode

? Main Protective Conductor:
  ◉ Copper
  ○ Aluminum
  ○ Steel

? Main Protective Conductor CSA (mm²): 16
? Main Switch/Circuit Breaker Type: BS EN 60947-2
? Main Switch Rating (A): 100
```

#### 8. Section G: Observations (Optional)

```
━━━ SECTION G: OBSERVATIONS AND RECOMMENDATIONS ━━━

? Add observations? Yes

Observation 1:
? Reference/Location: Consumer unit
? Code:
  ○ C1
  ◉ C2
  ○ C3
  ○ FI
? Observation: No RCD protection on socket outlets

? Add another observation? No
```

#### 9. Section H: Circuit Details

```
━━━ SECTION H: SCHEDULE OF CIRCUIT DETAILS AND TEST RESULTS ━━━

━━━ Circuit 1 ━━━

? Circuit Description: Lighting - Ground Floor

? Protection Device Standard:
  ◉ BS EN 60898
  ○ BS EN 61009
  ○ BS 88-3
  ○ BS 1361

? Type:
  ◉ B
  ○ C
  ○ D

? Rating (A): 6

? Cable Type:
  ◉ Thermoplastic 70°C
  ○ Thermosetting 90°C

? Reference Method:
  ○ A
  ○ B
  ◉ C
  ○ D

? Live Conductor CSA (mm²): 1.5
? CPC CSA (mm²): 1.5

ℹ  Calculating maximum Zs from BS 7671 tables...
✓ Max Zs for B 6A: 7.67 Ω

? Measured Zs (Ω): 0.89
✓ Pass (0.89 < 7.67)

? Measured R1+R2 (Ω): 0.45
? Insulation Resistance (MΩ): 250
? Polarity:
  ◉ Pass
  ○ Fail

[+] Add another circuit? Yes

━━━ Circuit 2 ━━━
...
```

#### 10. Section I: Inspector Details

```
━━━ SECTION I: DETAILS OF INSPECTOR ━━━

? Name: Jane Engineer
? Company/Trading Name: ABC Electrical Ltd
? Address: 456 Business Park
? Postcode: SE1 2AB
? Qualifications: IET Level 3, BS 7671:2018+A2
? Signature: J. Engineer
? Date: 2026-01-28
```

#### 11. Section J: Next Inspection

```
━━━ SECTION J: RECOMMENDATION FOR NEXT INSPECTION ━━━

? Recommended Inspection Interval:
  ○ 1 year
  ○ 3 years
  ◉ 5 years
  ○ 10 years
```

### Draft Saving

During the process, you can save your progress:

```
? Save as draft? Yes
✓ Draft saved: /home/user/.eicr_drafts/EICR-2026-01-28.json
```

### Export Options

At the end, you'll be prompted to export:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXPORT OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

? Export to JSON? Yes
? Filename: eicr_report.json
✓ Exported to: eicr_report.json

? Export to PDF? Yes
? Filename: eicr_report.pdf
✓ Exported to: eicr_report.pdf

✓ EICR Complete!
```

---

## Data-Driven Mode

### Measurement Data Format

Create a JSON file with your measurement data:

```json
{
  "supply": {
    "measured_ze": 0.35,
    "measured_ipf": 1.2,
    "earthing_arrangement": "TN-S",
    "number_of_live_conductors": "1-phase, 2-wire",
    "nominal_voltage_u0": 230
  },
  "client": {
    "name": "John Smith",
    "address_line_1": "123 Example Street",
    "city": "London",
    "postcode": "SW1A 1AA"
  },
  "installation": {
    "occupier": "John Smith",
    "installation_address": "123 Example Street, London",
    "description": "Domestic dwelling"
  },
  "circuits": [
    {
      "circuit_number": 1,
      "description": "Lighting - Ground Floor",
      "device_standard": "BS EN 60898",
      "device_type": "B",
      "rating": 6,
      "cable_type": "thermoplastic_70c",
      "cable_csa": 1.5,
      "cable_cpc_csa": 1.5,
      "cable_reference_method": "C",
      "measured_zs": 0.89,
      "measured_r1r2": 0.45,
      "insulation_resistance": 250.0,
      "polarity": "Pass",
      "design_current": 5,
      "cable_length": 15,
      "circuit_type": "lighting"
    },
    {
      "circuit_number": 2,
      "description": "Socket Outlets - Ground Floor",
      "device_standard": "BS EN 60898",
      "device_type": "B",
      "rating": 32,
      "cable_type": "thermoplastic_70c",
      "cable_csa": 4.0,
      "cable_cpc_csa": 2.5,
      "cable_reference_method": "C",
      "measured_zs": 0.72,
      "measured_r1r2": 0.38,
      "insulation_resistance": 300.0,
      "polarity": "Pass",
      "design_current": 20,
      "cable_length": 12,
      "circuit_type": "power"
    }
  ]
}
```

### Create EICR from Data

```bash
python src/cli.py create --from-data measurements.json --output report.json
```

**Output:**
```
Loading measurement data from: measurements.json

✓ EICR created from measurement data
  Circuits: 2
  All valid: True
✓ Exported to: report.json
```

---

## Command Reference

### `ecir create`

Create a new EICR report.

**Options:**
- `--interactive` - Launch interactive terminal form
- `--from-data <file>` - Create from JSON measurement data
- `--output <file>` - Output file path

**Examples:**
```bash
# Interactive mode
python src/cli.py create --interactive

# From data file
python src/cli.py create --from-data measurements.json --output report.json
```

---

### `ecir calculate`

Run calculations on existing EICR data.

**Options:**
- `--input <file>` - Input JSON file (required)
- `--output <file>` - Output file path

**Example:**
```bash
python src/cli.py calculate --input report.json --output calculated.json
```

**Output:**
```
Loading EICR data from: report.json

✓ Calculations complete
  Circuits processed: 2
  Circuit 1: ✓ Pass (Zs: 0.89Ω, Max: 7.67Ω)
  Circuit 2: ✓ Pass (Zs: 0.72Ω, Max: 1.44Ω)

✓ Exported to: calculated.json
```

---

### `ecir validate`

Validate a circuit against BS 7671 requirements.

**Options:**
- `--device <spec>` - Device specification (required)
- `--zs <value>` - Measured Zs in ohms
- `--cable <spec>` - Cable specification (e.g., "1.5mm²")
- `--design-current <value>` - Design current in amps
- `--cable-length <value>` - Cable length in meters

**Example:**
```bash
python src/cli.py validate \
  --device "BS EN 60898 Type B 6A" \
  --zs 0.89 \
  --cable "1.5mm²" \
  --design-current 5 \
  --cable-length 15
```

**Output:**
```
✓ Max Zs for B 6A: 7.67 Ω
✓ Pass: Measured Zs (0.89Ω) ≤ Max Zs (7.67Ω)

━━━ Full Circuit Validation ━━━
Overall: ✓ Pass
  ✓ Overload Protection
  ✓ Fault Protection
  ✓ Voltage Drop
  ✓ Cable Capacity
```

---

### `ecir lookup max-zs`

Look up maximum Zs from BS 7671 tables.

**Options:**
- `--device <standard>` - Device standard (required)
- `--type <type>` - Device type (required)
- `--rating <amps>` - Device rating (required)

**Example:**
```bash
python src/cli.py lookup max-zs --device "BS EN 60898" --type B --rating 6
```

**Output:**
```
Max Zs for BS EN 60898 Type B 6A:
  7.67 Ω
```

---

### `ecir lookup cable-rating`

Look up cable current rating from BS 7671 Appendix 4.

**Options:**
- `--type <type>` - Cable type (required)
- `--csa <mm²>` - Cross-sectional area (required)
- `--method <method>` - Reference method (required)
- `--ambient-temp <°C>` - Ambient temperature (default: 30)
- `--grouping <count>` - Number of grouped circuits (default: 1)

**Example:**
```bash
python src/cli.py lookup cable-rating \
  --type thermoplastic_70c \
  --csa 2.5 \
  --method C \
  --ambient-temp 40 \
  --grouping 2
```

**Output:**
```
Cable Rating for thermoplastic_70c 2.5mm² (Method C):
  Base rating: 24A
  Adjusted rating: 17.75A
  Conditions: 40°C, 2 circuit(s)
```

---

### `ecir lookup voltage-drop`

Look up voltage drop from BS 7671 Appendix 4.

**Options:**
- `--type <type>` - Cable type (required)
- `--csa <mm²>` - Cross-sectional area (required)
- `--length <m>` - Cable length (optional)
- `--current <A>` - Load current (optional)

**Example:**
```bash
python src/cli.py lookup voltage-drop \
  --type thermoplastic_copper \
  --csa 2.5 \
  --length 20 \
  --current 10
```

**Output:**
```
Voltage Drop for thermoplastic_copper 2.5mm²:
  18 mV/A/m

For 20m at 10A:
  Voltage drop: 3.60V (1.6%)
```

---

### `ecir render`

Render EICR data to PDF format.

**Arguments:**
- `<input_file>` - Input JSON file

**Options:**
- `--output <file>` - Output PDF file

**Example:**
```bash
python src/cli.py render report.json --output report.pdf
```

**Output:**
```
Loading EICR data from: report.json
Rendering PDF to: report.pdf
✓ PDF rendered successfully
```

---

### `ecir continue`

Resume working on a draft EICR.

**Arguments:**
- `<draft_id>` - Draft identifier (report number)

**Example:**
```bash
python src/cli.py continue EICR-2026-01-28
```

---

## Examples

### Example 1: Quick Circuit Validation

Validate a circuit before completing full EICR:

```bash
python src/cli.py validate \
  --device "BS EN 60898 Type C 32A" \
  --zs 0.72
```

### Example 2: Look Up Table Values

Check if a cable is suitable for a load:

```bash
# Check base rating
python src/cli.py lookup cable-rating \
  --type thermoplastic_70c \
  --csa 2.5 \
  --method C

# Check with correction factors
python src/cli.py lookup cable-rating \
  --type thermoplastic_70c \
  --csa 2.5 \
  --method C \
  --ambient-temp 35 \
  --grouping 3
```

### Example 3: Automated Testing Workflow

Integrate with existing measurement equipment:

```bash
# 1. Export measurements from equipment to JSON
equipment_export.sh > measurements.json

# 2. Create EICR from measurements
python src/cli.py create --from-data measurements.json --output report.json

# 3. Render PDF for customer
python src/cli.py render report.json --output final_report.pdf
```

### Example 4: Batch Processing

Process multiple properties:

```bash
#!/bin/bash
for property in property_*.json; do
    output="${property%.json}_report.json"
    pdf="${property%.json}_report.pdf"
    
    python src/cli.py create --from-data "$property" --output "$output"
    python src/cli.py render "$output" --output "$pdf"
    
    echo "Completed: $property"
done
```

---

## Tips and Best Practices

### 1. Save Drafts Frequently

When using interactive mode, save drafts periodically to avoid losing work.

### 2. Validate Circuits Individually

Use `ecir validate` to check circuits before adding them to the full EICR.

### 3. Use Measurement Data Format

For repeat inspections, save measurement data in JSON format for quick EICR generation.

### 4. Reference BS 7671 Tables

Use `ecir lookup` commands to reference BS 7671 values during on-site inspections.

### 5. Automate with Scripts

Integrate EICR CLI commands into your testing workflow scripts.

---

## Troubleshooting

### Issue: Command not found

**Solution:**
```bash
# Ensure you're using the correct path
python src/cli.py --help

# Or add to PATH
export PATH=$PATH:/path/to/ai-cli-sphere
```

### Issue: Missing dependencies

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Invalid JSON format

**Solution:** Validate your JSON file:
```bash
python -m json.tool measurements.json
```

### Issue: Value not found in tables

**Solution:** Verify the device/cable specification matches BS 7671 standard values.

---

## Support

For issues or questions:
- Review the [CALCULATIONS.md](CALCULATIONS.md) documentation
- Check BS 7671:2018+A2:2022 requirements
- Verify input data format matches examples

---

**Last Updated:** 2026-01-28  
**Version:** 1.0
