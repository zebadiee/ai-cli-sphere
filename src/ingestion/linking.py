"""
Evidence Linking

Manages links between evidence and EICR observations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class EvidenceLinking:
    """
    Manages relationships between evidence and EICR observations.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize evidence linking.
        
        Args:
            storage_path: Path for storing link data
        """
        if storage_path:
            self.links_path = Path(storage_path)
        else:
            self.links_path = Path.home() / ".ecir_evidence_store" / "links"
        
        self.links_path.mkdir(parents=True, exist_ok=True)
    
    def create_link(
        self,
        eicr_id: str,
        observation_item: str,
        evidence_ids: List[str]
    ) -> Dict:
        """
        Create a link between evidence and an observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number
            evidence_ids: List of evidence IDs
            
        Returns:
            Link record
        """
        # Load or create links file for this EICR
        links_file = self.links_path / f"{eicr_id}.json"
        
        if links_file.exists():
            with open(links_file, 'r') as f:
                links_data = json.load(f)
        else:
            links_data = {
                "eicr_id": eicr_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "observations": {}
            }
        
        # Add or update observation links
        if observation_item not in links_data["observations"]:
            links_data["observations"][observation_item] = {
                "evidence_ids": [],
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        
        # Add evidence IDs (avoid duplicates)
        existing_ids = set(links_data["observations"][observation_item]["evidence_ids"])
        for evidence_id in evidence_ids:
            if evidence_id not in existing_ids:
                links_data["observations"][observation_item]["evidence_ids"].append(evidence_id)
        
        links_data["observations"][observation_item]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        links_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Save
        with open(links_file, 'w') as f:
            json.dump(links_data, f, indent=2)
        
        return {
            "eicr_id": eicr_id,
            "observation_item": observation_item,
            "evidence_ids": links_data["observations"][observation_item]["evidence_ids"],
            "linked_at": links_data["observations"][observation_item].get("updated_at")
        }
    
    def get_evidence_for_observation(
        self,
        eicr_id: str,
        observation_item: str
    ) -> List[str]:
        """
        Get evidence IDs linked to an observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number
            
        Returns:
            List of evidence IDs
        """
        links_file = self.links_path / f"{eicr_id}.json"
        
        if not links_file.exists():
            return []
        
        with open(links_file, 'r') as f:
            links_data = json.load(f)
        
        if observation_item not in links_data.get("observations", {}):
            return []
        
        return links_data["observations"][observation_item].get("evidence_ids", [])
    
    def get_observations_for_evidence(
        self,
        eicr_id: str,
        evidence_id: str
    ) -> List[str]:
        """
        Get observation items linked to an evidence.
        
        Args:
            eicr_id: EICR report ID
            evidence_id: Evidence ID
            
        Returns:
            List of observation item numbers
        """
        links_file = self.links_path / f"{eicr_id}.json"
        
        if not links_file.exists():
            return []
        
        with open(links_file, 'r') as f:
            links_data = json.load(f)
        
        observation_items = []
        for obs_item, obs_data in links_data.get("observations", {}).items():
            if evidence_id in obs_data.get("evidence_ids", []):
                observation_items.append(obs_item)
        
        return observation_items
    
    def get_all_links_for_eicr(self, eicr_id: str) -> Dict:
        """
        Get all evidence links for an EICR.
        
        Args:
            eicr_id: EICR report ID
            
        Returns:
            Complete links data structure
        """
        links_file = self.links_path / f"{eicr_id}.json"
        
        if not links_file.exists():
            return {
                "eicr_id": eicr_id,
                "observations": {}
            }
        
        with open(links_file, 'r') as f:
            return json.load(f)
    
    def remove_link(
        self,
        eicr_id: str,
        observation_item: str,
        evidence_id: str
    ) -> bool:
        """
        Remove a specific evidence link from an observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number
            evidence_id: Evidence ID to remove
            
        Returns:
            True if removed, False if not found
        """
        links_file = self.links_path / f"{eicr_id}.json"
        
        if not links_file.exists():
            return False
        
        with open(links_file, 'r') as f:
            links_data = json.load(f)
        
        if observation_item not in links_data.get("observations", {}):
            return False
        
        evidence_ids = links_data["observations"][observation_item].get("evidence_ids", [])
        if evidence_id not in evidence_ids:
            return False
        
        # Remove the evidence ID
        evidence_ids.remove(evidence_id)
        links_data["observations"][observation_item]["evidence_ids"] = evidence_ids
        links_data["observations"][observation_item]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        links_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Save
        with open(links_file, 'w') as f:
            json.dump(links_data, f, indent=2)
        
        return True
    
    def delete_observation_links(
        self,
        eicr_id: str,
        observation_item: str
    ) -> bool:
        """
        Delete all evidence links for an observation.
        
        Args:
            eicr_id: EICR report ID
            observation_item: Observation item number
            
        Returns:
            True if deleted, False if not found
        """
        links_file = self.links_path / f"{eicr_id}.json"
        
        if not links_file.exists():
            return False
        
        with open(links_file, 'r') as f:
            links_data = json.load(f)
        
        if observation_item not in links_data.get("observations", {}):
            return False
        
        # Remove the observation
        del links_data["observations"][observation_item]
        links_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Save
        with open(links_file, 'w') as f:
            json.dump(links_data, f, indent=2)
        
        return True


# Export main class
__all__ = ["EvidenceLinking"]
