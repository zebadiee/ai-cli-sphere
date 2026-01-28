"""
EICR CLI Commands
Command-line interface for EICR system.
"""

import click
import json
from pathlib import Path
from typing import Optional

from src.ecir_template import ECIRTemplate
from algorithms.integration import ECIRIntegration
from algorithms.eicr_calculations import (
    calculate_max_zs,
    calculate_voltage_drop,
    calculate_cable_rating,
    validate_circuit
)
from algorithms.bs7671_tables import BS7671Tables


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    EICR - Electrical Installation Condition Report CLI
    
    Terminal-based EICR system with BS 7671 calculation integration.
    """
    pass


@cli.command()
@click.option('--interactive', is_flag=True, help='Interactive terminal form')
@click.option('--from-data', type=click.Path(exists=True), help='Create from JSON data file')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def create(interactive: bool, from_data: Optional[str], output: Optional[str]):
    """Create a new EICR report."""
    
    if interactive:
        # Import and run interactive terminal interface
        from cli.eicr_terminal import ECIRTerminalInterface
        
        click.echo("Starting interactive EICR form...")
        interface = ECIRTerminalInterface()
        eicr = interface.run_interactive()
        
        # Export if output specified
        if output:
            eicr.export(output)
            click.echo(f"✓ EICR exported to: {output}")
    
    elif from_data:
        # Load data from file and create EICR
        click.echo(f"Loading measurement data from: {from_data}")
        
        with open(from_data, 'r') as f:
            measurement_data = json.load(f)
        
        integration = ECIRIntegration.from_measurements(measurement_data)
        
        # Validate all circuits
        validation = integration.validate_all_circuits()
        
        click.echo(f"\n✓ EICR created from measurement data")
        click.echo(f"  Circuits: {len(validation['circuits'])}")
        click.echo(f"  All valid: {validation['all_valid']}")
        
        # Export
        if output:
            integration.export(output)
            click.echo(f"✓ Exported to: {output}")
        else:
            output_path = "eicr_report.json"
            integration.export(output_path)
            click.echo(f"✓ Exported to: {output_path}")
    
    else:
        click.echo("Error: Must specify either --interactive or --from-data")
        click.echo("Usage: ecir create --interactive")
        click.echo("   or: ecir create --from-data measurements.json --output report.json")


@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True), required=True, help='Input JSON file')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def calculate(input: str, output: Optional[str]):
    """Run calculations on existing EICR data."""
    
    click.echo(f"Loading EICR data from: {input}")
    
    with open(input, 'r') as f:
        data = json.load(f)
    
    # Create integration instance and run calculations
    integration = ECIRIntegration()
    integration.load_measurements(data)
    results = integration.run_calculations()
    
    click.echo(f"\n✓ Calculations complete")
    click.echo(f"  Circuits processed: {len(results['calculations'])}")
    
    # Display results
    for calc in results['calculations']:
        circuit_num = calc['circuit_number']
        max_zs = calc['max_zs']
        measured_zs = calc['measured_zs']
        passed = calc['pass']
        
        status = "✓ Pass" if passed else "✗ Fail" if passed is not None else "N/A"
        click.echo(f"  Circuit {circuit_num}: {status} (Zs: {measured_zs}Ω, Max: {max_zs}Ω)")
    
    # Export if output specified
    if output:
        integration.export(output)
        click.echo(f"\n✓ Exported to: {output}")


@cli.command()
@click.option('--device', required=True, help='Device (e.g., "BS EN 60898 Type B 6A")')
@click.option('--zs', type=float, help='Measured Zs (Ω)')
@click.option('--cable', help='Cable specification (e.g., "1.5mm²")')
@click.option('--design-current', type=float, help='Design current (A)')
@click.option('--cable-length', type=float, help='Cable length (m)')
def validate(device: str, zs: Optional[float], cable: Optional[str], 
            design_current: Optional[float], cable_length: Optional[float]):
    """Validate a circuit against BS 7671 requirements."""
    
    # Parse device string (e.g., "BS EN 60898 Type B 6A")
    parts = device.split()
    
    try:
        # Extract device standard, type, and rating
        if "BS EN 60898" in device:
            device_standard = "BS EN 60898"
            device_type = parts[parts.index("Type") + 1] if "Type" in parts else "B"
            rating = float(parts[-1].replace("A", ""))
        elif "BS EN 61009" in device:
            device_standard = "BS EN 61009"
            device_type = parts[parts.index("Type") + 1] if "Type" in parts else "B"
            rating = float(parts[-1].replace("A", ""))
        else:
            click.echo("Error: Unsupported device standard")
            return
        
        # Calculate max Zs
        max_zs = calculate_max_zs(device_standard, device_type, rating)
        
        if max_zs:
            click.echo(f"\n✓ Max Zs for {device_type} {rating}A: {max_zs} Ω")
            
            # Validate measured Zs if provided
            if zs:
                if zs <= max_zs:
                    click.echo(f"✓ Pass: Measured Zs ({zs}Ω) ≤ Max Zs ({max_zs}Ω)")
                else:
                    click.echo(f"✗ Fail: Measured Zs ({zs}Ω) > Max Zs ({max_zs}Ω)")
            
            # Full validation if all parameters provided
            if cable and design_current and cable_length and zs:
                # Parse cable CSA
                csa = float(cable.replace("mm²", "").replace("mm", ""))
                
                circuit_data = {
                    "device_standard": device_standard,
                    "device_type": device_type,
                    "device_rating": rating,
                    "cable_type": "thermoplastic_70c",
                    "cable_csa": csa,
                    "cable_reference_method": "C",
                    "measured_zs": zs,
                    "design_current": design_current,
                    "cable_length": cable_length,
                    "voltage": 230,
                    "circuit_type": "power"
                }
                
                validation_result = validate_circuit(circuit_data)
                
                click.echo(f"\n━━━ Full Circuit Validation ━━━")
                click.echo(f"Overall: {'✓ Pass' if validation_result['valid'] else '✗ Fail'}")
                
                for check, result in validation_result['checks'].items():
                    status = "✓" if result else "✗"
                    click.echo(f"  {status} {check.replace('_', ' ').title()}")
                
                if validation_result['issues']:
                    click.echo(f"\nIssues:")
                    for issue in validation_result['issues']:
                        click.echo(f"  • {issue}")
        else:
            click.echo("Error: Could not find max Zs in BS 7671 tables")
    
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.group()
def lookup():
    """Look up BS 7671 table values."""
    pass


@lookup.command(name='max-zs')
@click.option('--device', required=True, help='Device standard (e.g., "BS EN 60898")')
@click.option('--type', required=True, help='Device type (e.g., "B", "C", "D")')
@click.option('--rating', type=float, required=True, help='Device rating (A)')
def lookup_max_zs(device: str, type: str, rating: float):
    """Look up maximum Zs from BS 7671 tables."""
    
    max_zs = calculate_max_zs(device, type, rating)
    
    if max_zs:
        click.echo(f"\nMax Zs for {device} Type {type} {rating}A:")
        click.echo(f"  {max_zs} Ω")
    else:
        click.echo("Error: Value not found in BS 7671 tables")


@lookup.command(name='cable-rating')
@click.option('--type', required=True, help='Cable type (e.g., "thermoplastic_70c")')
@click.option('--csa', type=float, required=True, help='Cross-sectional area (mm²)')
@click.option('--method', required=True, help='Reference method (A, B, C, or D)')
@click.option('--ambient-temp', type=float, default=30, help='Ambient temperature (°C)')
@click.option('--grouping', type=int, default=1, help='Number of grouped circuits')
def lookup_cable_rating(type: str, csa: float, method: str, ambient_temp: float, grouping: int):
    """Look up cable current rating from BS 7671 Appendix 4."""
    
    rating = calculate_cable_rating(type, csa, method, ambient_temp, grouping, False)
    
    if rating:
        click.echo(f"\nCable Rating for {type} {csa}mm² (Method {method}):")
        click.echo(f"  Base rating: {calculate_cable_rating(type, csa, method, 30, 1, False)}A")
        click.echo(f"  Adjusted rating: {rating}A")
        click.echo(f"  Conditions: {ambient_temp}°C, {grouping} circuit(s)")
    else:
        click.echo("Error: Value not found in BS 7671 tables")


@lookup.command(name='voltage-drop')
@click.option('--type', required=True, help='Cable type (e.g., "thermoplastic_copper")')
@click.option('--csa', type=float, required=True, help='Cross-sectional area (mm²)')
@click.option('--length', type=float, help='Cable length (m)')
@click.option('--current', type=float, help='Load current (A)')
def lookup_voltage_drop(type: str, csa: float, length: Optional[float], current: Optional[float]):
    """Look up voltage drop from BS 7671 Appendix 4."""
    
    tables = BS7671Tables()
    mv_per_amp_per_meter = tables.get_voltage_drop(type, csa)
    
    if mv_per_amp_per_meter:
        click.echo(f"\nVoltage Drop for {type} {csa}mm²:")
        click.echo(f"  {mv_per_amp_per_meter} mV/A/m")
        
        if length and current:
            vd = calculate_voltage_drop(type, csa, length, current)
            if vd:
                vd_percent = (vd / 230) * 100
                click.echo(f"\nFor {length}m at {current}A:")
                click.echo(f"  Voltage drop: {vd:.2f}V ({vd_percent:.1f}%)")
    else:
        click.echo("Error: Value not found in BS 7671 tables")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output PDF file')
def render(input_file: str, output: Optional[str]):
    """Render EICR data to PDF format."""
    
    if not output:
        output = input_file.replace('.json', '.pdf')
    
    click.echo(f"Loading EICR data from: {input_file}")
    eicr = ECIRTemplate.load_from_file(input_file)
    
    click.echo(f"Rendering PDF to: {output}")
    eicr.render_pdf(output)
    
    click.echo("✓ PDF rendered successfully")


@cli.command()
@click.argument('draft_id')
def continue_draft(draft_id: str):
    """Resume working on a draft EICR."""
    
    from cli.eicr_terminal import ECIRTerminalInterface
    
    interface = ECIRTerminalInterface()
    
    if interface.load_draft(draft_id):
        click.echo("Continuing draft...")
        # Continue with the loaded draft
        # (In a full implementation, this would resume at the appropriate section)
    else:
        click.echo("Draft not found")


if __name__ == '__main__':
    cli()
