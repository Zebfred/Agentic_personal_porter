"""Multi-tenant identity resolution and boundary sanitization helpers (T109)."""

from dataclasses import dataclass
import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAX_USERNAME_LEN = 64
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_SLUG_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class TenantContext:
    """Immutable authenticated tenant context derived from JWT/API-key middleware."""

    user_email: str
    username: str
    user_role: str = "user"


def contains_null_bytes(value: Any) -> bool:
    """Recursively detect NUL byte injection inside request payloads or query values."""
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(contains_null_bytes(k) or contains_null_bytes(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(contains_null_bytes(item) for item in value)
    return False


def sanitize_tenant_username(raw_value: Any) -> str | None:
    """Normalize a candidate tenant username into a safe bounded identifier."""
    if not isinstance(raw_value, str) or "\x00" in raw_value:
        return None
    cleaned = _CONTROL_CHARS_RE.sub("", raw_value).strip()
    if not cleaned:
        return None
    slug = _SAFE_SLUG_RE.sub("_", cleaned).strip("._-")
    if not slug:
        return None
    return slug[:_MAX_USERNAME_LEN]


def derive_fallback_username(user_email: str | None) -> str:
    """Derive a deterministic, tenant-isolated fallback username from user_email."""
    if not isinstance(user_email, str) or not user_email.strip():
        return "Hero"
    normalized = user_email.strip()
    lowered = normalized.lower()
    if lowered == "hero":
        return "Hero"
    if lowered == "system_script@localhost":
        return "system"
    local_part = normalized.split("@", 1)[0]
    candidate = sanitize_tenant_username(local_part)
    if candidate:
        return candidate
    digest = hashlib.sha256(lowered.encode("utf-8")).hexdigest()[:10]
    return f"tenant_{digest}"


def resolve_tenant_username(
    user_email: str | None,
    *,
    jwt_username: str | None = None,
    mongo_storage: Any = None,
) -> str:
    """Resolve authenticated tenant username via Mongo profile, JWT claim, or safe fallback."""
    cleaned_email = user_email.strip() if isinstance(user_email, str) else ""

    if cleaned_email and cleaned_email.lower() not in {"hero", "system_script@localhost"}:
        try:
            storage = mongo_storage
            if storage is None:
                from src.database.mongo_storage import SovereignMongoStorage

                storage = SovereignMongoStorage()
            user_doc = storage.get_user_by_email(cleaned_email)
            if isinstance(user_doc, dict):
                doc_username = sanitize_tenant_username(user_doc.get("username"))
                if doc_username:
                    return doc_username
        except Exception as exc:
            logger.debug("Tenant username lookup fallback for %s: %s", cleaned_email, exc)

    safe_jwt = sanitize_tenant_username(jwt_username)
    if safe_jwt:
        return safe_jwt

    return derive_fallback_username(cleaned_email or None)


def resolve_request_tenant(req: Any, *, mongo_storage: Any = None) -> TenantContext | None:
    """Extract authenticated TenantContext strictly from Flask request auth attributes."""
    raw_email = getattr(req, "user_email", None)
    if not isinstance(raw_email, str) or not raw_email.strip() or "\x00" in raw_email:
        return None
    user_email = raw_email.strip()
    jwt_username = getattr(req, "user_username", None)
    username = resolve_tenant_username(
        user_email,
        jwt_username=jwt_username,
        mongo_storage=mongo_storage,
    )
    raw_role = getattr(req, "user_role", "user")
    return TenantContext(
        user_email=user_email,
        username=username,
        user_role=raw_role if isinstance(raw_role, str) else "user",
    )
