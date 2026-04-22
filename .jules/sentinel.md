## 2025-02-14 - Fix Insecure Deserialization of Google Calendar Tokens
**Vulnerability:** Google Calendar credentials were being serialized and stored as a `pickle` file (`token.pickle`).
**Learning:** `pickle` deserialization can result in arbitrary code execution if the file is tampered with by an attacker.
**Prevention:** Always use secure, language-agnostic data serialization formats like JSON (via `Credentials.from_authorized_user_file` and `to_json()`) instead of binary `pickle` objects to store sensitive user credentials or states.
## 2025-03-19 - Flask Debugger Exposed to 0.0.0.0
**Vulnerability:** The Flask app was hardcoded to run with `debug=True` and `host='0.0.0.0'` in `src/app.py`. This exposes the Werkzeug interactive debugger to any network interface, allowing potential Remote Code Execution (RCE) and sensitive data leakage if an error occurs.
**Learning:** Hardcoded debug configurations in entry point files are a common and critical security flaw, especially when the application is bound to all public interfaces (`0.0.0.0`). It must always be configurable via environment variables and default to `False`.
**Prevention:** Never hardcode `debug=True` in production-facing web servers. Use `os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'` to conditionally enable debugging only in local development environments.
## 2025-03-20 - Hardcoded API Key & Insecure String Comparison Fix
**Vulnerability:** A hardcoded default API key `"default_dev_key"` was present in `src/app.py` for `PORTER_API_KEY`. Additionally, string comparison `!=` was used for evaluating the API key, which is susceptible to timing attacks.
**Learning:** Hardcoded default secrets are risky and string evaluation for cryptographic keys can lead to timing attacks. The application used an insecure fallback instead of failing securely when environment configuration is incomplete.
**Prevention:** Always raise an exception when critical secrets are missing from the environment. Always use `hmac.compare_digest` for secure, constant-time comparison of secrets or tokens.
## 2024-05-24 - API Key Timing Attack Vulnerability
**Vulnerability:** The API key validation used a simple string comparison (`!=`) which is vulnerable to timing attacks. An attacker could potentially guess the API key by measuring the time it takes for the server to respond, as the string comparison returns `False` as soon as it finds a mismatching character.
**Learning:** Security-sensitive string comparisons like API keys, tokens, or passwords must use constant-time comparison functions to prevent timing attacks.
**Prevention:** Always use `hmac.compare_digest()` or a similar constant-time comparison function when checking sensitive tokens or passwords.
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
## 2025-03-22 - Fix Unauthenticated Access to Cloud Infrastructure Endpoints
**Vulnerability:** The `/wake_infrastructure` endpoint in `src/routes/admin_routes.py` lacked the `@require_api_key` decorator, allowing unauthenticated attackers to wake up cloud compute instances, potentially leading to denial-of-wallet (cost-based DoS) attacks.
**Learning:** Endpoints that trigger actions with real-world cost implications (like waking compute resources) must be treated as sensitive and always protected behind robust authentication, even if they seem innocuous or are meant for "stealth" frontend triggers.
**Prevention:** Ensure all administrative or operational endpoints have the `@require_api_key` or equivalent authentication decorator applied. Additionally, always test frontend integration of new authenticated endpoints using the designated secure fetch wrappers (e.g., `window.Auth.fetchWithAuth`).
