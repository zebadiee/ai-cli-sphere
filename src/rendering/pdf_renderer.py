"""
PDF Renderer for EICR Forms

Generates visually accurate PDF documents from EICR data using weasyprint.
Supports both blank templates and filled forms.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

from weasyprint import HTML, CSS

# Get the directory where this file is located
CURRENT_DIR = Path(__file__).parent
TEMPLATES_DIR = CURRENT_DIR / "templates"
STYLES_DIR = CURRENT_DIR / "styles"


class ECIRPDFRenderer:
    """
    Renders EICR forms as PDF documents.
    """
    
    def __init__(self):
        """Initialize the PDF renderer."""
        self.templates_dir = TEMPLATES_DIR
        self.styles_dir = STYLES_DIR
        
    def generate_pdf(
        self,
        output_path: str,
        template_type: str = "blank",
        data: Optional[Dict] = None
    ) -> str:
        """
        Generate a PDF from EICR data.
        
        Args:
            output_path: Path where PDF will be saved
            template_type: Type of template ("blank" or "filled")
            data: EICR data dictionary (required if template_type is "filled")
            
        Returns:
            Path to generated PDF
            
        Raises:
            ValueError: If template_type is invalid or data is missing for filled template
        """
        if template_type not in ["blank", "filled"]:
            raise ValueError(f"Invalid template_type: {template_type}. Must be 'blank' or 'filled'")
        
        if template_type == "filled" and not data:
            raise ValueError("Data is required for filled template")
        
        # Load the HTML template
        html_content = self._load_template(template_type, data)
        
        # Load the CSS styles
        css_content = self._load_styles()
        
        # Generate the PDF
        html = HTML(string=html_content, base_url=str(TEMPLATES_DIR))
        css = CSS(string=css_content)
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        if output_dir and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Render to PDF
        html.write_pdf(output_path, stylesheets=[css])
        
        return output_path
    
    def _load_template(self, template_type: str, data: Optional[Dict]) -> str:
        """
        Load and populate the HTML template.
        
        Args:
            template_type: Type of template
            data: EICR data
            
        Returns:
            HTML content as string
        """
        template_path = self.templates_dir / "eicr_template.html"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        if template_type == "blank":
            # For blank template, replace all variables with empty strings or placeholders
            html_content = self._populate_blank_template(html_content)
        else:
            # For filled template, populate with actual data
            html_content = self._populate_filled_template(html_content, data)
        
        return html_content
    
    def _populate_blank_template(self, html: str) -> str:
        """
        Populate template with blank placeholders.
        
        Args:
            html: HTML template content
            
        Returns:
            HTML with blank placeholders
        """
        # Replace template variables with underlines or empty boxes
        replacements = {
            "{{report_id}}": "_" * 20,
            "{{date_of_inspection}}": "_" * 15,
            "{{client_name}}": "_" * 50,
            "{{client_address}}": "_" * 100,
            "{{purpose_of_report}}": "_" * 50,
            "{{occupier}}": "_" * 50,
            "{{installation_address}}": "_" * 100,
            "{{type_of_installation}}": "_" * 30,
            "{{estimated_age}}": "_" * 20,
            "{{extent_of_inspection}}": "_" * 100,
            "{{percentage_inspected}}": "___",
            "{{general_condition}}": "",
            "{{inspector_name}}": "_" * 50,
            "{{inspector_position}}": "_" * 50,
            "{{signature}}": "_" * 50,
            "{{next_inspection_date}}": "_" * 15,
        }
        
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)
        
        return html
    
    def _populate_filled_template(self, html: str, data: Dict) -> str:
        """
        Populate template with actual data.
        
        Args:
            html: HTML template content
            data: EICR data
            
        Returns:
            HTML populated with data
        """
        # Extract values from data structure
        replacements = {}
        
        # Report metadata
        replacements["{{report_id}}"] = data.get("report_id", "")
        
        # Section A
        section_a = data.get("sections", {}).get("section_a", {})
        replacements["{{client_name}}"] = section_a.get("client_name", "")
        replacements["{{client_address}}"] = section_a.get("client_address", "")
        replacements["{{purpose_of_report}}"] = section_a.get("purpose_of_report", "")
        
        # Section C
        section_c = data.get("sections", {}).get("section_c", {})
        replacements["{{occupier}}"] = section_c.get("occupier", "")
        replacements["{{installation_address}}"] = section_c.get("installation_address", "")
        replacements["{{type_of_installation}}"] = section_c.get("type_of_installation", "")
        replacements["{{estimated_age}}"] = section_c.get("estimated_age", "")
        
        # Section D
        section_d = data.get("sections", {}).get("section_d", {})
        replacements["{{extent_of_inspection}}"] = section_d.get("extent_of_inspection", "")
        replacements["{{percentage_inspected}}"] = str(section_d.get("percentage_inspected", ""))
        
        # Section E
        section_e = data.get("sections", {}).get("section_e", {})
        replacements["{{general_condition}}"] = section_e.get("general_condition", "")
        replacements["{{overall_assessment}}"] = section_e.get("overall_assessment", "")
        
        # Section G
        section_g = data.get("sections", {}).get("section_g", {})
        replacements["{{inspector_name}}"] = section_g.get("inspector_name", "")
        replacements["{{inspector_position}}"] = section_g.get("inspector_position", "")
        replacements["{{date_of_inspection}}"] = section_g.get("date_of_inspection", "")
        replacements["{{signature}}"] = section_g.get("signature", "")
        replacements["{{next_inspection_date}}"] = section_g.get("next_inspection_date", "")
        
        # Apply all replacements
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, str(value))
        
        # Handle arrays (observations, recommendations, etc.)
        html = self._populate_observations(html, data)
        html = self._populate_recommendations(html, data)
        html = self._populate_schedules(html, data)
        
        return html
    
    def _populate_observations(self, html: str, data: Dict) -> str:
        """Populate observations section."""
        section_k = data.get("sections", {}).get("section_k", {})
        observations = section_k.get("observations", [])
        
        if not observations:
            return html
        
        obs_html = ""
        for obs in observations:
            evidence_html = ""
            if obs.get("evidence_refs"):
                evidence_html = "<div class='evidence-refs'><strong>Evidence:</strong><ul>"
                for ev in obs["evidence_refs"]:
                    evidence_html += f"<li>{ev.get('id', '')} (NICE: {ev.get('nice_ref', '')}) - {ev.get('description', '')}</li>"
                evidence_html += "</ul></div>"
            
            obs_html += f"""
            <div class="observation-item">
                <p><strong>Item {obs.get('item', '')}:</strong> {obs.get('description', '')}</p>
                <p><strong>Classification:</strong> {obs.get('classification', '')}</p>
                {evidence_html}
            </div>
            """
        
        html = html.replace("{{observations_list}}", obs_html)
        return html
    
    def _populate_recommendations(self, html: str, data: Dict) -> str:
        """Populate recommendations section."""
        section_f = data.get("sections", {}).get("section_f", {})
        recommendations = section_f.get("recommendations", [])
        
        if not recommendations:
            return html
        
        rec_html = ""
        for rec in recommendations:
            rec_html += f"""
            <div class="recommendation-item">
                <p><strong>{rec.get('code', '')}:</strong> {rec.get('description', '')} (Ref: {rec.get('reference', '')})</p>
            </div>
            """
        
        html = html.replace("{{recommendations_list}}", rec_html)
        return html
    
    def _populate_schedules(self, html: str, data: Dict) -> str:
        """Populate schedule tables."""
        schedules = data.get("schedules", {})
        
        # Circuit details
        circuit_details = schedules.get("circuit_details", [])
        if circuit_details:
            circuit_html = "<table class='schedule-table'><thead><tr>"
            circuit_html += "<th>Circuit</th><th>Type</th><th>Live</th><th>CPC</th><th>Overcurrent</th><th>RCD</th>"
            circuit_html += "</tr></thead><tbody>"
            for circuit in circuit_details:
                circuit_html += "<tr>"
                circuit_html += f"<td>{circuit.get('circuit_designation', '')}</td>"
                circuit_html += f"<td>{circuit.get('circuit_type', '')}</td>"
                circuit_html += f"<td>{circuit.get('live_conductors', '')}</td>"
                circuit_html += f"<td>{circuit.get('cpc_conductors', '')}</td>"
                circuit_html += f"<td>{circuit.get('overcurrent_device', '')}</td>"
                circuit_html += f"<td>{circuit.get('residual_current_device', '')}</td>"
                circuit_html += "</tr>"
            circuit_html += "</tbody></table>"
            html = html.replace("{{circuit_details_table}}", circuit_html)
        
        return html
    
    def _load_styles(self) -> str:
        """
        Load CSS styles.
        
        Returns:
            CSS content as string
        """
        style_path = self.styles_dir / "eicr.css"
        
        if not style_path.exists():
            raise FileNotFoundError(f"Style file not found: {style_path}")
        
        with open(style_path, 'r', encoding='utf-8') as f:
            return f.read()


def generate_eicr_pdf(
    output_path: str,
    template_type: str = "blank",
    data: Optional[Dict] = None
) -> str:
    """
    Convenience function to generate EICR PDF.
    
    Args:
        output_path: Path where PDF will be saved
        template_type: Type of template ("blank" or "filled")
        data: EICR data dictionary (required if template_type is "filled")
        
    Returns:
        Path to generated PDF
    """
    renderer = ECIRPDFRenderer()
    return renderer.generate_pdf(output_path, template_type, data)


# Export main functions
__all__ = ["ECIRPDFRenderer", "generate_eicr_pdf"]
