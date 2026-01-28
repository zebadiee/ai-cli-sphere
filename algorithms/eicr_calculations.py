"""
EICR Calculation Algorithms
Implements BS 7671:2018+A2:2022 compliant calculations.
"""

from typing import Dict, Any, List, Optional
from algorithms.bs7671_tables import BS7671Tables


# Initialize BS 7671 tables
tables = BS7671Tables()


def calculate_max_zs(device_standard: str, device_type: str, rating: float, 
                     voltage: float = 230) -> Optional[float]:
    """
    Calculate maximum earth fault loop impedance from BS 7671 tables.
    
    Args:
        device_standard: e.g. "BS EN 60898", "BS 88-3", "BS 1361"
        device_type: e.g. "B", "C", "D", "gG"
        rating: Device rating in amps
        voltage: Nominal voltage (default 230V)
    
    Returns:
        Maximum Zs in ohms, or None if not found
    
    Example:
        >>> calculate_max_zs("BS EN 60898", "B", 6)
        7.67
    """
    return tables.get_max_zs(device_standard, device_type, rating, voltage)


def calculate_voltage_drop(
    cable_type: str,
    csa: float,
    length: float,
    load_current: float,
    power_factor: float = 1.0,
    phase_type: str = "ac_single_phase"
) -> Optional[float]:
    """
    Calculate voltage drop for a circuit.
    
    Args:
        cable_type: e.g. "thermoplastic_copper", "thermosetting_copper"
        csa: Cross-sectional area in mm²
        length: Cable length in meters
        load_current: Design current in amps
        power_factor: Power factor (default 1.0)
        phase_type: "ac_single_phase" or "ac_three_phase"
    
    Returns:
        Voltage drop in volts, or None if not found
    
    Example:
        >>> calculate_voltage_drop("thermoplastic_copper", 2.5, 20, 10)
        3.6  # (18 mV/A/m * 10A * 20m) / 1000
    """
    mv_per_amp_per_meter = tables.get_voltage_drop(cable_type, csa, phase_type)
    if mv_per_amp_per_meter is None:
        return None
    
    # Calculate voltage drop: (mV/A/m * A * m) / 1000 = V
    voltage_drop = (mv_per_amp_per_meter * load_current * length) / 1000
    
    # Apply power factor if not unity (for more accurate calculations)
    # For simplicity, we'll use the basic formula as power factor is typically
    # accounted for in the tabulated values for AC circuits
    
    return voltage_drop


def calculate_cable_rating(
    cable_type: str,
    csa: float,
    reference_method: str,
    ambient_temp: float = 30,
    grouping: int = 1,
    insulation_contact: bool = False
) -> Optional[float]:
    """
    Calculate adjusted cable current-carrying capacity.
    
    Args:
        cable_type: e.g. "thermoplastic_70c", "thermosetting_90c"
        csa: Cross-sectional area in mm²
        reference_method: e.g. "A", "B", "C", "D"
        ambient_temp: Ambient temperature in °C (default 30)
        grouping: Number of circuits grouped together (default 1)
        insulation_contact: Cable in thermal insulation (default False)
    
    Returns:
        Current rating in amps, or None if not found
    
    Example:
        >>> calculate_cable_rating("thermoplastic_70c", 2.5, "C", 30, 1, False)
        24.0
    """
    base_rating = tables.get_base_current_rating(cable_type, csa, reference_method)
    if base_rating is None:
        return None
    
    # Apply correction factors
    ca = tables.get_ambient_temp_factor(ambient_temp, cable_type)
    cg = tables.get_grouping_factor(grouping, f"reference_method_{reference_method.lower()}")
    
    # Thermal insulation factor
    if insulation_contact:
        ci = tables.get_thermal_insulation_factor("totally_surrounded")
    else:
        ci = 1.0
    
    # Calculate adjusted rating
    adjusted_rating = base_rating * ca * cg * ci
    
    return adjusted_rating


def validate_circuit(circuit_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a complete circuit against BS 7671 requirements.
    
    Args:
        circuit_data: Dictionary containing circuit parameters:
            - device_standard: str (e.g. "BS EN 60898")
            - device_type: str (e.g. "B")
            - device_rating: float (A)
            - cable_type: str (e.g. "thermoplastic_70c")
            - cable_csa: float (mm²)
            - cable_reference_method: str (e.g. "C")
            - measured_zs: float (Ω)
            - design_current: float (A)
            - cable_length: float (m)
            - voltage: float (V, default 230)
            - circuit_type: str (e.g. "lighting" or "power")
            - ambient_temp: float (°C, default 30)
            - grouping: int (default 1)
            - insulation_contact: bool (default False)
    
    Returns:
        Dictionary with validation results:
            {
                "valid": bool,
                "checks": {
                    "overload_protection": bool,
                    "fault_protection": bool,
                    "voltage_drop": bool,
                    "cable_capacity": bool
                },
                "issues": [str],
                "calculations": {
                    "cable_rating": float,
                    "max_zs": float,
                    "voltage_drop": float,
                    "voltage_drop_percent": float
                }
            }
    
    Example:
        >>> circuit = {
        ...     "device_standard": "BS EN 60898",
        ...     "device_type": "B",
        ...     "device_rating": 6,
        ...     "cable_type": "thermoplastic_70c",
        ...     "cable_csa": 1.5,
        ...     "cable_reference_method": "C",
        ...     "measured_zs": 0.89,
        ...     "design_current": 5,
        ...     "cable_length": 15,
        ...     "voltage": 230,
        ...     "circuit_type": "lighting"
        ... }
        >>> result = validate_circuit(circuit)
        >>> result["valid"]
        True
    """
    issues = []
    checks = {}
    calculations = {}
    
    # Extract parameters with defaults
    device_standard = circuit_data.get("device_standard", "BS EN 60898")
    device_type = circuit_data.get("device_type", "B")
    device_rating = circuit_data.get("device_rating", 6)
    cable_type = circuit_data.get("cable_type", "thermoplastic_70c")
    cable_csa = circuit_data.get("cable_csa", 1.5)
    cable_reference_method = circuit_data.get("cable_reference_method", "C")
    measured_zs = circuit_data.get("measured_zs", 0)
    design_current = circuit_data.get("design_current", 0)
    cable_length = circuit_data.get("cable_length", 0)
    voltage = circuit_data.get("voltage", 230)
    circuit_type = circuit_data.get("circuit_type", "power")
    ambient_temp = circuit_data.get("ambient_temp", 30)
    grouping = circuit_data.get("grouping", 1)
    insulation_contact = circuit_data.get("insulation_contact", False)
    
    # Check 1: Cable rating calculation
    cable_rating = calculate_cable_rating(
        cable_type, cable_csa, cable_reference_method,
        ambient_temp, grouping, insulation_contact
    )
    calculations["cable_rating"] = cable_rating
    
    if cable_rating is not None:
        # Check overload protection (cable rating >= device rating)
        checks["overload_protection"] = cable_rating >= device_rating
        if not checks["overload_protection"]:
            issues.append(f"Cable rating ({cable_rating:.1f}A) < device rating ({device_rating}A)")
        
        # Check cable capacity (cable rating >= design current)
        checks["cable_capacity"] = cable_rating >= design_current
        if not checks["cable_capacity"]:
            issues.append(f"Cable capacity ({cable_rating:.1f}A) insufficient for design current ({design_current}A)")
    else:
        checks["overload_protection"] = False
        checks["cable_capacity"] = False
        issues.append("Could not determine cable rating from tables")
    
    # Check 2: Fault protection (Zs <= max Zs)
    max_zs = calculate_max_zs(device_standard, device_type, device_rating, voltage)
    calculations["max_zs"] = max_zs
    
    if max_zs is not None and measured_zs > 0:
        checks["fault_protection"] = measured_zs <= max_zs
        if not checks["fault_protection"]:
            issues.append(f"Zs ({measured_zs}Ω) > max ({max_zs}Ω) - fault protection inadequate")
    else:
        checks["fault_protection"] = False
        if max_zs is None:
            issues.append("Could not determine max Zs from tables")
        if measured_zs <= 0:
            issues.append("No measured Zs value provided")
    
    # Check 3: Voltage drop (< 3% for lighting, < 5% for other)
    if cable_length > 0 and design_current > 0:
        # Determine cable type for voltage drop calculation
        vd_cable_type = "thermoplastic_copper"
        if "thermosetting" in cable_type.lower():
            vd_cable_type = "thermosetting_copper"
        
        vd = calculate_voltage_drop(vd_cable_type, cable_csa, cable_length, design_current)
        calculations["voltage_drop"] = vd
        
        if vd is not None:
            vd_percent = (vd / voltage) * 100
            calculations["voltage_drop_percent"] = vd_percent
            
            max_vd_percent = 3 if circuit_type.lower() == "lighting" else 5
            checks["voltage_drop"] = vd_percent <= max_vd_percent
            
            if not checks["voltage_drop"]:
                issues.append(
                    f"Voltage drop ({vd:.2f}V, {vd_percent:.1f}%) exceeds {max_vd_percent}% limit "
                    f"({voltage * max_vd_percent / 100:.1f}V)"
                )
        else:
            checks["voltage_drop"] = False
            issues.append("Could not calculate voltage drop from tables")
    else:
        checks["voltage_drop"] = True  # Skip check if no data
        calculations["voltage_drop"] = None
        calculations["voltage_drop_percent"] = None
    
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "issues": issues,
        "calculations": calculations
    }


def calculate_design_current(load_power: float, voltage: float = 230, 
                            power_factor: float = 1.0, phases: int = 1) -> float:
    """
    Calculate design current from load power.
    
    Args:
        load_power: Load power in watts
        voltage: Supply voltage (default 230V)
        power_factor: Power factor (default 1.0)
        phases: Number of phases (1 or 3, default 1)
    
    Returns:
        Design current in amps
    
    Example:
        >>> calculate_design_current(2300, 230, 1.0, 1)
        10.0
    """
    if phases == 1:
        # Single phase: I = P / (V * PF)
        return load_power / (voltage * power_factor)
    elif phases == 3:
        # Three phase: I = P / (√3 * V * PF)
        return load_power / (1.732 * voltage * power_factor)
    else:
        raise ValueError("Phases must be 1 or 3")


def calculate_r1r2(csa_live: float, csa_cpc: float, length: float, 
                   temp: float = 20) -> float:
    """
    Calculate R1+R2 (live conductor + CPC resistance).
    
    Args:
        csa_live: Cross-sectional area of live conductor in mm²
        csa_cpc: Cross-sectional area of CPC in mm²
        length: Cable length in meters
        temp: Temperature in °C (default 20°C)
    
    Returns:
        R1+R2 in ohms
    
    Example:
        >>> calculate_r1r2(2.5, 1.5, 20, 20)
        0.254  # Approximate value
    """
    # Resistivity of copper at 20°C: 0.0178 Ω·mm²/m
    resistivity_20c = 0.0178
    
    # Temperature coefficient of copper: 0.004 per °C
    temp_coeff = 0.004
    
    # Adjust resistivity for temperature
    resistivity = resistivity_20c * (1 + temp_coeff * (temp - 20))
    
    # Calculate resistance of live conductor (R1)
    r1 = (resistivity * length) / csa_live
    
    # Calculate resistance of CPC (R2)
    r2 = (resistivity * length) / csa_cpc
    
    return r1 + r2
