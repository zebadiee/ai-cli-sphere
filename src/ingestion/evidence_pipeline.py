"""
Evidence Ingestion Pipeline

Orchestrates the complete evidence ingestion workflow:
Image Upload → Validation → NICE Processing → Storage → Linking → ECIR Reference
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .image_processor import ImageProcessor
from .nice_adapter import NICEAdapter
from .evidence_store import EvidenceStore
from .linking import EvidenceLinking


class EvidenceIngestionPipeline:
    """
    Main orchestrator for evidence ingestion and management.
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        nice_config: Optional[Dict] = None
    ):
        """
        Initialize the evidence ingestion pipeline.
        
        Args:
            storage_path: Path for local evidence storage
            nice_config: Configuration for NICE system integration
        """
        self.image_processor = ImageProcessor()
        self.nice_adapter = NICEAdapter(config=nice_config)
        self.evidence_store = EvidenceStore(storage_path=storage_path)
        self.linking = EvidenceLinking()
    
    def ingest_image(
        self,
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        description: str = "",
        location: str = "",
        inspector: str = "",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a single evidence image.
        
        Args:
            image_path: Path to image file (if uploading from file system)
            image_data: Raw image data (if uploading from bytes)
            description: Description of the evidence
            location: Location where evidence was captured
            inspector: Name of the inspector
            metadata: Additional metadata
            
        Returns:
            Evidence record with ID and NICE reference
            
        Raises:
            ValueError: If neither image_path nor image_data provided
            ValidationError: If image validation fails
        """
        if not image_path and not image_data:
            raise ValueError("Either image_path or image_data must be provided")
        
        # Step 1: Validate the image
        if image_path:
            validation_result = self.image_processor.validate_image(image_path)
        else:
            validation_result = self.image_processor.validate_image_data(image_data)
        
        if not validation_result["valid"]:
            raise ValueError(f"Image validation failed: {validation_result['errors']}")
        
        # Step 2: Process the image (extract metadata, create thumbnail)
        if image_path:
            processed = self.image_processor.process_image(image_path)
        else:
            processed = self.image_processor.process_image_data(image_data)
        
        # Step 3: Submit to NICE system
        nice_metadata = {
            "description": description,
            "location": location,
            "inspector": inspector,
            "image_metadata": processed["metadata"],
            **(metadata or {})
        }
        
        nice_result = self.nice_adapter.submit_evidence(
            image_path=image_path,
            image_data=image_data,
            metadata=nice_metadata
        )
        
        # Step 4: Store evidence locally (thumbnail and metadata only)
        evidence_id = self._generate_evidence_id()
        
        evidence_record = {
            "evidence_id": evidence_id,
            "nice_reference": nice_result["nice_ref"],
            "description": description,
            "location": location,
            "inspector": inspector,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": processed["metadata"],
            "storage_path": nice_result["storage_path"],
            "thumbnail_path": None,  # Will be set by store
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        
        # Store thumbnail locally for quick access
        if processed.get("thumbnail"):
            thumbnail_path = self.evidence_store.store_thumbnail(
                evidence_id=evidence_id,
                thumbnail_data=processed["thumbnail"]
            )
            evidence_record["thumbnail_path"] = thumbnail_path
        
        # Store evidence record
        self.evidence_store.store_evidence(evidence_record)
        
        return evidence_record
    
    def ingest_batch(
        self,
        images: List[Dict],
        batch_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Ingest multiple images as a batch.
        
        Args:
            images: List of image dictionaries with paths/data and metadata
            batch_metadata: Metadata to apply to all images in batch
            
        Returns:
            List of evidence records
        """
        results = []
        batch_id = self._generate_batch_id()
        
        for i, image_info in enumerate(images):
            try:
                # Merge batch metadata with individual metadata
                combined_metadata = {
                    "batch_id": batch_id,
                    "batch_index": i,
                    **(batch_metadata or {}),
                    **(image_info.get("metadata", {}))
                }
                
                result = self.ingest_image(
                    image_path=image_info.get("path"),
                    image_data=image_info.get("data"),
                    description=image_info.get("description", ""),
                    location=image_info.get("location", ""),
                    inspector=image_info.get("inspector", ""),
                    metadata=combined_metadata
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "image_index": i,
                    "image_info": image_info
                })
        
        return results
    
    def link_evidence(
        self,
        eicr_id: str,
        observation_item: str,
        evidence_ids: List[str]
    ) -> Dict:
        """
        Link evidence to an EICR observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number (e.g., "5.18")
            evidence_ids: List of evidence IDs to link
            
        Returns:
            Linking result
        """
        # Validate evidence exists
        for evidence_id in evidence_ids:
            if not self.evidence_store.evidence_exists(evidence_id):
                raise ValueError(f"Evidence not found: {evidence_id}")
        
        # Create the link
        link_result = self.linking.create_link(
            eicr_id=eicr_id,
            observation_item=observation_item,
            evidence_ids=evidence_ids
        )
        
        return link_result
    
    def get_evidence(self, evidence_id: str) -> Optional[Dict]:
        """
        Retrieve evidence record by ID.
        
        Args:
            evidence_id: Evidence ID
            
        Returns:
            Evidence record or None if not found
        """
        return self.evidence_store.get_evidence(evidence_id)
    
    def list_evidence(
        self,
        eicr_id: Optional[str] = None,
        inspector: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict]:
        """
        List evidence records with optional filters.
        
        Args:
            eicr_id: Filter by EICR ID
            inspector: Filter by inspector name
            location: Filter by location
            
        Returns:
            List of evidence records
        """
        filters = {}
        if eicr_id:
            filters["eicr_id"] = eicr_id
        if inspector:
            filters["inspector"] = inspector
        if location:
            filters["location"] = location
        
        return self.evidence_store.list_evidence(filters=filters)
    
    def get_evidence_for_observation(
        self,
        eicr_id: str,
        observation_item: str
    ) -> List[Dict]:
        """
        Get all evidence linked to a specific observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number
            
        Returns:
            List of evidence records
        """
        # Get linked evidence IDs
        linked_ids = self.linking.get_evidence_for_observation(
            eicr_id=eicr_id,
            observation_item=observation_item
        )
        
        # Retrieve evidence records
        evidence_records = []
        for evidence_id in linked_ids:
            record = self.get_evidence(evidence_id)
            if record:
                evidence_records.append(record)
        
        return evidence_records
    
    def _generate_evidence_id(self) -> str:
        """Generate a unique evidence ID."""
        from datetime import datetime
        import uuid
        
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        
        return f"EVD-{timestamp}-{unique_id}"
    
    def _generate_batch_id(self) -> str:
        """Generate a unique batch ID."""
        from datetime import datetime
        import uuid
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:6].upper()
        
        return f"BATCH-{timestamp}-{unique_id}"


# Export main class
__all__ = ["EvidenceIngestionPipeline"]
