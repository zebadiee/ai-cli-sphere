"""
Evidence Ingestion Module

Provides tools for ingesting, processing, and managing evidence images.
"""

from .evidence_pipeline import EvidenceIngestionPipeline
from .image_processor import ImageProcessor
from .nice_adapter import NICEAdapter
from .evidence_store import EvidenceStore
from .linking import EvidenceLinking

__all__ = [
    "EvidenceIngestionPipeline",
    "ImageProcessor",
    "NICEAdapter",
    "EvidenceStore",
    "EvidenceLinking",
]
