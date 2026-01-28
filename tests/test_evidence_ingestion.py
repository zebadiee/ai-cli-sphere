"""
Tests for Evidence Ingestion

Tests the evidence ingestion pipeline functionality.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion import (
    EvidenceIngestionPipeline,
    ImageProcessor,
    NICEAdapter,
    EvidenceStore,
    EvidenceLinking
)


class TestImageProcessor(unittest.TestCase):
    """Test image processing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = ImageProcessor()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_supported_formats(self):
        """Test that supported formats are defined"""
        self.assertIn("JPEG", self.processor.SUPPORTED_FORMATS)
        self.assertIn("PNG", self.processor.SUPPORTED_FORMATS)
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file"""
        result = self.processor.validate_image("/nonexistent/file.jpg")
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)


class TestNICEAdapter(unittest.TestCase):
    """Test NICE adapter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = NICEAdapter(config={"mock_storage_path": self.temp_dir})
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_mock_mode_enabled(self):
        """Test that mock mode is enabled by default"""
        self.assertTrue(self.adapter.mock_mode)
    
    def test_mock_submit_evidence(self):
        """Test mock evidence submission"""
        result = self.adapter.submit_evidence(
            image_path=None,
            image_data=b"fake image data",
            metadata={"description": "Test evidence"}
        )
        
        self.assertIn("nice_ref", result)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["nice_ref"].startswith("NICE-"))


class TestEvidenceStore(unittest.TestCase):
    """Test evidence store functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EvidenceStore(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_store_and_retrieve_evidence(self):
        """Test storing and retrieving evidence"""
        evidence_record = {
            "evidence_id": "EVD-TEST-001",
            "nice_reference": "NICE-TEST-001",
            "description": "Test evidence",
            "location": "Test location",
            "inspector": "Test inspector",
            "timestamp": "2026-01-28T12:00:00Z"
        }
        
        # Store
        evidence_id = self.store.store_evidence(evidence_record)
        self.assertEqual(evidence_id, "EVD-TEST-001")
        
        # Retrieve
        retrieved = self.store.get_evidence(evidence_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["evidence_id"], evidence_id)
        self.assertEqual(retrieved["description"], "Test evidence")
    
    def test_evidence_exists(self):
        """Test checking if evidence exists"""
        evidence_record = {
            "evidence_id": "EVD-TEST-002",
            "nice_reference": "NICE-TEST-002",
            "description": "Test",
            "timestamp": "2026-01-28T12:00:00Z"
        }
        
        self.assertFalse(self.store.evidence_exists("EVD-TEST-002"))
        
        self.store.store_evidence(evidence_record)
        
        self.assertTrue(self.store.evidence_exists("EVD-TEST-002"))
    
    def test_list_evidence(self):
        """Test listing evidence"""
        # Store multiple records
        for i in range(3):
            evidence_record = {
                "evidence_id": f"EVD-TEST-{i:03d}",
                "nice_reference": f"NICE-TEST-{i:03d}",
                "description": f"Test evidence {i}",
                "inspector": "Inspector A" if i < 2 else "Inspector B",
                "timestamp": f"2026-01-28T12:00:{i:02d}Z"
            }
            self.store.store_evidence(evidence_record)
        
        # List all
        all_evidence = self.store.list_evidence()
        self.assertEqual(len(all_evidence), 3)
        
        # Filter by inspector
        filtered = self.store.list_evidence(filters={"inspector": "Inspector A"})
        self.assertEqual(len(filtered), 2)
    
    def test_storage_stats(self):
        """Test getting storage statistics"""
        # Store some evidence
        evidence_record = {
            "evidence_id": "EVD-TEST-STAT",
            "nice_reference": "NICE-TEST-STAT",
            "description": "Test for stats",
            "timestamp": "2026-01-28T12:00:00Z"
        }
        self.store.store_evidence(evidence_record)
        
        stats = self.store.get_storage_stats()
        
        self.assertIn("evidence_count", stats)
        self.assertIn("total_size_bytes", stats)
        self.assertEqual(stats["evidence_count"], 1)


class TestEvidenceLinking(unittest.TestCase):
    """Test evidence linking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.linking = EvidenceLinking(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_and_retrieve_link(self):
        """Test creating and retrieving evidence links"""
        eicr_id = "EICR-2026-001"
        observation_item = "5.18"
        evidence_ids = ["EVD-TEST-001", "EVD-TEST-002"]
        
        # Create link
        result = self.linking.create_link(
            eicr_id=eicr_id,
            observation_item=observation_item,
            evidence_ids=evidence_ids
        )
        
        self.assertEqual(result["eicr_id"], eicr_id)
        self.assertEqual(result["observation_item"], observation_item)
        self.assertEqual(len(result["evidence_ids"]), 2)
        
        # Retrieve links
        retrieved_ids = self.linking.get_evidence_for_observation(
            eicr_id=eicr_id,
            observation_item=observation_item
        )
        
        self.assertEqual(len(retrieved_ids), 2)
        self.assertIn("EVD-TEST-001", retrieved_ids)
        self.assertIn("EVD-TEST-002", retrieved_ids)
    
    def test_get_observations_for_evidence(self):
        """Test getting observations linked to evidence"""
        eicr_id = "EICR-2026-002"
        evidence_id = "EVD-TEST-003"
        
        # Link to multiple observations
        self.linking.create_link(eicr_id, "5.18", [evidence_id])
        self.linking.create_link(eicr_id, "5.19", [evidence_id])
        
        # Get observations
        observations = self.linking.get_observations_for_evidence(
            eicr_id=eicr_id,
            evidence_id=evidence_id
        )
        
        self.assertEqual(len(observations), 2)
        self.assertIn("5.18", observations)
        self.assertIn("5.19", observations)


class TestEvidenceIngestionPipeline(unittest.TestCase):
    """Test complete evidence ingestion pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = EvidenceIngestionPipeline(
            storage_path=self.temp_dir,
            nice_config={"mock_storage_path": self.temp_dir}
        )
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_evidence_id(self):
        """Test evidence ID generation"""
        evidence_id = self.pipeline._generate_evidence_id()
        self.assertTrue(evidence_id.startswith("EVD-"))
        self.assertEqual(len(evidence_id.split("-")), 3)


if __name__ == '__main__':
    unittest.main()
