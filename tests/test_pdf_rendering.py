"""
Tests for PDF Rendering

Tests the PDF generation functionality for EICR forms.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rendering import generate_eicr_pdf, ECIRPDFRenderer


class TestPDFRendering(unittest.TestCase):
    """Test PDF rendering functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.renderer = ECIRPDFRenderer()
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_blank_template_generation(self):
        """Test generating a blank EICR template"""
        output_path = os.path.join(self.temp_dir, "blank_eicr.pdf")
        
        result = generate_eicr_pdf(
            output_path=output_path,
            template_type="blank"
        )
        
        self.assertEqual(result, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
    
    def test_filled_template_generation(self):
        """Test generating a filled EICR template"""
        output_path = os.path.join(self.temp_dir, "filled_eicr.pdf")
        
        # Sample EICR data
        data = {
            "report_id": "EICR-2026-001",
            "sections": {
                "section_a": {
                    "client_name": "Test Client",
                    "client_address": "123 Test Street",
                    "purpose_of_report": "Periodic inspection"
                },
                "section_c": {
                    "occupier": "Test Occupier",
                    "installation_address": "456 Test Avenue",
                    "type_of_installation": "Domestic",
                    "estimated_age": "10 years"
                },
                "section_e": {
                    "general_condition": "Generally satisfactory with minor issues noted",
                    "overall_assessment": "SATISFACTORY"
                },
                "section_g": {
                    "inspector_name": "John Smith",
                    "inspector_position": "Qualified Electrician",
                    "date_of_inspection": "2026-01-28",
                    "signature": "J. Smith",
                    "next_inspection_date": "2031-01-28"
                }
            }
        }
        
        result = generate_eicr_pdf(
            output_path=output_path,
            template_type="filled",
            data=data
        )
        
        self.assertEqual(result, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
    
    def test_invalid_template_type(self):
        """Test that invalid template type raises error"""
        output_path = os.path.join(self.temp_dir, "test.pdf")
        
        with self.assertRaises(ValueError):
            generate_eicr_pdf(
                output_path=output_path,
                template_type="invalid"
            )
    
    def test_filled_without_data(self):
        """Test that filled template without data raises error"""
        output_path = os.path.join(self.temp_dir, "test.pdf")
        
        with self.assertRaises(ValueError):
            generate_eicr_pdf(
                output_path=output_path,
                template_type="filled",
                data=None
            )
    
    def test_template_with_observations(self):
        """Test template with observations and evidence references"""
        output_path = os.path.join(self.temp_dir, "with_observations.pdf")
        
        data = {
            "report_id": "EICR-2026-002",
            "sections": {
                "section_k": {
                    "observations": [
                        {
                            "item": "5.18",
                            "description": "Damaged socket-outlet observed in kitchen",
                            "classification": "C2",
                            "evidence_refs": [
                                {
                                    "id": "EVD-20260128-ABC123",
                                    "nice_ref": "NICE-20260128-XYZ",
                                    "description": "Photo of damaged socket",
                                    "captured_at": "2026-01-28T14:30:00Z"
                                }
                            ]
                        }
                    ]
                }
            }
        }
        
        result = generate_eicr_pdf(
            output_path=output_path,
            template_type="filled",
            data=data
        )
        
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)


if __name__ == '__main__':
    unittest.main()
