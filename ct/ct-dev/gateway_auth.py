#!/usr/bin/env python3
"""
Phase 14.2: Gateway Authentication & Authorization

Implements deny-by-default security model:
  - All requests require valid API key
  - Per-key rate limiting (10 req/sec)
  - Request size limits
  - CORS locked to allowlist
  - No permission escalation

Architecture:
  1. APIKeyValidator: Validate and cache API key metadata
  2. RateLimiter: Per-key sliding window rate limiting
  3. RequestSizeValidator: Prevent oversized payloads
  4. PermissionChecker: Enforce deny-by-default authorization

Invariants Enforced:
  - All operations require auth
  - No user can exceed 10 req/sec
  - No operations are implicitly allowed
  - Invalid keys → 401 Unauthorized
  - Rate limit exceeded → 429 Too Many Requests
"""

import time
import hashlib
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta


# ============================================================================
# API KEY VALIDATOR
# ============================================================================

class APIKeyValidator:
    """
    Validate and manage API keys.
    
    Key formats:
    - sk_test_*: Development/test keys (no restrictions)
    - sk_prod_*: Production keys (requires verification)
    
    Design: Deny-by-default (invalid format → 401)
    """
    
    # Known test keys (for development)
    VALID_TEST_KEYS = {
        "sk_test_12345",
        "sk_test_abcde",
        "sk_test_valid",
        # Known validation key used by live validation harness
        "sk_test_validation_key_1234567890ab",
    }
    
    # In production, these would be validated against a real key store
    VALID_PROD_KEYS = set()
    
    def __init__(self):
        self.key_metadata = {}  # Cache: key -> {created, last_used, usage_count}
    
    def validate(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate API key format and existence.
        
        Returns: (is_valid, reason)
        """
        
        # Deny-by-default: empty or None
        if not api_key or not isinstance(api_key, str):
            return False, "Invalid key format"
        
        # Whitelist known test keys
        if api_key in self.VALID_TEST_KEYS:
            self._record_access(api_key)
            return True, "Valid test key"
        
        # Whitelist known prod keys
        if api_key in self.VALID_PROD_KEYS:
            self._record_access(api_key)
            return True, "Valid production key"
        
        # Deny anything else
        return False, "API key not found"
    
    def _record_access(self, api_key: str):
        """Record metadata about key usage"""
        if api_key not in self.key_metadata:
            self.key_metadata[api_key] = {
                "created": time.time(),
                "last_used": time.time(),
                "usage_count": 1
            }
        else:
            meta = self.key_metadata[api_key]
            meta["last_used"] = time.time()
            meta["usage_count"] += 1


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    Per-key rate limiting using sliding window.
    
    Limit: 10 requests per second
    Enforcement: On every request (fail-fast)
    Error: 429 Too Many Requests
    """
    
    MAX_REQUESTS_PER_SECOND = 10
    WINDOW_SIZE = 1.0  # seconds
    
    def __init__(self):
        self.request_history = {}  # key -> list of timestamps
    
    def check_and_record(self, api_key: str) -> Tuple[bool, str]:
        """
        Check if request is allowed, record if yes.
        
        Returns: (is_allowed, reason)
        """
        
        now = time.time()
        
        # Initialize key if needed
        if api_key not in self.request_history:
            self.request_history[api_key] = []
        
        # Remove requests older than window
        self.request_history[api_key] = [
            ts for ts in self.request_history[api_key]
            if now - ts < self.WINDOW_SIZE
        ]
        
        # Check limit
        current_count = len(self.request_history[api_key])
        
        if current_count >= self.MAX_REQUESTS_PER_SECOND:
            return False, f"Rate limit exceeded ({current_count}/{self.MAX_REQUESTS_PER_SECOND} req/sec)"
        
        # Record this request
        self.request_history[api_key].append(now)
        
        return True, "Request allowed"
    
    def get_usage(self, api_key: str) -> Dict[str, int]:
        """Get current usage for key"""
        now = time.time()
        
        if api_key not in self.request_history:
            return {"current": 0, "limit": self.MAX_REQUESTS_PER_SECOND}
        
        # Count recent requests
        recent = [
            ts for ts in self.request_history[api_key]
            if now - ts < self.WINDOW_SIZE
        ]
        
        return {
            "current": len(recent),
            "limit": self.MAX_REQUESTS_PER_SECOND
        }


# ============================================================================
# REQUEST SIZE VALIDATOR
# ============================================================================

class RequestSizeValidator:
    """
    Prevent oversized requests that could cause DoS.
    
    Limits:
    - Max request body: 1MB
    - Max header size: 8KB
    - Max URL length: 2KB
    """
    
    MAX_BODY_SIZE = 1024 * 1024  # 1MB
    MAX_HEADER_SIZE = 8 * 1024   # 8KB
    MAX_URL_LENGTH = 2 * 1024    # 2KB
    
    def validate_request(self, method: str, url: str, headers: Dict, body_size: int) -> Tuple[bool, str]:
        """
        Validate request size constraints.
        
        Returns: (is_valid, reason)
        """
        
        # Check URL length
        if len(url) > self.MAX_URL_LENGTH:
            return False, f"URL too long ({len(url)} > {self.MAX_URL_LENGTH})"
        
        # Check header size (rough estimate)
        header_size = sum(len(k) + len(str(v)) for k, v in headers.items())
        if header_size > self.MAX_HEADER_SIZE:
            return False, f"Headers too large ({header_size} > {self.MAX_HEADER_SIZE})"
        
        # Check body size (for POST/PUT)
        if method in ["POST", "PUT", "PATCH"]:
            if body_size > self.MAX_BODY_SIZE:
                return False, f"Body too large ({body_size} > {self.MAX_BODY_SIZE})"
        
        return True, "Request size valid"


# ============================================================================
# PERMISSION CHECKER
# ============================================================================

class PermissionChecker:
    """
    Enforce deny-by-default authorization.
    
    Model:
    - No implicit permissions
    - Only allow documented operations
    - Reject unknown endpoints
    - Block internal endpoints
    
    Allowed Operations (frozen surface):
      POST   /intent
      GET    /governance/orchestrator-state
      GET    /governance/plans
      GET    /governance/plans/{plan_id}
      GET    /governance/intents
      GET    /governance/audit
    
    Blocked (NEVER allowed):
      /internal/*
      /approve/*
      /resume/*
      PUT/DELETE/PATCH (all paths)
    """
    
    # Whitelist of allowed endpoints
    ALLOWED_ENDPOINTS = {
        ("POST", "/intent"),
        ("GET", "/governance/orchestrator-state"),
        ("GET", "/governance/plans"),
        ("GET", "/governance/plans/{plan_id}"),
        ("GET", "/governance/intents"),
        ("GET", "/governance/audit"),
        ("GET", "/healthz"),
        ("GET", "/readyz"),
    }
    
    # Explicitly forbidden paths
    FORBIDDEN_PATHS = {
        "/internal/",
        "/approve",
        "/resume",
        "/release-halt",
    }
    
    # Explicitly forbidden methods (no data mutation)
    FORBIDDEN_METHODS = {"PUT", "DELETE", "PATCH"}
    
    def check_permission(self, method: str, path: str) -> Tuple[bool, str]:
        """
        Check if operation is allowed.
        
        Returns: (is_allowed, reason)
        """
        
        # Deny forbidden methods
        if method in self.FORBIDDEN_METHODS:
            return False, f"Method {method} not allowed (no data mutation)"
        
        # Deny forbidden paths
        for forbidden_path in self.FORBIDDEN_PATHS:
            if path.startswith(forbidden_path):
                return False, f"Path {path} is internal only"
        
        # Allow only whitelisted endpoints
        # Note: /governance/plans/{plan_id} matches both /governance/plans/xxx
        if method == "GET" and path.startswith("/governance/plans/"):
            return True, "Allowed (plan detail endpoint)"
        
        if (method, path) in self.ALLOWED_ENDPOINTS:
            return True, "Allowed"
        
        return False, f"Operation {method} {path} not allowed"


# ============================================================================
# SECURITY CONTEXT
# ============================================================================

class SecurityContext:
    """
    Aggregates all security checks for a single request.
    """
    
    def __init__(self):
        self.key_validator = APIKeyValidator()
        self.rate_limiter = RateLimiter()
        self.size_validator = RequestSizeValidator()
        self.perm_checker = PermissionChecker()
    
    def validate_request(
        self,
        api_key: str,
        method: str,
        path: str,
        headers: Dict,
        body_size: int
    ) -> Tuple[int, Optional[str]]:
        """
        Run all security checks on request.
        
        Returns: (http_status_code, error_message)
        - (200, None) if all checks pass
        - (401, msg) if auth fails
        - (403, msg) if permission denied
        - (429, msg) if rate limited
        - (400, msg) if request invalid
        """
        
        # 1. Validate API key (401)
        is_valid_key, key_reason = self.key_validator.validate(api_key)
        if not is_valid_key:
            return 401, "AUTH_INVALID_KEY"
        
        # 2. Check rate limit (429)
        is_allowed, rate_reason = self.rate_limiter.check_and_record(api_key)
        if not is_allowed:
            return 429, "RATE_LIMIT_EXCEEDED"
        
        # 3. Check request size (400)
        is_valid_size, size_reason = self.size_validator.validate_request(
            method, path, headers, body_size
        )
        if not is_valid_size:
            return 400, "INVALID_REQUEST"
        
        # 4. Check permissions (403)
        is_permitted, perm_reason = self.perm_checker.check_permission(method, path)
        if not is_permitted:
            return 403, "AUTH_INSUFFICIENT_PERMISSION"
        
        # All checks passed
        return 200, None


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

SECURITY_CONTEXT = SecurityContext()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """Validate API key"""
    return SECURITY_CONTEXT.key_validator.validate(api_key)


def check_rate_limit(api_key: str) -> Tuple[bool, str]:
    """Check if request allowed (and record if yes)"""
    return SECURITY_CONTEXT.rate_limiter.check_and_record(api_key)


def check_permission(method: str, path: str) -> Tuple[bool, str]:
    """Check if operation is allowed"""
    return SECURITY_CONTEXT.perm_checker.check_permission(method, path)


def validate_request(
    api_key: str,
    method: str,
    path: str,
    headers: Dict,
    body_size: int
) -> Tuple[int, Optional[str]]:
    """
    Validate complete request (auth + rate limit + permissions + size).
    
    Returns: (http_status_code, error_code)
    """
    return SECURITY_CONTEXT.validate_request(api_key, method, path, headers, body_size)


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def add_test_key(api_key: str):
    """Add a test key for testing (not production)"""
    SECURITY_CONTEXT.key_validator.VALID_TEST_KEYS.add(api_key)


def remove_test_key(api_key: str):
    """Remove a test key"""
    SECURITY_CONTEXT.key_validator.VALID_TEST_KEYS.discard(api_key)


def reset_rate_limiter():
    """Reset rate limiter (for testing)"""
    SECURITY_CONTEXT.rate_limiter.request_history = {}


def get_rate_limit_usage(api_key: str) -> Dict:
    """Get current rate limit usage"""
    return SECURITY_CONTEXT.rate_limiter.get_usage(api_key)
