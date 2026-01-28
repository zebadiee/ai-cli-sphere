"""
EICR Template System
Provides template loading, manipulation, and data management for EICR forms.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class ECIRTemplate:
    """Class for loading and manipulating EICR templates."""
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize EICR template.
        
        Args:
            template_path: Path to EICR template YAML file.
                          If None, uses default templates/eicr_template.yaml
        """
        if template_path is None:
            # Get the directory where this file is located
            current_file = Path(__file__).resolve()
            # Go up one level to the repository root, then to templates
            template_path = current_file.parent.parent / "templates" / "eicr_template.yaml"
        
        self.template_path = Path(template_path)
        self.template_structure = self._load_template()
        self.data = self._initialize_data()
    
    def _load_template(self) -> Dict[str, Any]:
        """Load the EICR template from YAML file."""
        try:
            with open(self.template_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"EICR template not found: {self.template_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in template: {e}")
    
    def _initialize_data(self) -> Dict[str, Any]:
        """Initialize empty data structure based on template."""
        data = {}
        
        if "sections" in self.template_structure:
            for section_name, section_data in self.template_structure["sections"].items():
                data[section_name] = {}
                
                if "fields" in section_data:
                    for field_name, field_config in section_data["fields"].items():
                        field_type = field_config.get("type", "text")
                        
                        if field_type == "table":
                            data[section_name][field_name] = []
                        elif field_type == "boolean":
                            data[section_name][field_name] = None
                        elif field_type == "number":
                            default = field_config.get("default")
                            data[section_name][field_name] = default
                        else:
                            data[section_name][field_name] = None
        
        return data
    
    @classmethod
    def create_new(cls, template_path: Optional[str] = None) -> 'ECIRTemplate':
        """
        Create a new EICR with empty data.
        
        Args:
            template_path: Optional custom template path
        
        Returns:
            New ECIRTemplate instance
        """
        return cls(template_path)
    
    @classmethod
    def load_from_file(cls, filepath: str, template_path: Optional[str] = None) -> 'ECIRTemplate':
        """
        Load EICR data from JSON file.
        
        Args:
            filepath: Path to JSON file containing EICR data
            template_path: Optional custom template path
        
        Returns:
            ECIRTemplate instance with loaded data
        """
        instance = cls(template_path)
        
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
        
        instance.data = loaded_data
        return instance
    
    def set_field(self, field_path: str, value: Any) -> None:
        """
        Set a field value using dot notation path.
        
        Args:
            field_path: Path to field (e.g., "section_e_supply_characteristics.earthing_arrangement")
            value: Value to set
        
        Example:
            >>> eicr.set_field("section_e_supply_characteristics.earthing_arrangement", "TN-S")
        """
        parts = field_path.split(".")
        
        if len(parts) < 2:
            raise ValueError(f"Invalid field path: {field_path}. Must be 'section.field'")
        
        section = parts[0]
        field = ".".join(parts[1:])
        
        if section not in self.data:
            self.data[section] = {}
        
        self.data[section][field] = value
    
    def get_field(self, field_path: str) -> Any:
        """
        Get a field value using dot notation path.
        
        Args:
            field_path: Path to field (e.g., "section_e_supply_characteristics.earthing_arrangement")
        
        Returns:
            Field value or None if not found
        """
        parts = field_path.split(".")
        
        if len(parts) < 2:
            raise ValueError(f"Invalid field path: {field_path}. Must be 'section.field'")
        
        section = parts[0]
        field = ".".join(parts[1:])
        
        if section in self.data and field in self.data[section]:
            return self.data[section][field]
        
        return None
    
    def add_circuit(self, circuit_data: Dict[str, Any]) -> None:
        """
        Add a circuit to the circuit schedule.
        
        Args:
            circuit_data: Dictionary containing circuit data
        
        Example:
            >>> eicr.add_circuit({
            ...     "circuit_number": 1,
            ...     "circuit_description": "Lighting - Ground Floor",
            ...     "type_bs_standard": "BS EN 60898",
            ...     "type": "B",
            ...     "rating": 6,
            ...     "measured_zs": 0.89
            ... })
        """
        if "section_h_circuit_details" not in self.data:
            self.data["section_h_circuit_details"] = {}
        
        if "circuits" not in self.data["section_h_circuit_details"]:
            self.data["section_h_circuit_details"]["circuits"] = []
        
        self.data["section_h_circuit_details"]["circuits"].append(circuit_data)
    
    def add_observation(self, observation_data: Dict[str, Any]) -> None:
        """
        Add an observation to the observations table.
        
        Args:
            observation_data: Dictionary containing observation data
        
        Example:
            >>> eicr.add_observation({
            ...     "item": 1,
            ...     "reference": "Consumer unit",
            ...     "code": "C2",
            ...     "observation": "No RCD protection on socket outlets"
            ... })
        """
        if "section_g_observations" not in self.data:
            self.data["section_g_observations"] = {}
        
        if "observations" not in self.data["section_g_observations"]:
            self.data["section_g_observations"]["observations"] = []
        
        self.data["section_g_observations"]["observations"].append(observation_data)
    
    def export(self, filepath: str, format: str = "json") -> None:
        """
        Export EICR data to file.
        
        Args:
            filepath: Output file path
            format: Output format ("json" or "yaml")
        """
        filepath = Path(filepath)
        
        with open(filepath, 'w') as f:
            if format == "json":
                json.dump(self.data, f, indent=2, default=str)
            elif format == "yaml":
                yaml.dump(self.data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
    
    def render_pdf(self, output_path: str) -> None:
        """
        Render EICR data to PDF format.
        
        Args:
            output_path: Path for output PDF file
        
        Note:
            This is a placeholder for PDF rendering functionality.
            Full implementation would use reportlab or similar library.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=12
        )
        
        # Title
        elements.append(Paragraph("ELECTRICAL INSTALLATION CONDITION REPORT", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Iterate through sections
        for section_name, section_content in self.data.items():
            if not section_content:
                continue
            
            # Get section title from template
            section_title = self.template_structure.get("sections", {}).get(section_name, {}).get("title", section_name)
            elements.append(Paragraph(section_title, heading_style))
            
            # Add fields
            table_data = []
            for field_name, field_value in section_content.items():
                if isinstance(field_value, list):
                    # Handle tables (circuits, observations)
                    if field_value:
                        elements.append(Paragraph(f"{field_name.replace('_', ' ').title()}:", styles['Normal']))
                        
                        # Create table from list of dicts
                        if len(field_value) > 0:
                            headers = list(field_value[0].keys())
                            table_content = [headers]
                            for row in field_value:
                                table_content.append([str(row.get(h, '')) for h in headers])
                            
                            t = Table(table_content)
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 8),
                                ('FONTSIZE', (0, 1), (-1, -1), 7),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            elements.append(t)
                            elements.append(Spacer(1, 0.2 * inch))
                else:
                    field_label = field_name.replace('_', ' ').title()
                    field_val = str(field_value) if field_value is not None else ""
                    table_data.append([field_label, field_val])
            
            if table_data:
                t = Table(table_data, colWidths=[3 * inch, 4 * inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(t)
            
            elements.append(Spacer(1, 0.3 * inch))
        
        # Build PDF
        doc.build(elements)
    
    def get_all_sections(self) -> List[str]:
        """
        Get list of all section names.
        
        Returns:
            List of section names
        """
        return list(self.template_structure.get("sections", {}).keys())
    
    def get_section_fields(self, section_name: str) -> Dict[str, Any]:
        """
        Get field definitions for a section.
        
        Args:
            section_name: Name of the section
        
        Returns:
            Dictionary of field definitions
        """
        sections = self.template_structure.get("sections", {})
        if section_name in sections:
            return sections[section_name].get("fields", {})
        return {}
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate EICR data against template requirements.
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        for section_name, section_data in self.template_structure.get("sections", {}).items():
            fields = section_data.get("fields", {})
            
            for field_name, field_config in fields.items():
                required = field_config.get("required", False)
                value = self.data.get(section_name, {}).get(field_name)
                
                if required and (value is None or value == ""):
                    errors.append(f"{section_name}.{field_name}: Required field is missing")
                
                # Type validation
                field_type = field_config.get("type")
                if value is not None and field_type == "number":
                    if not isinstance(value, (int, float)):
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            errors.append(f"{section_name}.{field_name}: Must be a number")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
