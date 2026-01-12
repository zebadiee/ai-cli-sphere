#!/usr/bin/env python3
"""
Gateway auth copy (for simple gateway build context).
This is a direct copy of `ct-dev/gateway_auth.py` content so the lightweight gateway can use it.
"""

import time
from typing import Dict, Tuple, Optional

class APIKeyValidator:
    VALID_TEST_KEYS = {
        "sk_test_12345",
        "sk_test_abcde",
        "sk_test_valid",
        "sk_test_validation_key_1234567890ab",
    }
    VALID_PROD_KEYS = set()

    def __init__(self):
        self.key_metadata = {}

    def validate(self, api_key: str) -> Tuple[bool, str]:
        if not api_key or not isinstance(api_key, str):
            return False, "Invalid key format"
        if api_key in self.VALID_TEST_KEYS:
            self._record_access(api_key)
            return True, "Valid test key"
        if api_key in self.VALID_PROD_KEYS:
            self._record_access(api_key)
            return True, "Valid production key"
        return False, "API key not found"

    def _record_access(self, api_key: str):
        if api_key not in self.key_metadata:
            self.key_metadata[api_key] = {"created": time.time(), "last_used": time.time(), "usage_count": 1}
        else:
            meta = self.key_metadata[api_key]
            meta["last_used"] = time.time()
            meta["usage_count"] += 1


class RateLimiter:
    MAX_REQUESTS_PER_SECOND = 10
    WINDOW_SIZE = 1.0

    def __init__(self):
        self.request_history = {}

    def check_and_record(self, api_key: str) -> Tuple[bool, str]:
        now = time.time()
        if api_key not in self.request_history:
            self.request_history[api_key] = []
        self.request_history[api_key] = [ts for ts in self.request_history[api_key] if now - ts < self.WINDOW_SIZE]
        if len(self.request_history[api_key]) >= self.MAX_REQUESTS_PER_SECOND:
            return False, "Rate limit exceeded"
        self.request_history[api_key].append(now)
        return True, "Allowed"


class RequestSizeValidator:
    MAX_BODY_SIZE = 1024 * 1024
    MAX_HEADER_SIZE = 8 * 1024
    MAX_URL_LENGTH = 2 * 1024

    def validate_request(self, method: str, url: str, headers: Dict, body_size: int) -> Tuple[bool, str]:
        if len(url) > self.MAX_URL_LENGTH:
            return False, "URL too long"
        header_size = sum(len(k) + len(str(v)) for k, v in headers.items())
        if header_size > self.MAX_HEADER_SIZE:
            return False, "Headers too large"
        if method in ["POST", "PUT", "PATCH"] and body_size > self.MAX_BODY_SIZE:
            return False, "Body too large"
        return True, "OK"


class PermissionChecker:
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
    FORBIDDEN_PATHS = {"/internal/", "/approve", "/resume", "/release-halt"}
    FORBIDDEN_METHODS = {"PUT", "DELETE", "PATCH"}

    def check_permission(self, method: str, path: str) -> Tuple[bool, str]:
        # Normalize path to strip query parameters
        path = path.split('?', 1)[0]
        if method in self.FORBIDDEN_METHODS:
            return False, "Method not allowed"
        for forbidden in self.FORBIDDEN_PATHS:
            if path.startswith(forbidden):
                return False, "Path internal"
        if method == "GET" and path.startswith("/governance/plans/"):
            return True, "Allowed"
        if (method, path) in self.ALLOWED_ENDPOINTS:
            return True, "Allowed"
        return False, "Not permitted"


class SecurityContext:
    def __init__(self):
        self.key_validator = APIKeyValidator()
        self.rate_limiter = RateLimiter()
        self.size_validator = RequestSizeValidator()
        self.perm_checker = PermissionChecker()

    def validate_request(self, api_key: str, method: str, path: str, headers: Dict, body_size: int) -> Tuple[int, Optional[str]]:
        is_valid_key, _ = self.key_validator.validate(api_key)
        if not is_valid_key:
            return 401, "AUTH_INVALID_KEY"
        is_allowed, _ = self.rate_limiter.check_and_record(api_key)
        if not is_allowed:
            return 429, "RATE_LIMIT_EXCEEDED"
        is_valid_size, _ = self.size_validator.validate_request(method, path, headers, body_size)
        if not is_valid_size:
            return 400, "INVALID_REQUEST"
        is_permitted, _ = self.perm_checker.check_permission(method, path)
        if not is_permitted:
            return 403, "AUTH_INSUFFICIENT_PERMISSION"
        return 200, None


SECURITY_CONTEXT = SecurityContext()


def validate_request(api_key: str, method: str, path: str, headers: Dict, body_size: int) -> Tuple[int, Optional[str]]:
    return SECURITY_CONTEXT.validate_request(api_key, method, path, headers, body_size)
