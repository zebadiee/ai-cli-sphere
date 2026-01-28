"""
Tests for EICR Calculation Functions
Tests BS 7671 compliant calculations.
"""

import unittest
from algorithms.eicr_calculations import (
    calculate_max_zs,
    calculate_voltage_drop,
    calculate_cable_rating,
    validate_circuit,
    calculate_design_current,
    calculate_r1r2
)
from algorithms.bs7671_tables import BS7671Tables


class TestBS7671Tables(unittest.TestCase):
    """Test BS 7671 table lookups."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tables = BS7671Tables()
    
    def test_get_max_zs_bs_en_60898_type_b(self):
        """Test max Zs lookup for BS EN 60898 Type B MCB."""
        # Test known values from Table 41.3
        self.assertEqual(self.tables.get_max_zs("bs_en_60898", "type_b", 6), 7.67)
        self.assertEqual(self.tables.get_max_zs("bs_en_60898", "type_b", 10), 4.60)
        self.assertEqual(self.tables.get_max_zs("bs_en_60898", "type_b", 32), 1.44)
    
    def test_get_max_zs_bs_en_60898_type_c(self):
        """Test max Zs lookup for BS EN 60898 Type C MCB."""
        self.assertEqual(self.tables.get_max_zs("bs_en_60898", "type_c", 6), 3.83)
        self.assertEqual(self.tables.get_max_zs("bs_en_60898", "type_c", 32), 0.72)
    
    def test_get_cable_rating(self):
        """Test cable current rating lookup."""
        # Test known values for thermoplastic 70°C, method C
        self.assertEqual(self.tables.get_base_current_rating("thermoplastic_70c", 1.5, "reference_method_c"), 17.5)
        self.assertEqual(self.tables.get_base_current_rating("thermoplastic_70c", 2.5, "reference_method_c"), 24)
        self.assertEqual(self.tables.get_base_current_rating("thermoplastic_70c", 4.0, "reference_method_c"), 32)
    
    def test_get_voltage_drop(self):
        """Test voltage drop lookup."""
        # Test known values for thermoplastic copper
        self.assertEqual(self.tables.get_voltage_drop("thermoplastic_copper", 2.5, "ac_single_phase"), 18)
        self.assertEqual(self.tables.get_voltage_drop("thermoplastic_copper", 4.0, "ac_single_phase"), 11)
    
    def test_get_ambient_temp_factor(self):
        """Test ambient temperature correction factor."""
        # Test exact values
        self.assertEqual(self.tables.get_ambient_temp_factor(30, "thermoplastic_70c"), 1.0)
        self.assertEqual(self.tables.get_ambient_temp_factor(40, "thermoplastic_70c"), 0.87)
        
        # Test interpolation
        factor_35 = self.tables.get_ambient_temp_factor(35, "thermoplastic_70c")
        self.assertAlmostEqual(factor_35, 0.94, places=2)
    
    def test_get_grouping_factor(self):
        """Test grouping correction factor."""
        self.assertEqual(self.tables.get_grouping_factor(1, "reference_method_c"), 1.0)
        self.assertEqual(self.tables.get_grouping_factor(2, "reference_method_c"), 0.85)
        self.assertEqual(self.tables.get_grouping_factor(3, "reference_method_c"), 0.79)


class TestCalculations(unittest.TestCase):
    """Test calculation functions."""
    
    def test_calculate_max_zs(self):
        """Test max Zs calculation function."""
        # Test various device types
        self.assertEqual(calculate_max_zs("BS EN 60898", "B", 6), 7.67)
        self.assertEqual(calculate_max_zs("BS EN 60898", "C", 32), 0.72)
        self.assertEqual(calculate_max_zs("BS 88-3", "gG", 16), 1.58)
    
    def test_calculate_voltage_drop(self):
        """Test voltage drop calculation."""
        # Test: 2.5mm² cable, 20m length, 10A load
        # Expected: (18 mV/A/m * 10A * 20m) / 1000 = 3.6V
        vd = calculate_voltage_drop("thermoplastic_copper", 2.5, 20, 10)
        self.assertAlmostEqual(vd, 3.6, places=1)
        
        # Test: 4mm² cable, 15m length, 20A load
        # Expected: (11 mV/A/m * 20A * 15m) / 1000 = 3.3V
        vd = calculate_voltage_drop("thermoplastic_copper", 4.0, 15, 20)
        self.assertAlmostEqual(vd, 3.3, places=1)
    
    def test_calculate_cable_rating_no_corrections(self):
        """Test cable rating with no correction factors."""
        # At 30°C, 1 circuit, no insulation - all factors = 1.0
        rating = calculate_cable_rating("thermoplastic_70c", 2.5, "C", 30, 1, False)
        self.assertEqual(rating, 24.0)
    
    def test_calculate_cable_rating_with_corrections(self):
        """Test cable rating with correction factors."""
        # At 40°C, 2 circuits - apply correction factors
        rating = calculate_cable_rating("thermoplastic_70c", 2.5, "C", 40, 2, False)
        
        # Base: 24A, Ca: 0.87, Cg: 0.85, Ci: 1.0
        # Expected: 24 * 0.87 * 0.85 * 1.0 = 17.748A
        self.assertAlmostEqual(rating, 17.748, places=2)
    
    def test_calculate_cable_rating_with_insulation(self):
        """Test cable rating with thermal insulation."""
        rating = calculate_cable_rating("thermoplastic_70c", 2.5, "C", 30, 1, True)
        
        # Base: 24A, Ca: 1.0, Cg: 1.0, Ci: 0.5
        # Expected: 24 * 1.0 * 1.0 * 0.5 = 12A
        self.assertEqual(rating, 12.0)
    
    def test_calculate_design_current_single_phase(self):
        """Test design current calculation for single phase."""
        # 2300W at 230V, PF=1.0 -> 10A
        current = calculate_design_current(2300, 230, 1.0, 1)
        self.assertAlmostEqual(current, 10.0, places=1)
    
    def test_calculate_design_current_three_phase(self):
        """Test design current calculation for three phase."""
        # 10kW at 400V, PF=0.8, 3-phase
        current = calculate_design_current(10000, 400, 0.8, 3)
        # Expected: 10000 / (1.732 * 400 * 0.8) = 18.03A
        self.assertAlmostEqual(current, 18.03, places=1)
    
    def test_calculate_r1r2(self):
        """Test R1+R2 calculation."""
        # 2.5mm² live, 1.5mm² CPC, 20m length at 20°C
        r1r2 = calculate_r1r2(2.5, 1.5, 20, 20)
        
        # Expected: (0.0178 * 20 / 2.5) + (0.0178 * 20 / 1.5)
        # = 0.1424 + 0.2373 = 0.3797Ω
        self.assertAlmostEqual(r1r2, 0.3797, places=3)


class TestCircuitValidation(unittest.TestCase):
    """Test circuit validation function."""
    
    def test_validate_circuit_pass(self):
        """Test circuit validation for a passing circuit."""
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
        
        # Check that circuit passes all checks
        self.assertTrue(result["valid"], "Circuit should be valid")
        self.assertTrue(result["checks"]["overload_protection"])
        self.assertTrue(result["checks"]["fault_protection"])
        self.assertTrue(result["checks"]["voltage_drop"])
        self.assertTrue(result["checks"]["cable_capacity"])
        self.assertEqual(len(result["issues"]), 0)
    
    def test_validate_circuit_fail_zs(self):
        """Test circuit validation failing on Zs."""
        circuit_data = {
            "device_standard": "BS EN 60898",
            "device_type": "B",
            "device_rating": 6,
            "cable_type": "thermoplastic_70c",
            "cable_csa": 1.5,
            "cable_reference_method": "C",
            "measured_zs": 10.0,  # Too high!
            "design_current": 5,
            "cable_length": 15,
            "voltage": 230,
            "circuit_type": "lighting"
        }
        
        result = validate_circuit(circuit_data)
        
        # Circuit should fail fault protection check
        self.assertFalse(result["valid"])
        self.assertFalse(result["checks"]["fault_protection"])
        self.assertGreater(len(result["issues"]), 0)
        
        # Check that max Zs was calculated
        self.assertIsNotNone(result["calculations"]["max_zs"])
        self.assertEqual(result["calculations"]["max_zs"], 7.67)
    
    def test_validate_circuit_fail_voltage_drop(self):
        """Test circuit validation failing on voltage drop."""
        circuit_data = {
            "device_standard": "BS EN 60898",
            "device_type": "B",
            "device_rating": 32,
            "cable_type": "thermoplastic_70c",
            "cable_csa": 1.5,  # Too small for this distance/current
            "cable_reference_method": "C",
            "measured_zs": 0.5,
            "design_current": 20,
            "cable_length": 50,  # Long distance
            "voltage": 230,
            "circuit_type": "power"
        }
        
        result = validate_circuit(circuit_data)
        
        # Circuit should fail voltage drop check
        self.assertFalse(result["valid"])
        self.assertFalse(result["checks"]["voltage_drop"])
        
        # Voltage drop should be calculated
        self.assertIsNotNone(result["calculations"]["voltage_drop"])
        self.assertGreater(result["calculations"]["voltage_drop"], 11.5)  # > 5% of 230V
    
    def test_validate_circuit_fail_cable_capacity(self):
        """Test circuit validation failing on cable capacity."""
        circuit_data = {
            "device_standard": "BS EN 60898",
            "device_type": "B",
            "device_rating": 32,
            "cable_type": "thermoplastic_70c",
            "cable_csa": 1.5,  # Too small!
            "cable_reference_method": "C",
            "measured_zs": 0.5,
            "design_current": 25,  # Higher than cable capacity
            "cable_length": 10,
            "voltage": 230,
            "circuit_type": "power"
        }
        
        result = validate_circuit(circuit_data)
        
        # Circuit should fail cable capacity check
        self.assertFalse(result["valid"])
        self.assertFalse(result["checks"]["cable_capacity"])
        
        # Cable rating should be calculated (1.5mm² method C = 17.5A)
        self.assertIsNotNone(result["calculations"]["cable_rating"])
        self.assertEqual(result["calculations"]["cable_rating"], 17.5)


if __name__ == '__main__':
    unittest.main()
