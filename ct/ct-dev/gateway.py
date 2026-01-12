#!/usr/bin/env python3
"""
Phase 14.2: HTTP Gateway Implementation

Thin, non-escalatory HTTP transport layer over frozen OpenAPI v1.
Zero business logic, strict schema validation, full parity with SDK surface.

Architecture:
  1. FastAPI app with 6 frozen endpoints (POST /intent, GET /governance/*)
  2. Request/response schema validation (against openapi_v1_frozen.json)
  3. Auth middleware (API key validation)
  4. Rate limiting middleware (10 req/sec per key)
  5. Audit emission (append-only, no mutation)
  6. Error mapping (deterministic codes, no information leakage)

Invariants Enforced:
  - Intent = Data (POST /intent does NOT execute)
  - Human Approval Required (no /internal/approve endpoints)
  - HALT Absolute (no /internal/resume endpoints)
  - Audit Append-Only (read-only responses)
  - No Execution Verbs (POST/GET only, no PUT/DELETE/PATCH)
  - Surface = {get_orchestrator_state, get_plans, get_plan, get_intents, get_audit_trail, submit_intent}

Dependencies:
  - fastapi
  - uvicorn (ASGI server)
  - pydantic (schema validation)
"""

from fastapi import FastAPI, Request, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import json
import time
import sys
import os
from datetime import datetime

# Add orchestrator to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orchestrator'))

# Import frozen core (Phase 12)
from intent_validator import IntentValidator, IntentQueue, validate_intent, INTENT_QUEUE
from composed_plan_builder import ComposedPlanRegistry, COMPOSED_PLAN_REGISTRY
from audit_system import AuditLog, AUDIT_LOG


# ============================================================================
# REQUEST/RESPONSE SCHEMAS (from openapi_v1_frozen.json)
# ============================================================================

class IntentRequest(BaseModel):
    """Intent submission request (POST /intent)"""
    intent: str = Field(..., description="Intent type")
    target: str = Field(..., description="Target system/entity")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score (advisory)")
    mode: str = Field(default="reason-only", description="Mode: reason-only, simulate, propose")
    context: Optional[str] = Field(None, description="Optional context")
    
    @validator('intent')
    def validate_intent_enum(cls, v):
        valid = [
            "inspect_repo",
            "summarise_logs",
            "analyze_code",
            "plan_action",
            "apply_patch",
            # Extended intents used by clients
            "block_purchase",
            "verify_account",
            "require_mfa",
            "flag_for_review",
            "allow",
        ]
        if v not in valid:
            raise ValueError(f"intent must be one of {valid}")
        return v
    
    @validator('target')
    def validate_target_nonempty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("target must be non-empty string")
        return v
    
    @validator('mode')
    def validate_mode_enum(cls, v):
        valid = ["reason-only", "simulate", "propose"]
        if v not in valid:
            raise ValueError(f"mode must be one of {valid}")
        return v


class IntentResponse(BaseModel):
    """Intent submission response"""
    status: str = Field(..., description="accepted or rejected")
    intent_id: Optional[str] = Field(None, description="ID if accepted")
    composed_plan_id: Optional[str] = Field(None, description="Composed plan ID if applicable")
    message: str = Field(..., description="Status message")
    timestamp: float = Field(..., description="Unix timestamp")


class OrchestratorStateResponse(BaseModel):
    """Orchestrator state response"""
    halted: bool
    current_phase: Optional[str]
    approved_phase_id: Optional[str]
    current_plan_id: Optional[str]
    timestamp: float


class PlansResponse(BaseModel):
    """Plans list response"""
    current: Dict[str, Any]
    completed: List[Dict[str, Any]]
    timestamp: float


class PlanDetail(BaseModel):
    """Individual plan detail"""
    plan_id: str
    plan_type: str
    phases: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class IntentsQueueResponse(BaseModel):
    """Intent queue response"""
    pending: List[Dict[str, Any]]
    approved: List[Dict[str, Any]]
    rejected: List[Dict[str, Any]]
    timestamp: float


class AuditEventSchema(BaseModel):
    """Single audit event"""
    event_id: str
    timestamp: float
    actor: str
    operation: str
    resource: str
    result: str
    details: Dict[str, Any]


class AuditTrailResponse(BaseModel):
    """Audit trail response"""
    events: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    timestamp: float


class ErrorResponse(BaseModel):
    """Error response"""
    code: str
    message: str
    timestamp: float


# ============================================================================
# GATEWAY INITIALIZATION
# ============================================================================

app = FastAPI(
    title="CT Governance Gateway",
    version="1.0.0",
    description="Thin HTTP gateway over frozen OpenAPI v1",
    openapi_url="/openapi.json",
)

# CORS: Locked to allowlist (no wildcard)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:9001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # No PUT, DELETE, PATCH
    allow_headers=["Authorization", "Content-Type"],
)

# Global state (references Phase 12 sealed core)
validator = IntentValidator()
intent_queue = INTENT_QUEUE
plan_registry = COMPOSED_PLAN_REGISTRY
audit_log = AUDIT_LOG


# ============================================================================
# GATEWAY MIDDLEWARE (auth + rate limiting)
# ============================================================================

class RateLimiter:
    """Per-key rate limiter (10 req/sec)"""
    MAX_REQUESTS_PER_SECOND = 10
    
    def __init__(self):
        self.requests = {}  # key -> list of timestamps
    
    def check_and_wait(self, api_key: str) -> bool:
        """Check if request allowed, return False if rate limited"""
        now = time.time()
        
        if api_key not in self.requests:
            self.requests[api_key] = []
        
        # Remove old requests (>1 sec old)
        self.requests[api_key] = [
            ts for ts in self.requests[api_key] if now - ts < 1.0
        ]
        
        # Check limit
        if len(self.requests[api_key]) >= self.MAX_REQUESTS_PER_SECOND:
            return False
        
        # Record this request
        self.requests[api_key].append(now)
        return True


rate_limiter = RateLimiter()


@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    """
    Middleware: validate API key and enforce rate limiting via `gateway_auth`.
    Deny-by-default: invalid or unknown keys → 401
    """

    # Skip auth for health checks and OpenAPI
    if request.url.path in ["/healthz", "/openapi.json", "/docs", "/redoc"]:
        return await call_next(request)

    # Extract API key from Authorization header
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "code": "AUTH_INVALID_KEY",
                "message": "Missing or invalid Authorization header",
                "timestamp": time.time()
            }
        )

    api_key = auth_header[7:]  # Remove "Bearer " prefix

    # Use centralized security context to validate request
    from gateway_auth import validate_request

    # We don't know body size at middleware time without reading body; pass 0 for now
    status_code, err_code = validate_request(api_key, request.method, request.url.path, dict(request.headers), 0)

    if status_code != 200:
        # Map codes to friendly messages
        msg_map = {
            401: ("AUTH_INVALID_KEY", "Invalid or unknown API key"),
            429: ("RATE_LIMIT_EXCEEDED", "Rate limit exceeded (10 req/sec)"),
            400: ("INVALID_REQUEST", "Request size or format invalid"),
            403: ("AUTH_INSUFFICIENT_PERMISSION", "Permission denied for this operation")
        }
        code, message = msg_map.get(status_code, ("AUTH_INVALID_KEY", "Authentication failed"))
        return JSONResponse(
            status_code=status_code,
            content={
                "code": code,
                "message": message,
                "timestamp": time.time()
            }
        )

    # Store in request state for use in handlers
    request.state.api_key = api_key

    response = await call_next(request)
    return response


@app.middleware("http")
async def block_mutation_verbs_middleware(request: Request, call_next):
    """
    Middleware: Block PUT, DELETE, PATCH verbs (403 Forbidden).
    Only allow GET and POST.
    """
    if request.method in ["PUT", "DELETE", "PATCH"]:
        return JSONResponse(
            status_code=403,
            content={
                "code": "METHOD_NOT_ALLOWED",
                "message": f"HTTP method {request.method} is not allowed",
                "timestamp": time.time()
            }
        )
    
    return await call_next(request)


# ============================================================================
# ENDPOINT: POST /intent (Intent Submission)
# ============================================================================

@app.post(
    "/intent",
    response_model=IntentResponse,
    status_code=200,
    responses={
        400: {"model": ErrorResponse, "description": "Schema validation failed"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def submit_intent(
    request: Request,
    body: IntentRequest,
    x_actor: Optional[str] = Header(None)
) -> IntentResponse:
    """
    Submit an intent for processing.
    
    Intent is stored as DATA (non-executable).
    No auto-approval, no auto-execution.
    Confidence is ADVISORY only.
    
    Returns: IntentResponse with status (accepted/rejected)
    """
    try:
        api_key = request.state.api_key
        actor = x_actor or "gateway-client"
        
        # Convert request to intent dict
        intent_dict = {
            "intent": body.intent,
            "source": body.target,  # Mapped from target field
            "confidence": body.confidence,
            "mode": body.mode,
            "context": body.context,
        }
        
        # Validate and queue (Phase 12 sealed core)
        result = validate_intent(intent_dict)
        
        # Emit audit event
        audit_log.emit({
            "operation": "submit_intent",
            "actor": actor,
            "result": result["status"],
            "details": {
                "intent": body.intent,
                "target": body.target,
                "confidence": body.confidence,
                "intent_id": result.get("intent_id"),
            }
        })
        
        # Map result to IntentResponse
        return IntentResponse(
            status=result["status"],
            intent_id=result.get("intent_id"),
            composed_plan_id=result.get("composed_plan_id"),
            message=result["message"],
            timestamp=time.time()
        )
    
    except Exception as e:
        # Internal error
        audit_log.emit({
            "operation": "submit_intent",
            "actor": request.state.api_key,
            "result": "error",
            "details": {"error": str(e)}
        })
        
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# ENDPOINT: GET /governance/orchestrator-state (Read State)
# ============================================================================

@app.get(
    "/governance/orchestrator-state",
    response_model=OrchestratorStateResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def get_orchestrator_state(
    request: Request,
    x_actor: Optional[str] = Header(None)
) -> OrchestratorStateResponse:
    """Read current orchestrator state (HALT status, current plan, etc.)"""
    try:
        actor = x_actor or "gateway-client"
        
        # Hardcoded sealed state (no mutation)
        state = {
            "halted": True,
            "current_phase": None,
            "approved_phase_id": None,
            "current_plan_id": None,
        }
        
        # Audit read
        audit_log.emit({
            "operation": "get_orchestrator_state",
            "actor": actor,
            "result": "success",
            "details": {}
        })
        
        return OrchestratorStateResponse(
            **state,
            timestamp=time.time()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# ENDPOINT: GET /governance/plans (List Plans)
# ============================================================================

@app.get(
    "/governance/plans",
    response_model=PlansResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def get_plans(
    request: Request,
    x_actor: Optional[str] = Header(None)
) -> PlansResponse:
    """Read all plans (current + completed)"""
    try:
        actor = x_actor or "gateway-client"
        
        # Get executing plans (current) or default to halted state
        executing_plans = plan_registry.get_executing()
        current_plan = executing_plans[0] if executing_plans else {
            "plan_id": None,
            "state": "halted",
            "phases": []
        }
        completed_plans = plan_registry.get_completed()
        
        # Audit read
        audit_log.emit({
            "operation": "get_plans",
            "actor": actor,
            "result": "success",
            "details": {
                "current_plan_id": current_plan.get("plan_id"),
                "completed_count": len(completed_plans)
            }
        })
        
        return PlansResponse(
            current=current_plan,
            completed=completed_plans,
            timestamp=time.time()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# ENDPOINT: GET /governance/plans/{plan_id} (Get Plan Detail)
# ============================================================================

@app.get(
    "/governance/plans/{plan_id}",
    response_model=PlanDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def get_plan(
    request: Request,
    plan_id: str,
    x_actor: Optional[str] = Header(None)
) -> PlanDetail:
    """Read specific plan by ID"""
    try:
        actor = x_actor or "gateway-client"
        
        plan = plan_registry.get_plan(plan_id)
        
        if not plan:
            audit_log.emit({
                "operation": "get_plan",
                "actor": actor,
                "result": "not_found",
                "details": {"plan_id": plan_id}
            })
            
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "PLAN_NOT_FOUND",
                    "message": f"Plan {plan_id} not found",
                    "timestamp": time.time()
                }
            )
        
        # Audit read
        audit_log.emit({
            "operation": "get_plan",
            "actor": actor,
            "result": "success",
            "details": {"plan_id": plan_id}
        })
        
        return PlanDetail(
            plan_id=plan["plan_id"],
            plan_type=plan["plan_type"],
            phases=plan["phases"],
            metadata=plan["metadata"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# ENDPOINT: GET /governance/intents (List Intents)
# ============================================================================

@app.get(
    "/governance/intents",
    response_model=IntentsQueueResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def get_intents(
    request: Request,
    x_actor: Optional[str] = Header(None)
) -> IntentsQueueResponse:
    """Read intent queue (pending, approved, rejected)"""
    try:
        actor = x_actor or "gateway-client"
        
        pending = intent_queue.get_pending()
        approved = intent_queue.get_approved()
        rejected = intent_queue.get_rejected()
        
        # Audit read
        audit_log.emit({
            "operation": "get_intents",
            "actor": actor,
            "result": "success",
            "details": {
                "pending_count": len(pending),
                "approved_count": len(approved),
                "rejected_count": len(rejected)
            }
        })
        
        return IntentsQueueResponse(
            pending=pending,
            approved=approved,
            rejected=rejected,
            timestamp=time.time()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# ENDPOINT: GET /governance/audit (Audit Trail)
# ============================================================================

@app.get(
    "/governance/audit",
    response_model=AuditTrailResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def get_audit_trail(
    request: Request,
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    limit: int = Query(100, ge=1, le=1000, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    x_actor: Optional[str] = Header(None)
) -> AuditTrailResponse:
    """Read audit trail with optional filtering"""
    try:
        actor = x_actor or "gateway-client"
        
        # Validate parameters
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_PARAMS",
                    "message": "limit must be between 1 and 1000",
                    "timestamp": time.time()
                }
            )
        
        # Get audit events
        events = audit_log.get_events(plan_id=plan_id, limit=limit, offset=offset)
        total = audit_log.get_count(plan_id=plan_id)
        
        # Audit read
        audit_log.emit({
            "operation": "get_audit_trail",
            "actor": actor,
            "result": "success",
            "details": {
                "filter_plan_id": plan_id,
                "limit": limit,
                "offset": offset,
                "events_returned": len(events)
            }
        })
        
        return AuditTrailResponse(
            events=events,
            total=total,
            offset=offset,
            limit=limit,
            timestamp=time.time()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Internal server error",
                "timestamp": time.time()
            }
        )


# ============================================================================
# HEALTH CHECK & LIVENESS
# ============================================================================

@app.get("/healthz", tags=["health"])
async def health_check():
    """Liveness probe"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@app.get("/readyz", tags=["health"])
async def readiness_check():
    """Readiness probe"""
    return {
        "status": "ready",
        "halted": True,  # Always halted unless explicitly resumed
        "timestamp": time.time()
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail or {
            "code": "SERVER_ERROR",
            "message": "Internal server error",
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "code": "SERVER_ERROR",
            "message": "Internal server error",
            "timestamp": time.time()
        }
    )


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup"""
    print("=" * 70)
    print("Phase 14.2: HTTP Gateway Starting")
    print("=" * 70)
    print("  ✓ API: FastAPI/OpenAPI v1")
    print("  ✓ Auth: Bearer token (mandatory)")
    print("  ✓ Rate Limit: 10 req/sec per key")
    print("  ✓ CORS: Locked allowlist")
    print("  ✓ Surface: 6 methods (POST /intent + 5 GET /governance/*)")
    print("  ✓ Invariants: Phase 12/13/14.1 all enforced")
    print()
    print("Frozen endpoints:")
    print("  POST   /intent")
    print("  GET    /governance/orchestrator-state")
    print("  GET    /governance/plans")
    print("  GET    /governance/plans/{plan_id}")
    print("  GET    /governance/intents")
    print("  GET    /governance/audit")
    print()
    print("Non-existent (blocked):")
    print("  ❌ /internal/* (internal only)")
    print("  ❌ /approve (no SDK approval)")
    print("  ❌ /resume (no HALT release)")
    print("  ❌ PUT/DELETE/PATCH (no data mutation)")
    print()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\nGateway shutting down...")


# ============================================================================
# MAIN ENTRY
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run on port 9001 (matches SDK default)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9001,
        log_level="info"
    )
