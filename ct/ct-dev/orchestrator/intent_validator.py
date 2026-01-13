#!/usr/bin/env python3
"""
Phase 12: Intent Validator

Validates external intent against schema.
Provides hard rejection on validation failure.
No execution, no side effects.
"""

import json
import jsonschema
import uuid
from datetime import datetime

# Phase 12 Step 2: Import composition builder
try:
    from composed_plan_builder import compose_from_intent, COMPOSED_PLAN_REGISTRY
    COMPOSITION_AVAILABLE = True
except ImportError:
    COMPOSITION_AVAILABLE = False

# Phase 12 Intent Schema (extends ct-intent.schema.json)
INTENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CT Phase 12 Intent (External)",
    "type": "object",
    "required": ["intent", "source"],
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "inspect_repo",
                "summarise_logs",
                "analyze_code",
                "plan_action",
                "apply_patch",
                # Client-defined intents
                "block_purchase",
                "verify_account",
                "require_mfa",
                "flag_for_review",
                "allow"
            ],
            "description": "Intent type (from ct-intent.schema.json)"
        },
        "source": {
            "type": "string",
            "description": "External system identifier (e.g., 'user_cli', 'automation_system')"
        },
        "target": {
            "type": "string",
            "description": "Abstract target identifier"
        },
        "context": {
            "oneOf": [{"type": "string"}, {"type": "object"}],
            "description": "Human-readable context for the intent (string or structured object)"
        },
        "patch_content": {
            "type": "string",
            "description": "For apply_patch intent"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.5,
            "description": "Intent confidence (advisory only, never used for auto-approval)"
        },
        "mode": {
            "type": "string",
            "enum": ["reason-only", "simulate", "propose"],
            "default": "propose",
            "description": "Execution mode"
        },
        "notes": {
            "type": "string",
            "description": "Additional notes"
        },
        "phases": {
            "type": "array",
            "description": "Optional: proposed phase sequence for plan composition",
            "items": {
                "type": "object",
                "required": ["phase_id", "description"],
                "properties": {
                    "phase_id": {
                        "type": "string",
                        "description": "Unique phase identifier"
                    },
                    "description": {
                        "type": "string",
                        "description": "Phase description"
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Phase dependencies"
                    },
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Task descriptions"
                    }
                },
                "additionalProperties": False
            }
        }
    },
    "additionalProperties": False
}

class IntentValidator:
    """Validates intent against schema with hard rejection on failure."""
    
    def __init__(self, schema=INTENT_SCHEMA):
        self.schema = schema
        self.validator = jsonschema.Draft7Validator(schema)
    
    def validate(self, intent_data):
        """Validate intent data against schema.
        
        Returns:
            (success: bool, intent_object: dict or None, error_details: dict or None)
        """
        # Attempt to parse as JSON if string
        if isinstance(intent_data, str):
            try:
                intent_data = json.loads(intent_data)
            except json.JSONDecodeError as e:
                return False, None, {
                    "reason": "json_parse_error",
                    "message": str(e)
                }
        
        # Validate against schema
        errors = list(self.validator.iter_errors(intent_data))
        
        if errors:
            return False, None, {
                "reason": "schema_validation_failed",
                "errors": [
                    {
                        "field": e.json_path,
                        "message": e.message,
                        "schema_constraint": e.schema.get("type", "unknown")
                    }
                    for e in errors[:5]  # Limit to first 5 errors
                ]
            }
        
        # Validation passed: wrap with Phase 12 metadata
        intent_object = {
            "intent_id": str(uuid.uuid4()),
            "source": intent_data.get("source", "unknown"),
            "data": intent_data,
            "arrival_time": datetime.utcnow().isoformat() + "Z",
            "status": "pending",  # pending | approved | rejected
            "composed_plan_id": None
        }
        
        return True, intent_object, None
    
    def validate_batch(self, intent_list):
        """Validate multiple intents.
        
        Returns:
            (accepted: [intent_objects], rejected: [{intent_data, error}])
        """
        accepted = []
        rejected = []
        
        for intent in intent_list:
            success, obj, error = self.validate(intent)
            if success:
                accepted.append(obj)
            else:
                rejected.append({
                    "intent_data": intent,
                    "error": error
                })
        
        return accepted, rejected


class IntentQueue:
    """In-memory intent queue management."""
    
    def __init__(self):
        self.pending = []      # [{intent_id, source, data, arrival_time, ...}]
        self.approved = []     # Intents approved by human
        self.rejected = []     # [{intent_id, reason, rejection_time}]
        self.composed = {}     # {intent_id: composed_plan}
    
    def add_pending(self, intent_object):
        """Add validated intent to pending queue."""
        self.pending.append({
            "intent_id": intent_object["intent_id"],
            "source": intent_object["source"],
            "data": intent_object["data"],
            "arrival_time": intent_object["arrival_time"],
            "status": "pending",
            "composed_plan_id": None
        })
        return intent_object["intent_id"]
    
    def reject_intent(self, intent_id, reason):
        """Move intent from pending to rejected."""
        # Find intent in pending
        intent = None
        for i, item in enumerate(self.pending):
            if item["intent_id"] == intent_id:
                intent = self.pending.pop(i)
                break
        
        if not intent:
            return False  # Intent not found
        
        # Add to rejected
        self.rejected.append({
            "intent_id": intent_id,
            "source": intent.get("source"),
            "reason": reason,
            "rejection_time": datetime.utcnow().isoformat() + "Z",
            "original_data": intent.get("data")
        })
        
        return True
    
    def approve_intent(self, intent_id, composed_plan_id=None):
        """Move intent from pending to approved."""
        # Find intent in pending
        intent = None
        for i, item in enumerate(self.pending):
            if item["intent_id"] == intent_id:
                intent = self.pending.pop(i)
                break
        
        if not intent:
            return False  # Intent not found
        
        # Add to approved
        intent["status"] = "approved"
        intent["composed_plan_id"] = composed_plan_id
        intent["approval_time"] = datetime.utcnow().isoformat() + "Z"
        self.approved.append(intent)
        
        return True
    
    def get_pending(self):
        """Get all pending intents."""
        return self.pending.copy()
    
    def get_rejected(self):
        """Get all rejected intents."""
        return self.rejected.copy()
    
    def get_approved(self):
        """Get all approved intents."""
        return self.approved.copy()
    
    def to_dict(self):
        """Export queue state as dict."""
        return {
            "pending": self.get_pending(),
            "approved": self.get_approved(),
            "rejected": self.get_rejected()
        }


# Global queue (singleton)
INTENT_QUEUE = IntentQueue()


def validate_intent(intent_data):
    """Top-level intent validation function.
    
    Args:
        intent_data: dict or JSON string
    
    Returns:
        {
            "status": "accepted" | "rejected",
            "intent_id": str or None,
            "composed_plan_id": str or None,
            "message": str,
            "errors": list or None
        }
    """
    validator = IntentValidator()
    success, intent_obj, error = validator.validate(intent_data)
    
    if success:
        intent_id = INTENT_QUEUE.add_pending(intent_obj)
        
        # Phase 12 Step 2: Attempt composition if available
        composed_plan_id = None
        if COMPOSITION_AVAILABLE:
            try:
                comp_success, comp_plan_id = compose_from_intent(intent_obj)
                if comp_success:
                    composed_plan_id = comp_plan_id
                    # Update intent object with composed plan reference
                    intent_obj["composed_plan_id"] = composed_plan_id
            except Exception as e:
                # Composition failure is not fatal; continue with intent
                pass
        
        return {
            "status": "accepted",
            "intent_id": intent_id,
            "composed_plan_id": composed_plan_id,
            "message": f"Intent queued for human approval. Intent ID: {intent_id}" +
                      (f" (Plan ID: {composed_plan_id})" if composed_plan_id else ""),
            "errors": None
        }
    else:
        return {
            "status": "rejected",
            "intent_id": None,
            "composed_plan_id": None,
            "message": f"Intent validation failed: {error.get('reason', 'unknown')}",
            "errors": error.get("errors", [])
        }
