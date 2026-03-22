## 2026-03-22 - Secure API Key Comparison
**Vulnerability:** Timing attack vulnerability in `src/app.py`'s `require_api_key` decorator. API keys were compared using standard string comparison `!=`, which could leak the correct key's length and character values over many requests.
**Learning:** Custom authentication decorators should always use constant-time comparison methods, not standard equality operators, to prevent timing side channels.
**Prevention:** Use `hmac.compare_digest()` for string comparisons involving secrets (passwords, tokens, API keys).
