#!/usr/bin/env python3
"""
Phase 14.3: CT SDK Client

Thin Python client for gateway communication.
Submits intents, polls state, reads audit trail.

Usage:
    client = CTClient(gateway_url="http://localhost:9001", api_key="sk_test_12345")
    intent_response = client.submit_intent(intent="analyze_code", target="repo")
    state = client.get_orchestrator_state()
    plans = client.get_plans()
    audit = client.get_audit_trail(limit=50)
"""

import httpx
import time
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """Valid intent types."""
    INSPECT_REPO = "inspect_repo"
    SUMMARISE_LOGS = "summarise_logs"
    ANALYZE_CODE = "analyze_code"
    PLAN_ACTION = "plan_action"
    APPLY_PATCH = "apply_patch"


class IntentMode(Enum):
    """Valid intent modes."""
    REASON_ONLY = "reason-only"
    SIMULATE = "simulate"
    PROPOSE = "propose"


class CTClientError(Exception):
    """Base exception for CT client errors."""
    pass


class CTAuthError(CTClientError):
    """Authentication error (401)."""
    pass


class CTRateLimitError(CTClientError):
    """Rate limit exceeded (429)."""
    pass


class CTNotFoundError(CTClientError):
    """Resource not found (404)."""
    pass


class CTSchemaError(CTClientError):
    """Schema validation error (422)."""
    pass


class CTServerError(CTClientError):
    """Server error (500)."""
    pass


@dataclass
class IntentResponse:
    """Response from intent submission."""
    status: str  # "accepted" or "rejected"
    intent_id: Optional[str] = None
    composed_plan_id: Optional[str] = None
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "IntentResponse":
        obj = cls(
            status=data.get("status", "unknown"),
            intent_id=data.get("intent_id"),
            composed_plan_id=data.get("composed_plan_id"),
            message=data.get("message", ""),
            timestamp=data.get("timestamp", time.time())
        )
        # Provide compatibility alias expected by validation harness
        setattr(obj, 'id', obj.intent_id)
        return obj


@dataclass
class OrchestratorState:
    """Orchestrator state response."""
    halted: bool
    current_phase: Optional[str] = None
    approved_phase_id: Optional[str] = None
    current_plan_id: Optional[str] = None
    active_plan_count: int = 0
    pending_intent_count: int = 0
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OrchestratorState":
        return cls(
            halted=data.get("halted", True),
            current_phase=data.get("current_phase"),
            approved_phase_id=data.get("approved_phase_id"),
            current_plan_id=data.get("current_plan_id"),
            active_plan_count=int(data.get("active_plan_count", 0) or 0),
            pending_intent_count=int(data.get("pending_intent_count", 0) or 0),
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class Plan:
    """Composed plan."""
    plan_id: str
    state: str
    phases: List[Dict] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Plan":
        return cls(
            plan_id=data.get("plan_id", "unknown"),
            state=data.get("state", "unknown"),
            phases=data.get("phases", [])
        )


@dataclass
class PlansResponse:
    """Response from plans endpoint."""
    pending: List[Plan] = field(default_factory=list)
    approved: List[Plan] = field(default_factory=list)
    rejected: List[Plan] = field(default_factory=list)
    executing: List[Plan] = field(default_factory=list)
    completed: List[Plan] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PlansResponse":
        pending = [Plan.from_dict(p) for p in data.get("pending", [])]
        approved = [Plan.from_dict(p) for p in data.get("approved", [])]
        rejected = [Plan.from_dict(p) for p in data.get("rejected", [])]
        executing = [Plan.from_dict(p) for p in data.get("executing", [])]
        completed = [Plan.from_dict(p) for p in data.get("completed", [])]
        
        return cls(
            pending=pending,
            approved=approved,
            rejected=rejected,
            executing=executing,
            completed=completed,
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class IntentsQueueResponse:
    """Response from intents queue endpoint."""
    pending: List[Dict] = field(default_factory=list)
    approved: List[Dict] = field(default_factory=list)
    rejected: List[Dict] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "IntentsQueueResponse":
        return cls(
            pending=data.get("pending", []),
            approved=data.get("approved", []),
            rejected=data.get("rejected", []),
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class AuditTrailResponse:
    """Response from audit trail endpoint."""
    events: List[Dict] = field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 100
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AuditTrailResponse":
        return cls(
            events=data.get("events", []),
            total=data.get("total", 0),
            offset=data.get("offset", 0),
            limit=data.get("limit", 100),
            timestamp=data.get("timestamp", time.time())
        )


class CTClient:
    """CT SDK Client for gateway communication."""
    
    def __init__(
        self,
        gateway_url: str = "http://localhost:9001",
        api_key: str = "sk_test_default",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize CT client.
        
        Args:
            gateway_url: Gateway base URL (e.g., http://localhost:9001)
            api_key: API key for authentication (format: sk_test_* or sk_prod_*)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient errors
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Validate API key format
        if not api_key.startswith(("sk_test_", "sk_prod_")):
            raise CTClientError(f"Invalid API key format: {api_key}")
        
        self.client = httpx.Client(
            timeout=timeout,
            headers=self._auth_headers()
        )
    
    def _auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        
        if response.status_code == 401:
            raise CTAuthError(f"Unauthorized: {response.text}")
        
        if response.status_code == 429:
            raise CTRateLimitError(f"Rate limit exceeded: {response.text}")
        
        if response.status_code == 404:
            raise CTNotFoundError(f"Not found: {response.text}")
        
        if response.status_code == 422:
            raise CTSchemaError(f"Schema validation failed: {response.text}")
        
        if response.status_code >= 500:
            raise CTServerError(f"Server error: {response.text}")
        
        if response.status_code >= 400:
            raise CTClientError(f"HTTP {response.status_code}: {response.text}")
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw": response.text}
    
    def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        
        url = f"{self.gateway_url}{path}"
        
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    response = self.client.get(url, **kwargs)
                elif method == "POST":
                    response = self.client.post(url, **kwargs)
                else:
                    raise CTClientError(f"Unsupported method: {method}")
                
                return self._handle_response(response)
            
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt  # Exponential backoff
                    time.sleep(backoff)
                else:
                    raise CTClientError(f"Connection failed after {self.max_retries} retries: {e}")
            
            except CTServerError:
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    raise
            
            except (CTAuthError, CTRateLimitError, CTNotFoundError, CTSchemaError):
                # Don't retry these
                raise
    
    def submit_intent(
        self,
        intent: str,
        target: str,
        confidence: float = 0.5,
        mode: str = "reason-only",
        context: Optional[str] = None
    ) -> IntentResponse:
        """
        Submit an intent for processing.
        
        Args:
            intent: Intent type (inspect_repo, summarise_logs, analyze_code, plan_action, apply_patch)
            target: Target system/entity
            confidence: Confidence score (0.0-1.0), advisory only
            mode: Mode (reason-only, simulate, propose)
            context: Optional context/description
        
        Returns:
            IntentResponse with status (accepted/rejected), intent_id, composed_plan_id
        
        Raises:
            CTAuthError: Invalid API key
            CTSchemaError: Invalid intent data
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        payload = {
            "intent": intent,
            "target": target,
            "confidence": confidence,
            "mode": mode
        }
        
        if context:
            payload["context"] = context
        
        data = self._request_with_retry(
            "POST",
            "/intent",
            json=payload
        )
        
        return IntentResponse.from_dict(data)
    
    def get_orchestrator_state(self) -> OrchestratorState:
        """
        Read current orchestrator state.
        
        Returns:
            OrchestratorState with halted status, current plan, phases
        
        Raises:
            CTAuthError: Invalid API key
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        data = self._request_with_retry(
            "GET",
            "/governance/orchestrator-state"
        )
        
        return OrchestratorState.from_dict(data)
    
    def get_plans(self) -> PlansResponse:
        """
        Read all plans (current + completed).
        
        Returns:
            PlansResponse with current and completed plans
        
        Raises:
            CTAuthError: Invalid API key
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        data = self._request_with_retry(
            "GET",
            "/governance/plans"
        )
        
        return PlansResponse.from_dict(data)
    
    def get_plan(self, plan_id: str) -> Plan:
        """
        Read specific plan.
        
        Args:
            plan_id: Plan identifier
        
        Returns:
            Plan with phases and state
        
        Raises:
            CTNotFoundError: Plan not found
            CTAuthError: Invalid API key
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        data = self._request_with_retry(
            "GET",
            f"/governance/plans/{plan_id}"
        )
        
        return Plan.from_dict(data)
    
    def get_intents(self) -> IntentsQueueResponse:
        """
        Read intent queue.
        
        Returns:
            IntentsQueueResponse with pending, approved, rejected intents
        
        Raises:
            CTAuthError: Invalid API key
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        data = self._request_with_retry(
            "GET",
            "/governance/intents"
        )
        
        return IntentsQueueResponse.from_dict(data)
    
    def get_audit_trail(
        self,
        plan_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> AuditTrailResponse:
        """
        Read audit trail with optional filtering.
        
        Args:
            plan_id: Optional plan ID to filter events
            limit: Number of events to return (1-1000)
            offset: Offset for pagination
        
        Returns:
            AuditTrailResponse with events, total count, pagination info
        
        Raises:
            CTSchemaError: Invalid limit (must be 1-1000)
            CTAuthError: Invalid API key
            CTRateLimitError: Rate limited
            CTServerError: Server error
        """
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if plan_id:
            params["plan_id"] = plan_id
        
        data = self._request_with_retry(
            "GET",
            "/governance/audit",
            params=params
        )
        
        return AuditTrailResponse.from_dict(data)
    
    def poll_orchestrator_state(
        self,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
        condition: Optional[callable] = None
    ) -> OrchestratorState:
        """
        Poll orchestrator state until condition is met or timeout.
        
        Args:
            timeout: Maximum polling duration in seconds
            poll_interval: Time between polls in seconds
            condition: Function(state) -> bool; stops when True
        
        Returns:
            OrchestratorState when condition met or timeout
        
        Raises:
            CTClientError: Polling failed
        """
        
        if condition is None:
            condition = lambda s: not s.halted  # Stop when not halted
        
        start = time.time()
        
        while time.time() - start < timeout:
            state = self.get_orchestrator_state()
            
            if condition(state):
                return state
            
            time.sleep(poll_interval)
        
        # Timeout reached
        final_state = self.get_orchestrator_state()
        return final_state
    
    def wait_for_plan_approval(
        self,
        plan_id: str,
        timeout: float = 60.0
    ) -> Plan:
        """
        Wait for plan to be approved (appear in approved state).
        
        Args:
            plan_id: Plan identifier to wait for
            timeout: Maximum wait duration in seconds
        
        Returns:
            Plan when approved or final state at timeout
        
        Raises:
            CTNotFoundError: Plan not found
            CTClientError: Polling failed
        """
        
        start = time.time()
        
        while time.time() - start < timeout:
            plans = self.get_plans()
            
            if plans.current and plans.current.plan_id == plan_id:
                return plans.current
            
            time.sleep(0.5)
        
        # Timeout reached
        return self.get_plan(plan_id)
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# SIMPLE EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("CT SDK Client Example\n")
    
    # Create client
    client = CTClient(
        gateway_url="http://localhost:9001",
        api_key="sk_test_12345"
    )
    
    try:
        # Check orchestrator state
        print("1. Checking orchestrator state...")
        state = client.get_orchestrator_state()
        print(f"   Halted: {state.halted}")
        print(f"   Current plan: {state.current_plan_id}")
        print()
        
        # Submit intent
        print("2. Submitting intent...")
        response = client.submit_intent(
            intent="analyze_code",
            target="repo",
            confidence=0.85,
            mode="simulate",
            context="Analyze repository structure"
        )
        print(f"   Status: {response.status}")
        print(f"   Intent ID: {response.intent_id}")
        print(f"   Composed plan: {response.composed_plan_id}")
        print(f"   Message: {response.message}")
        print()
        
        # Get plans
        print("3. Listing plans...")
        plans = client.get_plans()
        print(f"   Current plan: {plans.current.plan_id if plans.current else 'None'}")
        print(f"   Completed plans: {len(plans.completed)}")
        print()
        
        # Get intents
        print("4. Listing intents...")
        intents = client.get_intents()
        print(f"   Pending: {len(intents.pending)}")
        print(f"   Approved: {len(intents.approved)}")
        print(f"   Rejected: {len(intents.rejected)}")
        print()
        
        # Get audit trail
        print("5. Reading audit trail...")
        audit = client.get_audit_trail(limit=10)
        print(f"   Events returned: {len(audit.events)}")
        print(f"   Total events: {audit.total}")
        for event in audit.events[:3]:
            print(f"   - {event.get('operation')} by {event.get('actor')}: {event.get('result')}")
        
    except CTClientError as e:
        print(f"Error: {e}")
    
    finally:
        client.close()
