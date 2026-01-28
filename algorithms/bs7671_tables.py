"""
BS 7671 Tables Data Loader
Provides access to BS 7671:2018+A2:2022 tables for calculations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class BS7671Tables:
    """Class to load and access BS 7671 tables."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the BS 7671 tables loader.
        
        Args:
            data_dir: Directory containing BS 7671 table JSON files.
                     If None, uses default data/bs7671_tables/ directory.
        """
        if data_dir is None:
            # Get the directory where this file is located
            current_file = Path(__file__).resolve()
            # Go up one level to the repository root, then to data/bs7671_tables
            data_dir = current_file.parent.parent / "data" / "bs7671_tables"
        
        self.data_dir = Path(data_dir)
        self._max_zs_data = None
        self._cable_ratings_data = None
        self._voltage_drop_data = None
        self._correction_factors_data = None
        
        # Load all tables
        self._load_tables()
    
    def _load_tables(self):
        """Load all BS 7671 tables from JSON files."""
        self._max_zs_data = self._load_json("max_zs_values.json")
        self._cable_ratings_data = self._load_json("cable_ratings.json")
        self._voltage_drop_data = self._load_json("voltage_drop.json")
        self._correction_factors_data = self._load_json("correction_factors.json")
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load a JSON file from the data directory."""
        filepath = self.data_dir / filename
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"BS 7671 table file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
    
    def get_max_zs(self, device_standard: str, device_type: str, rating: float, 
                   voltage: float = 230) -> Optional[float]:
        """
        Get maximum earth fault loop impedance from BS 7671 tables.
        
        Args:
            device_standard: e.g. "bs_en_60898", "bs_88_3", "bs_1361"
            device_type: e.g. "type_b", "type_c", "type_d", "gg"
            rating: Device rating in amps
            voltage: Nominal voltage (default 230V)
        
        Returns:
            Maximum Zs in ohms, or None if not found
        """
        try:
            # Normalize the device standard
            device_standard = device_standard.lower().replace(" ", "_").replace("-", "_")
            device_type = device_type.lower().replace(" ", "_").replace("-", "_")
            
            # Convert rating to string for JSON lookup
            rating_str = str(int(rating))
            
            # Look up the value
            if device_standard in self._max_zs_data:
                if device_type in self._max_zs_data[device_standard]:
                    if rating_str in self._max_zs_data[device_standard][device_type]:
                        return float(self._max_zs_data[device_standard][device_type][rating_str])
            
            return None
        except (KeyError, ValueError, TypeError):
            return None
    
    def get_base_current_rating(self, cable_type: str, csa: float, 
                                reference_method: str) -> Optional[float]:
        """
        Get base current rating for a cable from BS 7671 Appendix 4.
        
        Args:
            cable_type: e.g. "thermoplastic_70c", "thermosetting_90c"
            csa: Cross-sectional area in mm²
            reference_method: e.g. "reference_method_a", "reference_method_c"
        
        Returns:
            Current rating in amps, or None if not found
        """
        try:
            # Normalize inputs
            cable_type = cable_type.lower().replace(" ", "_").replace("°", "")
            reference_method = reference_method.lower().replace(" ", "_")
            
            # Ensure reference_method has the right format
            if not reference_method.startswith("reference_method_"):
                reference_method = f"reference_method_{reference_method}"
            
            # Convert CSA to string for JSON lookup
            csa_str = str(float(csa))
            
            # Look up the value
            if cable_type in self._cable_ratings_data:
                if reference_method in self._cable_ratings_data[cable_type]:
                    if csa_str in self._cable_ratings_data[cable_type][reference_method]:
                        return float(self._cable_ratings_data[cable_type][reference_method][csa_str])
            
            return None
        except (KeyError, ValueError, TypeError):
            return None
    
    def get_voltage_drop(self, cable_type: str, csa: float, 
                        phase_type: str = "ac_single_phase") -> Optional[float]:
        """
        Get voltage drop per amp per meter from BS 7671 Appendix 4.
        
        Args:
            cable_type: e.g. "thermoplastic_copper", "thermosetting_copper"
            csa: Cross-sectional area in mm²
            phase_type: "ac_single_phase" or "ac_three_phase"
        
        Returns:
            Voltage drop in mV/A/m, or None if not found
        """
        try:
            # Normalize inputs
            cable_type = cable_type.lower().replace(" ", "_")
            phase_type = phase_type.lower().replace(" ", "_")
            
            # Convert CSA to string for JSON lookup
            csa_str = str(float(csa))
            
            # Look up the value
            if cable_type in self._voltage_drop_data:
                if csa_str in self._voltage_drop_data[cable_type]:
                    if phase_type in self._voltage_drop_data[cable_type][csa_str]:
                        return float(self._voltage_drop_data[cable_type][csa_str][phase_type])
            
            return None
        except (KeyError, ValueError, TypeError):
            return None
    
    def get_ambient_temp_factor(self, ambient_temp: float, 
                                cable_type: str = "thermoplastic_70c") -> float:
        """
        Get ambient temperature correction factor from Table 4B1.
        
        Args:
            ambient_temp: Ambient temperature in °C
            cable_type: "thermoplastic_70c" or "thermosetting_90c"
        
        Returns:
            Correction factor (interpolated if necessary)
        """
        try:
            cable_type = cable_type.lower().replace(" ", "_").replace("°", "")
            
            if "ambient_temperature" not in self._correction_factors_data:
                return 1.0
            
            if cable_type not in self._correction_factors_data["ambient_temperature"]:
                return 1.0
            
            temp_factors = self._correction_factors_data["ambient_temperature"][cable_type]
            
            # Convert keys to floats and sort
            temps = sorted([float(t) for t in temp_factors.keys()])
            
            # If exact match, return it
            temp_str = str(int(ambient_temp))
            if temp_str in temp_factors:
                return float(temp_factors[temp_str])
            
            # Otherwise interpolate
            if ambient_temp <= temps[0]:
                return float(temp_factors[str(int(temps[0]))])
            if ambient_temp >= temps[-1]:
                return float(temp_factors[str(int(temps[-1]))])
            
            # Linear interpolation
            for i in range(len(temps) - 1):
                if temps[i] <= ambient_temp <= temps[i + 1]:
                    t1, t2 = temps[i], temps[i + 1]
                    f1 = float(temp_factors[str(int(t1))])
                    f2 = float(temp_factors[str(int(t2))])
                    
                    # Linear interpolation formula
                    factor = f1 + (f2 - f1) * (ambient_temp - t1) / (t2 - t1)
                    return factor
            
            return 1.0
        except (KeyError, ValueError, TypeError):
            return 1.0
    
    def get_grouping_factor(self, num_circuits: int, 
                           reference_method: str = "reference_method_c") -> float:
        """
        Get grouping correction factor from Table 4C1.
        
        Args:
            num_circuits: Number of circuits grouped together
            reference_method: Installation reference method
        
        Returns:
            Correction factor
        """
        try:
            reference_method = reference_method.lower().replace(" ", "_")
            
            # Ensure reference_method has the right format
            if not reference_method.startswith("reference_method_"):
                reference_method = f"reference_method_{reference_method}"
            
            if "grouping" not in self._correction_factors_data:
                return 1.0
            
            if reference_method not in self._correction_factors_data["grouping"]:
                return 1.0
            
            grouping_factors = self._correction_factors_data["grouping"][reference_method]
            
            # Convert num_circuits to string for lookup
            num_str = str(num_circuits)
            if num_str in grouping_factors:
                return float(grouping_factors[num_str])
            
            # If not found, return the last available value
            max_available = max([int(k) for k in grouping_factors.keys()])
            if num_circuits > max_available:
                return float(grouping_factors[str(max_available)])
            
            return 1.0
        except (KeyError, ValueError, TypeError):
            return 1.0
    
    def get_thermal_insulation_factor(self, insulation_type: str) -> float:
        """
        Get thermal insulation correction factor.
        
        Args:
            insulation_type: "touching_one_side", "totally_surrounded", "not_touching"
        
        Returns:
            Correction factor
        """
        try:
            insulation_type = insulation_type.lower().replace(" ", "_")
            
            if "thermal_insulation" not in self._correction_factors_data:
                return 1.0
            
            if insulation_type in self._correction_factors_data["thermal_insulation"]:
                return float(self._correction_factors_data["thermal_insulation"][insulation_type])
            
            return 1.0
        except (KeyError, ValueError, TypeError):
            return 1.0
