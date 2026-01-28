"""
Terminal-based EICR Interface
Interactive CLI for EICR completion using questionary.
"""

import questionary
from questionary import Style
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from src.ecir_template import ECIRTemplate
from algorithms.eicr_calculations import (
    calculate_max_zs,
    calculate_voltage_drop,
    calculate_cable_rating,
    validate_circuit
)


# Custom style for the terminal interface
custom_style = Style([
    ('qmark', 'fg:#1a5490 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#06989a bold'),
    ('pointer', 'fg:#1a5490 bold'),
    ('highlighted', 'fg:#1a5490 bold'),
    ('selected', 'fg:#06989a'),
    ('separator', 'fg:#6c6c6c'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])


class ECIRTerminalInterface:
    """Interactive terminal interface for EICR completion."""
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize EICR terminal interface.
        
        Args:
            template_path: Optional custom template path
        """
        self.eicr = ECIRTemplate.create_new(template_path)
        self.current_section = 0
        self.draft_dir = Path.home() / ".eicr_drafts"
        self.draft_dir.mkdir(exist_ok=True)
    
    def show_header(self):
        """Display the application header."""
        print("\n" + "=" * 70)
        print("║  ELECTRICAL INSTALLATION CONDITION REPORT".center(70) + "║")
        print("║  Terminal Interface".center(70) + "║")
        print("=" * 70 + "\n")
    
    def show_section_header(self, section_name: str, title: str):
        """Display section header."""
        print("\n" + "─" * 70)
        print(f"  {title}")
        print("─" * 70 + "\n")
    
    def run_interactive(self) -> ECIRTemplate:
        """
        Run the interactive EICR form.
        
        Returns:
            Completed ECIRTemplate instance
        """
        self.show_header()
        
        # Get report number
        report_number = questionary.text(
            "Report Number:",
            default=f"EICR-{datetime.now().strftime('%Y-%m-%d')}",
            style=custom_style
        ).ask()
        
        print(f"\n📋 Report Number: {report_number}\n")
        
        # Section A: Client Details
        self.collect_client_details()
        
        # Section B: Installation Details
        self.collect_installation_details()
        
        # Section C: Extent of Inspection
        self.collect_extent_of_inspection()
        
        # Section D: Summary
        self.collect_summary()
        
        # Section E: Supply Characteristics
        self.collect_supply_characteristics()
        
        # Section F: Particulars of Installation
        self.collect_particulars_of_installation()
        
        # Section G: Observations (optional)
        if questionary.confirm("Add observations?", default=False, style=custom_style).ask():
            self.collect_observations()
        
        # Section H: Circuit Details
        self.collect_circuit_details()
        
        # Section I: Inspector Details
        self.collect_inspector_details()
        
        # Section J: Next Inspection
        self.collect_next_inspection()
        
        # Save draft option
        if questionary.confirm("Save as draft?", default=False, style=custom_style).ask():
            self.save_draft(report_number)
        
        return self.eicr
    
    def collect_client_details(self):
        """Collect Section A: Client Details."""
        self.show_section_header("section_a", "SECTION A: DETAILS OF PERSON ORDERING REPORT")
        
        name = questionary.text("Name:", style=custom_style).ask()
        self.eicr.set_field("section_a_client_details.name", name)
        
        address_line_1 = questionary.text("Address Line 1:", style=custom_style).ask()
        self.eicr.set_field("section_a_client_details.address_line_1", address_line_1)
        
        address_line_2 = questionary.text("Address Line 2 (optional):", default="", style=custom_style).ask()
        if address_line_2:
            self.eicr.set_field("section_a_client_details.address_line_2", address_line_2)
        
        city = questionary.text("City:", style=custom_style).ask()
        self.eicr.set_field("section_a_client_details.city", city)
        
        postcode = questionary.text("Postcode:", style=custom_style).ask()
        self.eicr.set_field("section_a_client_details.postcode", postcode)
        
        telephone = questionary.text("Telephone (optional):", default="", style=custom_style).ask()
        if telephone:
            self.eicr.set_field("section_a_client_details.telephone", telephone)
    
    def collect_installation_details(self):
        """Collect Section B: Installation Details."""
        self.show_section_header("section_b", "SECTION B: DETAILS OF THE INSTALLATION")
        
        occupier = questionary.text("Occupier:", style=custom_style).ask()
        self.eicr.set_field("section_b_installation_details.occupier", occupier)
        
        installation_address = questionary.text("Installation Address:", style=custom_style).ask()
        self.eicr.set_field("section_b_installation_details.installation_address", installation_address)
        
        description = questionary.text("Description of Premises:", style=custom_style).ask()
        self.eicr.set_field("section_b_installation_details.description", description)
        
        if questionary.confirm("Do you know the estimated age?", default=True, style=custom_style).ask():
            estimated_age = questionary.text("Estimated Age (years):", style=custom_style).ask()
            self.eicr.set_field("section_b_installation_details.estimated_age", int(estimated_age))
        
        alterations = questionary.confirm(
            "Evidence of Alterations or Additions?",
            default=False,
            style=custom_style
        ).ask()
        self.eicr.set_field("section_b_installation_details.evidence_of_alterations", alterations)
    
    def collect_extent_of_inspection(self):
        """Collect Section C: Extent and Limitations."""
        self.show_section_header("section_c", "SECTION C: EXTENT AND LIMITATIONS OF INSPECTION")
        
        extent = questionary.text(
            "Extent of Electrical Installation Covered:",
            default="Complete installation",
            style=custom_style
        ).ask()
        self.eicr.set_field("section_c_extent_of_inspection.extent_of_electrical_installation", extent)
        
        limitations = questionary.text(
            "Limitations (if any):",
            default="None",
            style=custom_style
        ).ask()
        self.eicr.set_field("section_c_extent_of_inspection.limitations", limitations)
        
        agreed = questionary.confirm(
            "Agreed with Client?",
            default=True,
            style=custom_style
        ).ask()
        self.eicr.set_field("section_c_extent_of_inspection.agreed_with_client", agreed)
    
    def collect_summary(self):
        """Collect Section D: Summary."""
        self.show_section_header("section_d", "SECTION D: SUMMARY OF THE INSPECTION")
        
        date_of_inspection = questionary.text(
            "Date(s) of Inspection:",
            default=datetime.now().strftime("%Y-%m-%d"),
            style=custom_style
        ).ask()
        self.eicr.set_field("section_d_summary.date_of_inspection", date_of_inspection)
        
        overall = questionary.select(
            "Overall Assessment:",
            choices=["Satisfactory", "Unsatisfactory"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_d_summary.overall_assessment", overall)
    
    def collect_supply_characteristics(self):
        """Collect Section E: Supply Characteristics."""
        self.show_section_header("section_e", "SECTION E: SUPPLY CHARACTERISTICS AND EARTHING ARRANGEMENTS")
        
        earthing = questionary.select(
            "Earthing arrangement:",
            choices=["TN-S", "TN-C-S", "TT", "IT", "TN-C"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_e_supply_characteristics.earthing_arrangement", earthing)
        
        conductors = questionary.select(
            "Number of live conductors:",
            choices=["1-phase, 2-wire", "1-phase, 3-wire", "3-phase, 4-wire"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_e_supply_characteristics.number_of_live_conductors", conductors)
        
        voltage = questionary.text(
            "Nominal voltage U0 (V):",
            default="230",
            style=custom_style
        ).ask()
        self.eicr.set_field("section_e_supply_characteristics.nominal_voltage_u0", float(voltage))
        
        # Prospective fault current
        auto_calc_ipf = questionary.confirm(
            "Auto-calculate prospective fault current from measurements?",
            default=False,
            style=custom_style
        ).ask()
        
        if auto_calc_ipf:
            print("\nℹ  Auto-calculation would require additional measurement data.")
            ipf = questionary.text("Enter measured value (kA):", style=custom_style).ask()
            self.eicr.set_field("section_e_supply_characteristics.prospective_fault_current", float(ipf))
        else:
            ipf = questionary.text("Prospective fault current (kA):", style=custom_style).ask()
            self.eicr.set_field("section_e_supply_characteristics.prospective_fault_current", float(ipf))
        
        # External loop impedance
        ze = questionary.text("External loop impedance Ze (Ω):", style=custom_style).ask()
        self.eicr.set_field("section_e_supply_characteristics.external_loop_impedance", float(ze))
        
        print(f"\n✓ Ze recorded: {ze} Ω")
    
    def collect_particulars_of_installation(self):
        """Collect Section F: Particulars of Installation."""
        self.show_section_header("section_f", "SECTION F: PARTICULARS OF INSTALLATION AT THE ORIGIN")
        
        earthing_means = questionary.select(
            "Means of Earthing:",
            choices=["Supplier's facility", "Installation earth electrode"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_f_particulars_of_installation.means_of_earthing", earthing_means)
        
        conductor_type = questionary.select(
            "Main Protective Conductor:",
            choices=["Copper", "Aluminum", "Steel"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_f_particulars_of_installation.main_protective_conductor", conductor_type)
        
        csa = questionary.text("Main Protective Conductor CSA (mm²):", style=custom_style).ask()
        self.eicr.set_field("section_f_particulars_of_installation.main_protective_conductor_csa", float(csa))
        
        switch_type = questionary.select(
            "Main Switch/Circuit Breaker Type:",
            choices=["BS EN 60947-2", "BS EN 60947-3", "BS 88-3", "Other"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_f_particulars_of_installation.main_switch_type", switch_type)
        
        rating = questionary.text("Main Switch Rating (A):", style=custom_style).ask()
        self.eicr.set_field("section_f_particulars_of_installation.main_switch_rating", float(rating))
    
    def collect_observations(self):
        """Collect Section G: Observations."""
        self.show_section_header("section_g", "SECTION G: OBSERVATIONS AND RECOMMENDATIONS")
        
        item_num = 1
        while True:
            print(f"\nObservation {item_num}:")
            
            reference = questionary.text("Reference/Location:", style=custom_style).ask()
            
            code = questionary.select(
                "Code:",
                choices=["C1", "C2", "C3", "FI"],
                style=custom_style
            ).ask()
            
            observation = questionary.text("Observation:", style=custom_style).ask()
            
            self.eicr.add_observation({
                "item": item_num,
                "reference": reference,
                "code": code,
                "observation": observation
            })
            
            if not questionary.confirm("Add another observation?", default=False, style=custom_style).ask():
                break
            
            item_num += 1
    
    def collect_circuit_details(self):
        """Collect Section H: Circuit Details."""
        self.show_section_header("section_h", "SECTION H: SCHEDULE OF CIRCUIT DETAILS AND TEST RESULTS")
        
        circuit_num = 1
        while True:
            print(f"\n━━━ Circuit {circuit_num} ━━━")
            
            description = questionary.text("Circuit Description:", style=custom_style).ask()
            
            # Protection device
            device_standard = questionary.select(
                "Protection Device Standard:",
                choices=["BS EN 60898", "BS EN 61009", "BS 88-3", "BS 1361"],
                style=custom_style
            ).ask()
            
            if "BS EN" in device_standard:
                device_type = questionary.select(
                    "Type:",
                    choices=["B", "C", "D"],
                    style=custom_style
                ).ask()
            else:
                device_type = "gG"
            
            rating = float(questionary.text("Rating (A):", style=custom_style).ask())
            
            # Cable details
            cable_type_display = questionary.select(
                "Cable Type:",
                choices=["Thermoplastic 70°C", "Thermosetting 90°C"],
                style=custom_style
            ).ask()
            
            ref_method = questionary.select(
                "Reference Method:",
                choices=["A", "B", "C", "D"],
                style=custom_style
            ).ask()
            
            csa = float(questionary.text("Live Conductor CSA (mm²):", style=custom_style).ask())
            cpc_csa = float(questionary.text("CPC CSA (mm²):", style=custom_style).ask())
            
            # Calculate max Zs
            print("\nℹ  Calculating maximum Zs from BS 7671 tables...")
            max_zs = calculate_max_zs(device_standard, device_type, rating)
            
            if max_zs:
                print(f"✓ Max Zs for {device_type} {rating}A: {max_zs} Ω")
            else:
                print("⚠ Could not find max Zs in tables")
                max_zs = None
            
            # Measured values
            measured_zs = float(questionary.text("Measured Zs (Ω):", style=custom_style).ask())
            
            # Validate
            if max_zs and measured_zs <= max_zs:
                print(f"✓ Pass ({measured_zs} < {max_zs})")
                result = "Pass"
            elif max_zs:
                print(f"✗ Fail ({measured_zs} > {max_zs})")
                result = "Fail"
            else:
                result = "N/A"
            
            measured_r1r2 = float(questionary.text("Measured R1+R2 (Ω):", style=custom_style).ask())
            insulation = float(questionary.text("Insulation Resistance (MΩ):", style=custom_style).ask())
            
            polarity = questionary.select(
                "Polarity:",
                choices=["Pass", "Fail"],
                style=custom_style
            ).ask()
            
            # Add circuit
            self.eicr.add_circuit({
                "circuit_number": circuit_num,
                "circuit_description": description,
                "type_bs_standard": device_standard,
                "type": device_type,
                "rating": rating,
                "cable_type": cable_type_display,
                "cable_reference_method": ref_method,
                "cable_csa": csa,
                "cable_cpc_csa": cpc_csa,
                "max_zs": max_zs,
                "measured_zs": measured_zs,
                "measured_r1r2": measured_r1r2,
                "insulation_resistance": insulation,
                "polarity": polarity,
                "result": result
            })
            
            if not questionary.confirm("\n[+] Add another circuit?", default=True, style=custom_style).ask():
                break
            
            circuit_num += 1
    
    def collect_inspector_details(self):
        """Collect Section I: Inspector Details."""
        self.show_section_header("section_i", "SECTION I: DETAILS OF INSPECTOR")
        
        name = questionary.text("Name:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_name", name)
        
        company = questionary.text("Company/Trading Name:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_company", company)
        
        address = questionary.text("Address:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_address", address)
        
        postcode = questionary.text("Postcode:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_postcode", postcode)
        
        qualifications = questionary.text("Qualifications:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_qualifications", qualifications)
        
        signature = questionary.text("Signature:", style=custom_style).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_signature", signature)
        
        date = questionary.text(
            "Date:",
            default=datetime.now().strftime("%Y-%m-%d"),
            style=custom_style
        ).ask()
        self.eicr.set_field("section_i_inspector_details.inspector_date", date)
    
    def collect_next_inspection(self):
        """Collect Section J: Next Inspection."""
        self.show_section_header("section_j", "SECTION J: RECOMMENDATION FOR NEXT INSPECTION")
        
        interval = questionary.select(
            "Recommended Inspection Interval:",
            choices=["1 year", "3 years", "5 years", "10 years"],
            style=custom_style
        ).ask()
        self.eicr.set_field("section_j_next_inspection.next_inspection_interval", interval)
    
    def save_draft(self, report_number: str):
        """Save current progress as draft."""
        draft_file = self.draft_dir / f"{report_number}.json"
        self.eicr.export(str(draft_file))
        print(f"\n✓ Draft saved: {draft_file}")
    
    def load_draft(self, report_number: str) -> bool:
        """Load a draft from file."""
        draft_file = self.draft_dir / f"{report_number}.json"
        
        if draft_file.exists():
            self.eicr = ECIRTemplate.load_from_file(str(draft_file))
            print(f"\n✓ Draft loaded: {draft_file}")
            return True
        else:
            print(f"\n✗ Draft not found: {draft_file}")
            return False


def main():
    """Main entry point for interactive terminal interface."""
    interface = ECIRTerminalInterface()
    eicr = interface.run_interactive()
    
    # Export options
    print("\n" + "=" * 70)
    print("  EXPORT OPTIONS")
    print("=" * 70 + "\n")
    
    if questionary.confirm("Export to JSON?", default=True, style=custom_style).ask():
        filename = questionary.text(
            "Filename:",
            default="eicr_report.json",
            style=custom_style
        ).ask()
        eicr.export(filename)
        print(f"✓ Exported to: {filename}")
    
    if questionary.confirm("Export to PDF?", default=True, style=custom_style).ask():
        filename = questionary.text(
            "Filename:",
            default="eicr_report.pdf",
            style=custom_style
        ).ask()
        eicr.render_pdf(filename)
        print(f"✓ Exported to: {filename}")
    
    print("\n✓ EICR Complete!\n")


if __name__ == "__main__":
    main()
