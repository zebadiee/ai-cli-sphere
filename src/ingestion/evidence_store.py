"""
Evidence Store

Local storage for evidence metadata and thumbnails.
Full images are stored in NICE system; only references stored here.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class EvidenceStore:
    """
    Manages local storage of evidence metadata and thumbnails.
    
    NEVER stores full images - only references, metadata, and thumbnails.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize evidence store.
        
        Args:
            storage_path: Path for local storage (default: ~/.ecir_evidence_store)
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / ".ecir_evidence_store"
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.storage_path / "metadata"
        self.thumbnails_path = self.storage_path / "thumbnails"
        self.links_path = self.storage_path / "links"
        
        self.metadata_path.mkdir(exist_ok=True)
        self.thumbnails_path.mkdir(exist_ok=True)
        self.links_path.mkdir(exist_ok=True)
    
    def store_evidence(self, evidence_record: Dict) -> str:
        """
        Store evidence metadata.
        
        Args:
            evidence_record: Evidence record dictionary
            
        Returns:
            Evidence ID
        """
        evidence_id = evidence_record["evidence_id"]
        
        # Store metadata
        metadata_file = self.metadata_path / f"{evidence_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(evidence_record, f, indent=2)
        
        return evidence_id
    
    def store_thumbnail(self, evidence_id: str, thumbnail_data: bytes) -> str:
        """
        Store evidence thumbnail.
        
        Args:
            evidence_id: Evidence ID
            thumbnail_data: Thumbnail image data
            
        Returns:
            Path to stored thumbnail
        """
        thumbnail_path = self.thumbnails_path / f"{evidence_id}.jpg"
        
        with open(thumbnail_path, 'wb') as f:
            f.write(thumbnail_data)
        
        return str(thumbnail_path)
    
    def get_evidence(self, evidence_id: str) -> Optional[Dict]:
        """
        Retrieve evidence record by ID.
        
        Args:
            evidence_id: Evidence ID
            
        Returns:
            Evidence record or None if not found
        """
        metadata_file = self.metadata_path / f"{evidence_id}.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            return json.load(f)
    
    def evidence_exists(self, evidence_id: str) -> bool:
        """
        Check if evidence exists.
        
        Args:
            evidence_id: Evidence ID
            
        Returns:
            True if exists, False otherwise
        """
        metadata_file = self.metadata_path / f"{evidence_id}.json"
        return metadata_file.exists()
    
    def list_evidence(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List all evidence with optional filters.
        
        Args:
            filters: Dictionary of filters to apply
            
        Returns:
            List of evidence records
        """
        evidence_list = []
        
        for metadata_file in self.metadata_path.glob("*.json"):
            with open(metadata_file, 'r') as f:
                record = json.load(f)
            
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if record.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            evidence_list.append(record)
        
        # Sort by timestamp (newest first)
        evidence_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return evidence_list
    
    def get_thumbnail(self, evidence_id: str) -> Optional[bytes]:
        """
        Retrieve thumbnail for evidence.
        
        Args:
            evidence_id: Evidence ID
            
        Returns:
            Thumbnail data or None if not found
        """
        thumbnail_path = self.thumbnails_path / f"{evidence_id}.jpg"
        
        if not thumbnail_path.exists():
            return None
        
        with open(thumbnail_path, 'rb') as f:
            return f.read()
    
    def delete_evidence(self, evidence_id: str) -> bool:
        """
        Delete evidence record and thumbnail.
        
        Note: This only deletes local metadata and thumbnail.
        Full image in NICE system must be deleted separately.
        
        Args:
            evidence_id: Evidence ID
            
        Returns:
            True if deleted, False if not found
        """
        metadata_file = self.metadata_path / f"{evidence_id}.json"
        thumbnail_file = self.thumbnails_path / f"{evidence_id}.jpg"
        
        deleted = False
        
        if metadata_file.exists():
            metadata_file.unlink()
            deleted = True
        
        if thumbnail_file.exists():
            thumbnail_file.unlink()
            deleted = True
        
        return deleted
    
    def update_evidence(self, evidence_id: str, updates: Dict) -> bool:
        """
        Update evidence metadata.
        
        Args:
            evidence_id: Evidence ID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated, False if not found
        """
        record = self.get_evidence(evidence_id)
        
        if not record:
            return False
        
        # Apply updates
        record.update(updates)
        record["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Save
        self.store_evidence(record)
        
        return True
    
    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        metadata_count = len(list(self.metadata_path.glob("*.json")))
        thumbnail_count = len(list(self.thumbnails_path.glob("*.jpg")))
        
        # Calculate total size
        total_size = 0
        for path in [self.metadata_path, self.thumbnails_path]:
            for file in path.rglob("*"):
                if file.is_file():
                    total_size += file.stat().st_size
        
        return {
            "evidence_count": metadata_count,
            "thumbnail_count": thumbnail_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_path": str(self.storage_path)
        }


# Export main class
__all__ = ["EvidenceStore"]
