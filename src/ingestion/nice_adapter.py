"""
NICE System Adapter

Integrates with the NICE evidence management system.
Provides a mock implementation for testing when NICE is unavailable.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from shutil import copy2
    SHUTIL_AVAILABLE = True
except ImportError:
    SHUTIL_AVAILABLE = False


class NICEAdapter:
    """
    Adapter for NICE evidence management system.
    
    Uses mock implementation by default for testing.
    Configure with real NICE API credentials for production.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize NICE adapter.
        
        Args:
            config: Configuration dictionary with NICE API settings
                    If None, uses mock mode
        """
        self.config = config or {}
        self.mock_mode = not self.config.get("api_url")
        
        if self.mock_mode:
            # Use mock storage
            self.mock_storage_path = Path(self.config.get("mock_storage_path", "/tmp/nice_mock_storage"))
            self.mock_storage_path.mkdir(parents=True, exist_ok=True)
    
    def submit_evidence(
        self,
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Submit evidence to NICE system.
        
        Args:
            image_path: Path to image file
            image_data: Raw image data
            metadata: Evidence metadata
            
        Returns:
            NICE submission result with reference ID
        """
        if self.mock_mode:
            return self._mock_submit_evidence(image_path, image_data, metadata)
        else:
            return self._real_submit_evidence(image_path, image_data, metadata)
    
    def get_evidence_status(self, nice_ref: str) -> Dict:
        """
        Check processing status in NICE.
        
        Args:
            nice_ref: NICE reference ID
            
        Returns:
            Status information
        """
        if self.mock_mode:
            return self._mock_get_status(nice_ref)
        else:
            return self._real_get_status(nice_ref)
    
    def retrieve_evidence(self, nice_ref: str) -> Dict:
        """
        Retrieve evidence from NICE by reference.
        
        Args:
            nice_ref: NICE reference ID
            
        Returns:
            Evidence data and metadata
        """
        if self.mock_mode:
            return self._mock_retrieve_evidence(nice_ref)
        else:
            return self._real_retrieve_evidence(nice_ref)
    
    # Mock implementation methods
    
    def _mock_submit_evidence(
        self,
        image_path: Optional[str],
        image_data: Optional[bytes],
        metadata: Optional[Dict]
    ) -> Dict:
        """
        Mock implementation of evidence submission.
        """
        # Generate mock NICE reference
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        nice_ref = f"NICE-{timestamp}-{unique_id}"
        
        # Store in mock storage
        mock_record = {
            "nice_ref": nice_ref,
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {},
            "status": "processed"
        }
        
        # If image_path provided, copy to mock storage
        if image_path:
            if not SHUTIL_AVAILABLE:
                raise ImportError("shutil module required for file operations")
            dest_path = self.mock_storage_path / f"{nice_ref}.jpg"
            copy2(image_path, dest_path)
            mock_record["storage_path"] = str(dest_path)
        elif image_data:
            # Save image data
            dest_path = self.mock_storage_path / f"{nice_ref}.jpg"
            with open(dest_path, 'wb') as f:
                f.write(image_data)
            mock_record["storage_path"] = str(dest_path)
        
        # Save mock record
        record_path = self.mock_storage_path / f"{nice_ref}.json"
        with open(record_path, 'w') as f:
            json.dump(mock_record, f, indent=2)
        
        return {
            "nice_ref": nice_ref,
            "status": "success",
            "storage_path": mock_record.get("storage_path", ""),
            "submitted_at": mock_record["submitted_at"]
        }
    
    def _mock_get_status(self, nice_ref: str) -> Dict:
        """
        Mock implementation of status check.
        """
        record_path = self.mock_storage_path / f"{nice_ref}.json"
        
        if not record_path.exists():
            return {
                "nice_ref": nice_ref,
                "status": "not_found"
            }
        
        with open(record_path, 'r') as f:
            record = json.load(f)
        
        return {
            "nice_ref": nice_ref,
            "status": record.get("status", "processed"),
            "submitted_at": record.get("submitted_at")
        }
    
    def _mock_retrieve_evidence(self, nice_ref: str) -> Dict:
        """
        Mock implementation of evidence retrieval.
        """
        record_path = self.mock_storage_path / f"{nice_ref}.json"
        
        if not record_path.exists():
            raise ValueError(f"Evidence not found: {nice_ref}")
        
        with open(record_path, 'r') as f:
            record = json.load(f)
        
        # Check if image file exists
        if record.get("storage_path"):
            image_path = Path(record["storage_path"])
            if image_path.exists():
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                record["image_data"] = image_data
        
        return record
    
    # Real implementation methods (placeholders for actual NICE API)
    
    def _real_submit_evidence(
        self,
        image_path: Optional[str],
        image_data: Optional[bytes],
        metadata: Optional[Dict]
    ) -> Dict:
        """
        Real implementation of evidence submission.
        
        This would make actual API calls to NICE system.
        """
        import requests
        
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Read image data if path provided
        if image_path and not image_data:
            with open(image_path, 'rb') as f:
                image_data = f.read()
        
        # Submit to NICE
        files = {"image": image_data}
        data = {"metadata": json.dumps(metadata or {})}
        
        response = requests.post(
            f"{api_url}/evidence/submit",
            headers=headers,
            files=files,
            data=data
        )
        
        response.raise_for_status()
        return response.json()
    
    def _real_get_status(self, nice_ref: str) -> Dict:
        """
        Real implementation of status check.
        """
        import requests
        
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(
            f"{api_url}/evidence/{nice_ref}/status",
            headers=headers
        )
        
        response.raise_for_status()
        return response.json()
    
    def _real_retrieve_evidence(self, nice_ref: str) -> Dict:
        """
        Real implementation of evidence retrieval.
        """
        import requests
        
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(
            f"{api_url}/evidence/{nice_ref}",
            headers=headers
        )
        
        response.raise_for_status()
        return response.json()


# Export main class
__all__ = ["NICEAdapter"]
