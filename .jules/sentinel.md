## 2026-03-22 - Secure API Key Comparison
**Vulnerability:** Timing attack vulnerability in `src/app.py`'s `require_api_key` decorator. API keys were compared using standard string comparison `!=`, which could leak the correct key's length and character values over many requests.
**Learning:** Custom authentication decorators should always use constant-time comparison methods, not standard equality operators, to prevent timing side channels.
**Prevention:** Use `hmac.compare_digest()` for string comparisons involving secrets (passwords, tokens, API keys).
## 2025-03-22 - [Timing Attack Vulnerability in Authentication]
**Vulnerability:** A non-constant time string comparison (`==`) was used for both API key checking and user login in `src/app.py`. This exposes the application to timing attacks, allowing attackers to potentially brute-force keys by analyzing response times.
**Learning:** Even seemingly standard string comparisons are not secure for sensitive secrets like passwords or API keys.
**Prevention:** Always use `hmac.compare_digest()` for comparing secrets, tokens, or passwords to ensure constant-time verification.
## 2024-05-24 - Remove Hardcoded Secrets from Codebase
 **Vulnerability:** Hardcoded fallback values for `PORTER_API_KEY` and `JWT_SECRET` in `src/app.py` would allow application to boot up with easily guessable default values if the environment variables were inadvertently missed. This creates a risk of authentication bypass.
 **Learning:** Fallbacks for highly sensitive values might seem like a convenience for local development, but they can easily lead to a production instance running with well-known compromised secrets.
 **Prevention:** For critical security values like API Keys and JWT secrets, it's safer to have the application fail fast (e.g., raise a `ValueError`) on startup if the required environment variables are absent, preventing it from ever running in an insecure state.
