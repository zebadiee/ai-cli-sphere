# EICR Calculations Documentation

## Overview

This document describes all calculation algorithms implemented in the EICR system, based on BS 7671:2018+A2:2022 (18th Edition IET Wiring Regulations).

## Table of Contents

1. [Maximum Earth Fault Loop Impedance (Zs)](#maximum-zs)
2. [Voltage Drop](#voltage-drop)
3. [Cable Current Rating](#cable-current-rating)
4. [Circuit Validation](#circuit-validation)
5. [Additional Calculations](#additional-calculations)

---

## Maximum Zs

### Function: `calculate_max_zs()`

Calculates the maximum earth fault loop impedance from BS 7671 tables.

**BS 7671 Reference:** Tables 41.2, 41.3, 41.4, 41.5

**Formula:**
```
Max Zs = U0 / Ia
```

Where:
- `U0` = Nominal voltage to earth (230V)
- `Ia` = Current causing automatic disconnection

**Implementation:**

Values are looked up from pre-populated tables based on:
- Device standard (BS EN 60898, BS EN 61009, BS 88-3, BS 1361)
- Device type (B, C, D for MCBs; gG for fuses)
- Device rating (A)

**Example:**

```python
from algorithms.eicr_calculations import calculate_max_zs

# BS EN 60898 Type B 6A MCB
max_zs = calculate_max_zs("BS EN 60898", "B", 6)
# Returns: 7.67 Ω

# BS EN 60898 Type C 32A MCB
max_zs = calculate_max_zs("BS EN 60898", "C", 32)
# Returns: 0.72 Ω
```

**Validation:**

The measured earth fault loop impedance (Zs) must be less than or equal to the maximum value:

```
Zs (measured) ≤ Zs (max)
```

---

## Voltage Drop

### Function: `calculate_voltage_drop()`

Calculates voltage drop for a circuit based on cable characteristics and load.

**BS 7671 Reference:** Appendix 4, Tables 4D1B-4J4B

**Formula:**
```
Voltage Drop (V) = (mV/A/m × Ib × L) / 1000
```

Where:
- `mV/A/m` = Voltage drop per ampere per meter (from tables)
- `Ib` = Design current (A)
- `L` = Cable length (m)

**Limits:**

- **Lighting circuits:** ≤ 3% of nominal voltage (6.9V at 230V)
- **Other circuits:** ≤ 5% of nominal voltage (11.5V at 230V)

**Implementation:**

```python
from algorithms.eicr_calculations import calculate_voltage_drop

# 2.5mm² thermoplastic copper cable, 20m, 10A load
vd = calculate_voltage_drop(
    cable_type="thermoplastic_copper",
    csa=2.5,
    length=20,
    load_current=10
)
# Returns: 3.6V (18 mV/A/m × 10A × 20m / 1000)

# Check against limit
voltage = 230
vd_percent = (vd / voltage) * 100
# 1.57% - within 3% limit for lighting
```

**Example Values (mV/A/m):**

| CSA (mm²) | Thermoplastic | Thermosetting |
|-----------|---------------|---------------|
| 1.5       | 29            | 29            |
| 2.5       | 18            | 18            |
| 4.0       | 11            | 11            |
| 6.0       | 7.3           | 7.3           |
| 10.0      | 4.4           | 4.4           |

---

## Cable Current Rating

### Function: `calculate_cable_rating()`

Calculates the adjusted current-carrying capacity of a cable.

**BS 7671 Reference:** Appendix 4, Tables 4D1A-4J4A; Tables 4B1, 4B2, 4C1

**Formula:**
```
It = Iz × Ca × Cg × Ci
```

Where:
- `It` = Tabulated current rating (A)
- `Ca` = Ambient temperature correction factor
- `Cg` = Grouping correction factor
- `Ci` = Thermal insulation correction factor
- `Iz` = Effective current-carrying capacity (A)

**Correction Factors:**

### 1. Ambient Temperature (Ca)

**Table 4B1 - 70°C Thermoplastic:**

| Temp (°C) | Factor |
|-----------|--------|
| 25        | 1.06   |
| 30        | 1.00   |
| 35        | 0.94   |
| 40        | 0.87   |
| 45        | 0.79   |
| 50        | 0.71   |

### 2. Grouping (Cg)

**Table 4C1 - Method C (Clipped Direct):**

| Circuits | Factor |
|----------|--------|
| 1        | 1.00   |
| 2        | 0.85   |
| 3        | 0.79   |
| 4        | 0.75   |
| 5        | 0.73   |

### 3. Thermal Insulation (Ci)

| Condition           | Factor |
|---------------------|--------|
| Not touching        | 1.00   |
| Touching one side   | 0.75   |
| Totally surrounded  | 0.50   |

**Implementation:**

```python
from algorithms.eicr_calculations import calculate_cable_rating

# 2.5mm² thermoplastic cable, Method C
# At 40°C, 2 circuits grouped, no insulation
rating = calculate_cable_rating(
    cable_type="thermoplastic_70c",
    csa=2.5,
    reference_method="C",
    ambient_temp=40,
    grouping=2,
    insulation_contact=False
)
# Base rating: 24A
# Adjusted: 24 × 0.87 × 0.85 × 1.0 = 17.75A
```

**Base Current Ratings (Method C, 70°C Thermoplastic):**

| CSA (mm²) | Rating (A) |
|-----------|------------|
| 1.0       | 13.5       |
| 1.5       | 17.5       |
| 2.5       | 24         |
| 4.0       | 32         |
| 6.0       | 41         |
| 10.0      | 57         |
| 16.0      | 76         |

---

## Circuit Validation

### Function: `validate_circuit()`

Performs comprehensive circuit validation against BS 7671 requirements.

**Checks Performed:**

### 1. Overload Protection

```
Iz ≥ In
```

Where:
- `Iz` = Cable current-carrying capacity (adjusted)
- `In` = Nominal current of protective device

### 2. Fault Protection

```
Zs ≤ Zs(max)
```

Where:
- `Zs` = Measured earth fault loop impedance
- `Zs(max)` = Maximum permitted value from tables

### 3. Voltage Drop

```
Voltage drop ≤ 3% (lighting) or 5% (other)
```

### 4. Cable Capacity

```
Iz ≥ Ib
```

Where:
- `Iz` = Cable current-carrying capacity
- `Ib` = Design current of circuit

**Implementation:**

```python
from algorithms.eicr_calculations import validate_circuit

circuit_data = {
    "device_standard": "BS EN 60898",
    "device_type": "B",
    "device_rating": 6,
    "cable_type": "thermoplastic_70c",
    "cable_csa": 1.5,
    "cable_reference_method": "C",
    "measured_zs": 0.89,
    "design_current": 5,
    "cable_length": 15,
    "voltage": 230,
    "circuit_type": "lighting",
    "ambient_temp": 30,
    "grouping": 1,
    "insulation_contact": False
}

result = validate_circuit(circuit_data)

# Result structure:
{
    "valid": True,
    "checks": {
        "overload_protection": True,
        "fault_protection": True,
        "voltage_drop": True,
        "cable_capacity": True
    },
    "issues": [],
    "calculations": {
        "cable_rating": 17.5,
        "max_zs": 7.67,
        "voltage_drop": 2.175,
        "voltage_drop_percent": 0.95
    }
}
```

---

## Additional Calculations

### Design Current

**Function:** `calculate_design_current()`

**Formula (Single Phase):**
```
Ib = P / (U × PF)
```

**Formula (Three Phase):**
```
Ib = P / (√3 × U × PF)
```

Where:
- `Ib` = Design current (A)
- `P` = Load power (W)
- `U` = Voltage (V)
- `PF` = Power factor

**Example:**

```python
from algorithms.eicr_calculations import calculate_design_current

# 2300W load, 230V, PF=1.0
current = calculate_design_current(2300, 230, 1.0, 1)
# Returns: 10.0A
```

### R1+R2 Calculation

**Function:** `calculate_r1r2()`

**Formula:**
```
R1+R2 = (ρ × L / A1) + (ρ × L / A2)
```

Where:
- `ρ` = Resistivity of copper at temperature (Ω·mm²/m)
- `L` = Cable length (m)
- `A1` = Live conductor CSA (mm²)
- `A2` = CPC CSA (mm²)

**Resistivity of copper:**
- At 20°C: 0.0178 Ω·mm²/m
- Temperature coefficient: 0.004 per °C

**Example:**

```python
from algorithms.eicr_calculations import calculate_r1r2

# 2.5mm² live, 1.5mm² CPC, 20m length at 20°C
r1r2 = calculate_r1r2(2.5, 1.5, 20, 20)
# Returns: 0.38Ω
```

---

## Usage in EICR System

### Integration with Terminal Interface

The terminal interface automatically uses these calculations:

```python
from cli.eicr_terminal import ECIRTerminalInterface

interface = ECIRTerminalInterface()
eicr = interface.run_interactive()

# Calculations are performed automatically during circuit entry:
# - Max Zs is looked up when device is specified
# - Measured Zs is compared against max Zs
# - Pass/Fail status is determined
```

### Integration with External Algorithms

External measurement systems can use the integration API:

```python
from algorithms.integration import ECIRIntegration

# Load measurement data
measurement_data = {
    "supply": {
        "measured_ze": 0.35,
        "measured_ipf": 1.2,
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
            "cable_length": 15,
        }
    ]
}

# Create EICR with automatic calculations
integration = ECIRIntegration.from_measurements(measurement_data)

# Validate all circuits
validation = integration.validate_all_circuits()

# Export
integration.export("eicr_report.pdf", format="pdf")
```

---

## References

- BS 7671:2018+A2:2022 - Requirements for Electrical Installations (IET Wiring Regulations, 18th Edition)
- IET Guidance Note 1: Selection & Erection
- IET Guidance Note 6: Protection Against Overcurrent
- IET On-Site Guide (BS 7671:2018+A2:2022)

---

## Notes

1. All calculations comply with BS 7671:2018+A2:2022
2. Values are based on standard UK supply voltage (230V)
3. Correction factors are interpolated when necessary
4. Calculations assume copper conductors unless specified
5. For aluminum conductors, different resistivity values apply

---

**Last Updated:** 2026-01-28  
**Version:** 1.0
