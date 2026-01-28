"""
External Algorithm Integration API
Allows external algorithms and scripts to integrate with the EICR system.
"""

from typing import Dict, Any, List, Optional
from src.ecir_template import ECIRTemplate
from algorithms.eicr_calculations import (
    calculate_max_zs,
    calculate_voltage_drop,
    calculate_cable_rating,
    validate_circuit,
    calculate_design_current,
    calculate_r1r2
)


class ECIRIntegration:
    """
    Integration API for external algorithms to populate EICR data.
    
    This class provides a high-level interface for:
    - Loading measurement data from external sources
    - Running calculations automatically
    - Validating circuits
    - Generating complete EICR reports
    """
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize EICR integration.
        
        Args:
            template_path: Optional custom template path
        """
        self.eicr = ECIRTemplate.create_new(template_path)
    
    @classmethod
    def from_measurements(cls, measurement_data: Dict[str, Any], 
                         template_path: Optional[str] = None) -> 'ECIRIntegration':
        """
        Create EICR from measurement data.
        
        Args:
            measurement_data: Dictionary containing measurement data
            template_path: Optional custom template path
        
        Returns:
            ECIRIntegration instance with populated data
        
        Example:
            >>> data = {
            ...     "supply": {
            ...         "measured_ze": 0.35,
            ...         "measured_ipf": 1.2,
            ...         "earthing_arrangement": "TN-S"
            ...     },
            ...     "circuits": [...]
            ... }
            >>> integration = ECIRIntegration.from_measurements(data)
        """
        instance = cls(template_path)
        instance.load_measurements(measurement_data)
        return instance
    
    def load_measurements(self, measurement_data: Dict[str, Any]) -> None:
        """
        Load measurement data into EICR template.
        
        Args:
            measurement_data: Dictionary containing:
                - supply: Supply characteristics
                - circuits: List of circuit measurements
                - client: Client details (optional)
                - installation: Installation details (optional)
        """
        # Load supply characteristics
        if "supply" in measurement_data:
            supply = measurement_data["supply"]
            section = "section_e_supply_characteristics"
            
            if "measured_ze" in supply:
                self.eicr.set_field(f"{section}.external_loop_impedance", supply["measured_ze"])
            
            if "measured_ipf" in supply:
                self.eicr.set_field(f"{section}.prospective_fault_current", supply["measured_ipf"])
            
            if "earthing_arrangement" in supply:
                self.eicr.set_field(f"{section}.earthing_arrangement", supply["earthing_arrangement"])
            
            if "number_of_live_conductors" in supply:
                self.eicr.set_field(f"{section}.number_of_live_conductors", supply["number_of_live_conductors"])
            
            if "nominal_voltage_u0" in supply:
                self.eicr.set_field(f"{section}.nominal_voltage_u0", supply["nominal_voltage_u0"])
        
        # Load client details
        if "client" in measurement_data:
            client = measurement_data["client"]
            section = "section_a_client_details"
            
            for key, value in client.items():
                self.eicr.set_field(f"{section}.{key}", value)
        
        # Load installation details
        if "installation" in measurement_data:
            installation = measurement_data["installation"]
            section = "section_b_installation_details"
            
            for key, value in installation.items():
                self.eicr.set_field(f"{section}.{key}", value)
        
        # Load circuits
        if "circuits" in measurement_data:
            for circuit in measurement_data["circuits"]:
                self.add_circuit_from_measurements(circuit)
    
    def add_circuit_from_measurements(self, circuit_measurements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a circuit from measurement data with automatic calculations.
        
        Args:
            circuit_measurements: Dictionary containing circuit measurements
        
        Returns:
            Dictionary with circuit data and validation results
        
        Example:
            >>> circuit = {
            ...     "description": "Lighting - Ground Floor",
            ...     "device_standard": "BS EN 60898",
            ...     "device_type": "B",
            ...     "rating": 6,
            ...     "cable_type": "thermoplastic_70c",
            ...     "cable_csa": 1.5,
            ...     "cable_reference_method": "C",
            ...     "measured_zs": 0.89,
            ...     "measured_r1r2": 0.45,
            ...     "insulation_resistance": 250.0
            ... }
            >>> result = integration.add_circuit_from_measurements(circuit)
        """
        # Calculate max Zs
        max_zs = calculate_max_zs(
            circuit_measurements.get("device_standard", "BS EN 60898"),
            circuit_measurements.get("device_type", "B"),
            circuit_measurements.get("rating", 6)
        )
        
        # Prepare circuit data
        circuit_data = {
            "circuit_number": circuit_measurements.get("circuit_number"),
            "circuit_description": circuit_measurements.get("description", ""),
            "type_bs_standard": circuit_measurements.get("device_standard", "BS EN 60898"),
            "type": circuit_measurements.get("device_type", "B"),
            "rating": circuit_measurements.get("rating", 6),
            "cable_type": circuit_measurements.get("cable_type", "Thermoplastic 70°C"),
            "cable_reference_method": circuit_measurements.get("cable_reference_method", "C"),
            "cable_csa": circuit_measurements.get("cable_csa", 1.5),
            "cable_cpc_csa": circuit_measurements.get("cable_cpc_csa", 1.5),
            "max_zs": max_zs,
            "measured_zs": circuit_measurements.get("measured_zs", 0),
            "measured_r1r2": circuit_measurements.get("measured_r1r2", 0),
            "insulation_resistance": circuit_measurements.get("insulation_resistance", 0),
            "polarity": circuit_measurements.get("polarity", "Pass"),
            "rcd_test": circuit_measurements.get("rcd_test"),
        }
        
        # Validate circuit if we have enough data
        validation_result = None
        if all(k in circuit_measurements for k in ["measured_zs", "design_current", "cable_length"]):
            validation_data = {
                "device_standard": circuit_data["type_bs_standard"],
                "device_type": circuit_data["type"],
                "device_rating": circuit_data["rating"],
                "cable_type": circuit_measurements.get("cable_type", "thermoplastic_70c"),
                "cable_csa": circuit_data["cable_csa"],
                "cable_reference_method": circuit_data["cable_reference_method"],
                "measured_zs": circuit_data["measured_zs"],
                "design_current": circuit_measurements["design_current"],
                "cable_length": circuit_measurements["cable_length"],
                "voltage": circuit_measurements.get("voltage", 230),
                "circuit_type": circuit_measurements.get("circuit_type", "power")
            }
            validation_result = validate_circuit(validation_data)
            
            # Set result based on validation
            circuit_data["result"] = "Pass" if validation_result["valid"] else "Fail"
        else:
            # Check basic pass/fail based on Zs only
            if max_zs and circuit_data["measured_zs"] > 0:
                circuit_data["result"] = "Pass" if circuit_data["measured_zs"] <= max_zs else "Fail"
            else:
                circuit_data["result"] = "N/A"
        
        # Add circuit to EICR
        self.eicr.add_circuit(circuit_data)
        
        return {
            "circuit_data": circuit_data,
            "validation": validation_result
        }
    
    def run_calculations(self, circuit_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Run calculations on circuits.
        
        Args:
            circuit_number: If specified, only calculate for this circuit.
                           If None, calculate for all circuits.
        
        Returns:
            Dictionary with calculation results
        """
        results = []
        
        circuits = self.eicr.data.get("section_h_circuit_details", {}).get("circuits", [])
        
        for circuit in circuits:
            if circuit_number is not None and circuit.get("circuit_number") != circuit_number:
                continue
            
            # Recalculate max Zs
            max_zs = calculate_max_zs(
                circuit.get("type_bs_standard", "BS EN 60898"),
                circuit.get("type", "B"),
                circuit.get("rating", 6)
            )
            
            if max_zs:
                circuit["max_zs"] = max_zs
            
            results.append({
                "circuit_number": circuit.get("circuit_number"),
                "max_zs": max_zs,
                "measured_zs": circuit.get("measured_zs"),
                "pass": circuit.get("measured_zs", 0) <= max_zs if max_zs else None
            })
        
        return {"calculations": results}
    
    def validate_all_circuits(self) -> Dict[str, Any]:
        """
        Validate all circuits in the EICR.
        
        Returns:
            Dictionary with validation results for all circuits
        """
        results = []
        
        circuits = self.eicr.data.get("section_h_circuit_details", {}).get("circuits", [])
        
        for circuit in circuits:
            # Basic validation based on max Zs
            max_zs = circuit.get("max_zs")
            measured_zs = circuit.get("measured_zs", 0)
            
            valid = measured_zs <= max_zs if (max_zs and measured_zs > 0) else None
            
            results.append({
                "circuit_number": circuit.get("circuit_number"),
                "description": circuit.get("circuit_description"),
                "valid": valid,
                "max_zs": max_zs,
                "measured_zs": measured_zs
            })
        
        all_valid = all(r["valid"] for r in results if r["valid"] is not None)
        
        return {
            "all_valid": all_valid,
            "circuits": results
        }
    
    def export(self, filepath: str, format: str = "json") -> None:
        """
        Export EICR to file.
        
        Args:
            filepath: Output file path
            format: Output format ("json", "yaml", or "pdf")
        """
        if format == "pdf":
            self.eicr.render_pdf(filepath)
        else:
            self.eicr.export(filepath, format)
    
    def get_eicr(self) -> ECIRTemplate:
        """
        Get the underlying EICR template instance.
        
        Returns:
            ECIRTemplate instance
        """
        return self.eicr


# Example usage function
def example_integration():
    """
    Example of using the integration API with external measurement data.
    """
    # Sample measurement data from external algorithm/survey tool
    survey_data = {
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
            "installation_address": "123 Example Street, London, SW1A 1AA",
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
    
    # Create EICR from measurements
    integration = ECIRIntegration.from_measurements(survey_data)
    
    # Validate all circuits
    validation = integration.validate_all_circuits()
    print(f"All circuits valid: {validation['all_valid']}")
    
    # Export to JSON
    integration.export("filled_eicr.json")
    
    # Export to PDF
    integration.export("filled_eicr.pdf", format="pdf")
    
    return integration


if __name__ == "__main__":
    example_integration()
