# Terminal-Based EICR System

A comprehensive terminal-based CLI for creating, managing, and validating Electrical Installation Condition Reports (EICRs) compliant with BS 7671:2018+A2:2022 (18th Edition IET Wiring Regulations).

## 🎯 Features

### ✅ Interactive Terminal Interface
- Rich terminal UI with dropdown menus and prompts
- Section-by-section guided form completion
- Auto-calculation of BS 7671 values
- Real-time validation
- Draft saving and resuming

### ✅ BS 7671 Integration
- Complete BS 7671:2018+A2:2022 tables
- Maximum Zs calculations (Tables 41.2-41.5)
- Cable current ratings (Appendix 4)
- Voltage drop calculations
- Correction factors (ambient temperature, grouping, thermal insulation)

### ✅ Algorithm Integration
- Load measurement data from external sources
- Automatic circuit validation
- Batch processing support
- JSON/YAML/PDF export

### ✅ Command-Line Tools
- `ecir create` - Create new EICR (interactive or data-driven)
- `ecir validate` - Validate circuits against BS 7671
- `ecir lookup` - Look up BS 7671 table values
- `ecir calculate` - Run calculations on existing data
- `ecir render` - Export to PDF

## 📦 Installation

### Requirements
- Python 3.8 or higher
- pip package manager

### Install Dependencies
```bash
cd ai-cli-sphere
pip install -r requirements.txt
```

### Verify Installation
```bash
./ecir --help
```

## 🚀 Quick Start

### Interactive Mode
Create an EICR using the interactive terminal interface:

```bash
./ecir create --interactive
```

This launches a guided form with:
- Dropdown menus for all enum fields
- Auto-calculation of max Zs values
- Real-time pass/fail validation
- Draft saving

### Data-Driven Mode
Create an EICR from measurement data:

```bash
./ecir create --from-data example_measurements.json --output report.json
./ecir render report.json --output report.pdf
```

### Quick Lookups
Look up BS 7671 values instantly:

```bash
# Maximum Zs for Type B 6A MCB
./ecir lookup max-zs --device "BS EN 60898" --type B --rating 6
# Output: 7.67 Ω

# Cable rating with correction factors
./ecir lookup cable-rating --type thermoplastic_70c --csa 2.5 --method C --ambient-temp 40 --grouping 2
# Output: Base: 24A, Adjusted: 17.75A

# Voltage drop calculation
./ecir lookup voltage-drop --type thermoplastic_copper --csa 2.5 --length 20 --current 10
# Output: 3.60V (1.6%)
```

### Circuit Validation
Validate a circuit before completing the full EICR:

```bash
./ecir validate \
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

## 📋 Usage Examples

### Example 1: Interactive EICR Creation

```bash
./ecir create --interactive
```

**Interactive Flow:**
```
═══════════════════════════════════════════════════════
║  ELECTRICAL INSTALLATION CONDITION REPORT           ║
║  Terminal Interface                                 ║
═══════════════════════════════════════════════════════

Report Number: EICR-2026-01-28

━━━ SECTION A: DETAILS OF PERSON ORDERING REPORT ━━━

? Name: John Smith
? Address Line 1: 123 Example Street
? City: London
? Postcode: SW1A 1AA

━━━ SECTION E: SUPPLY CHARACTERISTICS ━━━

? Earthing arrangement:
  ◉ TN-S
  ○ TN-C-S
  ○ TT

? External loop impedance Ze (Ω): 0.35
✓ Ze recorded: 0.35 Ω

━━━ SECTION H: CIRCUIT DETAILS ━━━

━━━ Circuit 1 ━━━

? Circuit Description: Lighting - Ground Floor
? Protection Device Standard: BS EN 60898
? Type: B
? Rating (A): 6
? Cable CSA (mm²): 1.5

ℹ  Calculating maximum Zs from BS 7671 tables...
✓ Max Zs for B 6A: 7.67 Ω

? Measured Zs (Ω): 0.89
✓ Pass (0.89 < 7.67)
```

### Example 2: Automated Processing

**measurement_data.json:**
```json
{
  "supply": {
    "measured_ze": 0.35,
    "measured_ipf": 1.2,
    "earthing_arrangement": "TN-S"
  },
  "circuits": [
    {
      "circuit_number": 1,
      "description": "Lighting - Ground Floor",
      "device_standard": "BS EN 60898",
      "device_type": "B",
      "rating": 6,
      "cable_csa": 1.5,
      "measured_zs": 0.89,
      "design_current": 5,
      "cable_length": 15
    }
  ]
}
```

**Process:**
```bash
# Create EICR from measurements
./ecir create --from-data measurement_data.json --output report.json

# Render to PDF
./ecir render report.json --output report.pdf
```

### Example 3: Integration with External Tools

**Python Script:**
```python
from algorithms.integration import ECIRIntegration

# Load measurements from your equipment/software
measurement_data = load_from_equipment()

# Create EICR with automatic calculations
integration = ECIRIntegration.from_measurements(measurement_data)

# Validate all circuits
validation = integration.validate_all_circuits()

# Export
integration.export("report.json")
integration.export("report.pdf", format="pdf")
```

## 📚 Documentation

### Complete Documentation
- **[CLI_USAGE.md](docs/CLI_USAGE.md)** - Comprehensive CLI guide
- **[CALCULATIONS.md](docs/CALCULATIONS.md)** - All calculation algorithms
- **[example_measurements.json](example_measurements.json)** - Example data file

### BS 7671 Tables Included
- **Table 41.2-41.5:** Maximum earth fault loop impedance (Zs)
- **Appendix 4:** Cable current ratings (all reference methods)
- **Appendix 4:** Voltage drop values
- **Table 4B1:** Ambient temperature correction factors
- **Table 4C1:** Grouping correction factors
- **Table 52.2:** Thermal insulation factors

## 🧪 Testing

### Run All Tests
```bash
python -m unittest tests.test_calculations -v
```

**Test Coverage:**
- ✅ BS 7671 table lookups (6 tests)
- ✅ Calculation functions (8 tests)
- ✅ Circuit validation (4 tests)
- **Total: 18 tests - All passing**

### Test Results
```
test_get_max_zs_bs_en_60898_type_b ... ok
test_calculate_voltage_drop ... ok
test_calculate_cable_rating_with_corrections ... ok
test_validate_circuit_pass ... ok
...

Ran 18 tests in 0.003s
OK
```

## 📁 Project Structure

```
ai-cli-sphere/
├── algorithms/
│   ├── bs7671_tables.py        # BS 7671 table lookup class
│   ├── eicr_calculations.py    # All calculation functions
│   └── integration.py          # External algorithm integration API
├── cli/
│   └── eicr_terminal.py        # Interactive terminal interface
├── data/
│   └── bs7671_tables/          # BS 7671 data tables (JSON)
│       ├── max_zs_values.json
│       ├── cable_ratings.json
│       ├── voltage_drop.json
│       └── correction_factors.json
├── docs/
│   ├── CALCULATIONS.md         # Algorithm documentation
│   └── CLI_USAGE.md            # CLI usage guide
├── src/
│   ├── cli.py                  # CLI command definitions
│   └── ecir_template.py        # Template loading/manipulation
├── templates/
│   └── eicr_template.yaml      # Complete EICR structure
├── tests/
│   └── test_calculations.py    # Test suite
├── ecir                        # Wrapper script
├── example_measurements.json   # Example measurement data
└── requirements.txt            # Python dependencies
```

## 🎯 Use Cases

### 1. Electrical Contractors
- Complete EICRs on-site using tablet/laptop
- Quick BS 7671 table lookups during inspections
- Validate circuits before finishing the report

### 2. Testing Equipment Integration
- Import measurements from testing equipment
- Automatic calculation and validation
- Batch process multiple properties

### 3. Training & Education
- Learn BS 7671 calculations interactively
- Understand circuit validation requirements
- Practice EICR completion

### 4. Quality Assurance
- Validate EICR data programmatically
- Ensure all calculations comply with BS 7671
- Automated testing workflows

## ⚙️ Technical Details

### Calculations Implemented

**1. Maximum Zs (Earth Fault Loop Impedance)**
```python
max_zs = calculate_max_zs("BS EN 60898", "B", 6)
# Returns: 7.67 Ω
```

**2. Voltage Drop**
```python
vd = calculate_voltage_drop("thermoplastic_copper", 2.5, 20, 10)
# Returns: 3.6V
```

**3. Cable Current Rating (with correction factors)**
```python
rating = calculate_cable_rating(
    "thermoplastic_70c", 2.5, "C",
    ambient_temp=40, grouping=2, insulation_contact=False
)
# Returns: 17.75A (24A × 0.87 × 0.85)
```

**4. Circuit Validation**
```python
result = validate_circuit(circuit_data)
# Checks: overload, fault protection, voltage drop, cable capacity
```

### Data Format

**Measurement Data JSON:**
```json
{
  "supply": {
    "measured_ze": 0.35,
    "measured_ipf": 1.2,
    "earthing_arrangement": "TN-S"
  },
  "circuits": [
    {
      "circuit_number": 1,
      "description": "Lighting - Ground Floor",
      "device_standard": "BS EN 60898",
      "device_type": "B",
      "rating": 6,
      "cable_csa": 1.5,
      "measured_zs": 0.89
    }
  ]
}
```

## 📄 License

This EICR system is part of the ai-cli-sphere project. See main repository LICENSE for details.

## ⚠️ Important Notes

1. **Compliance:** All calculations are based on BS 7671:2018+A2:2022
2. **Qualified Use:** This tool is for use by qualified electrical engineers with appropriate certifications
3. **Official Forms:** User must have rights to use official EICR forms
4. **Verification:** Always verify critical calculations independently
5. **Standards:** BS 7671 values are based on UK standard voltage (230V)

## 🔧 Development

### Adding New Features

**Add a new BS 7671 table:**
1. Create JSON file in `data/bs7671_tables/`
2. Add lookup method in `algorithms/bs7671_tables.py`
3. Add calculation function in `algorithms/eicr_calculations.py`
4. Add tests in `tests/test_calculations.py`

**Add a new CLI command:**
1. Add command in `src/cli.py`
2. Document in `docs/CLI_USAGE.md`
3. Test manually

### Testing Checklist
- [ ] Run all unit tests
- [ ] Test interactive mode flow
- [ ] Test data-driven mode
- [ ] Test all CLI commands
- [ ] Verify BS 7671 calculations
- [ ] Test PDF rendering

## 📞 Support

For issues, questions, or contributions, please refer to the main repository.

---

**Version:** 1.0  
**Last Updated:** 2026-01-28  
**BS 7671 Edition:** 18th Edition (2018+A2:2022)  
**Status:** ✅ Production Ready
