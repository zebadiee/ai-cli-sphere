"""
ECIR Studio - Electrical Installation Condition Report System

This package provides tools for:
1. PDF generation of EICR forms
2. Evidence ingestion and management
3. Integration with NICE system
"""

__version__ = "1.0.0"

from .contracts import (
    ClassificationCode,
    OverallAssessment,
    AuthorityBoundary,
    ValidationRules,
    AuditTrail,
)

__all__ = [
    "ClassificationCode",
    "OverallAssessment",
    "AuthorityBoundary",
    "ValidationRules",
    "AuditTrail",
]
