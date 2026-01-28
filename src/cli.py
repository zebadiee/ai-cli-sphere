"""
ECIR CLI

Command-line interface for ECIR Studio operations.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click

# Import ECIR modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from rendering import generate_eicr_pdf
from ingestion import EvidenceIngestionPipeline


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    ECIR Studio - Electrical Installation Condition Report System
    
    Provides tools for:
    - PDF generation of EICR forms
    - Evidence ingestion and management
    - Integration with NICE system
    """
    pass


# ============================================================================
# PDF Rendering Commands
# ============================================================================

@cli.group()
def render():
    """PDF rendering commands"""
    pass


@render.command()
@click.option('--template', type=click.Choice(['blank', 'filled']), default='blank',
              help='Template type: blank or filled')
@click.option('--data', type=click.Path(exists=True),
              help='JSON file with EICR data (required for filled template)')
@click.option('--output', '-o', required=True, type=click.Path(),
              help='Output PDF file path')
def generate(template: str, data: Optional[str], output: str):
    """
    Generate EICR PDF.
    
    Examples:
        ecir render generate --template blank --output blank_eicr.pdf
        ecir render generate --template filled --data report.json --output filled_eicr.pdf
    """
    try:
        # Load data if provided
        eicr_data = None
        if data:
            with open(data, 'r') as f:
                eicr_data = json.load(f)
        elif template == 'filled':
            click.echo("Error: --data is required for filled template", err=True)
            sys.exit(1)
        
        # Generate PDF
        click.echo(f"Generating {template} EICR PDF...")
        output_path = generate_eicr_pdf(
            output_path=output,
            template_type=template,
            data=eicr_data
        )
        
        click.echo(f"✓ PDF generated successfully: {output_path}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


# ============================================================================
# Evidence Management Commands
# ============================================================================

@cli.group()
def evidence():
    """Evidence ingestion and management commands"""
    pass


@evidence.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--description', '-d', required=True, help='Description of the evidence')
@click.option('--location', '-l', required=True, help='Location where evidence was captured')
@click.option('--inspector', '-i', required=True, help='Inspector name')
@click.option('--metadata', '-m', type=click.Path(exists=True),
              help='JSON file with additional metadata')
def ingest(image_path: str, description: str, location: str, inspector: str, 
           metadata: Optional[str]):
    """
    Ingest evidence image.
    
    Example:
        ecir evidence ingest photo.jpg -d "Damaged socket" -l "Kitchen" -i "John Smith"
    """
    try:
        # Load additional metadata if provided
        extra_metadata = None
        if metadata:
            with open(metadata, 'r') as f:
                extra_metadata = json.load(f)
        
        # Initialize pipeline
        pipeline = EvidenceIngestionPipeline()
        
        click.echo(f"Ingesting evidence from {image_path}...")
        
        # Ingest the image
        result = pipeline.ingest_image(
            image_path=image_path,
            description=description,
            location=location,
            inspector=inspector,
            metadata=extra_metadata
        )
        
        click.echo("✓ Evidence ingested successfully!")
        click.echo(f"  Evidence ID: {result['evidence_id']}")
        click.echo(f"  NICE Reference: {result['nice_reference']}")
        click.echo(f"  Timestamp: {result['timestamp']}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@evidence.command()
@click.argument('evidence_id')
@click.option('--eicr', required=True, help='EICR report ID')
@click.option('--item', required=True, help='Observation item number (e.g., 5.18)')
def link(evidence_id: str, eicr: str, item: str):
    """
    Link evidence to EICR observation.
    
    Example:
        ecir evidence link EVD-20260128-ABC123 --eicr EICR-2026-001 --item 5.18
    """
    try:
        pipeline = EvidenceIngestionPipeline()
        
        click.echo(f"Linking evidence {evidence_id} to {eicr} item {item}...")
        
        result = pipeline.link_evidence(
            eicr_id=eicr,
            observation_item=item,
            evidence_ids=[evidence_id]
        )
        
        click.echo("✓ Evidence linked successfully!")
        click.echo(f"  EICR: {result['eicr_id']}")
        click.echo(f"  Observation: {result['observation_item']}")
        click.echo(f"  Evidence IDs: {', '.join(result['evidence_ids'])}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@evidence.command()
@click.option('--eicr', help='Filter by EICR ID')
@click.option('--inspector', help='Filter by inspector name')
@click.option('--location', help='Filter by location')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list(eicr: Optional[str], inspector: Optional[str], location: Optional[str],
         output_format: str):
    """
    List evidence records.
    
    Example:
        ecir evidence list --eicr EICR-2026-001
        ecir evidence list --inspector "John Smith" --format json
    """
    try:
        pipeline = EvidenceIngestionPipeline()
        
        # Get evidence list
        evidence_list = pipeline.list_evidence(
            eicr_id=eicr,
            inspector=inspector,
            location=location
        )
        
        if not evidence_list:
            click.echo("No evidence found.")
            return
        
        if output_format == 'json':
            click.echo(json.dumps(evidence_list, indent=2))
        else:
            # Table format
            click.echo(f"\nFound {len(evidence_list)} evidence record(s):\n")
            for ev in evidence_list:
                click.echo(f"ID: {ev['evidence_id']}")
                click.echo(f"  NICE Ref: {ev['nice_reference']}")
                click.echo(f"  Description: {ev['description']}")
                click.echo(f"  Location: {ev['location']}")
                click.echo(f"  Inspector: {ev['inspector']}")
                click.echo(f"  Timestamp: {ev['timestamp']}")
                click.echo()
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@evidence.command()
@click.argument('evidence_id')
def info(evidence_id: str):
    """
    Get detailed information about evidence.
    
    Example:
        ecir evidence info EVD-20260128-ABC123
    """
    try:
        pipeline = EvidenceIngestionPipeline()
        
        record = pipeline.get_evidence(evidence_id)
        
        if not record:
            click.echo(f"Evidence not found: {evidence_id}", err=True)
            sys.exit(1)
        
        click.echo(json.dumps(record, indent=2))
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    cli()
