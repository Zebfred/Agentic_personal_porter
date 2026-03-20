## 2025-03-20 - Hardcoded API Key & Insecure String Comparison Fix
**Vulnerability:** A hardcoded default API key `"default_dev_key"` was present in `src/app.py` for `PORTER_API_KEY`. Additionally, string comparison `!=` was used for evaluating the API key, which is susceptible to timing attacks.
**Learning:** Hardcoded default secrets are risky and string evaluation for cryptographic keys can lead to timing attacks. The application used an insecure fallback instead of failing securely when environment configuration is incomplete.
**Prevention:** Always raise an exception when critical secrets are missing from the environment. Always use `hmac.compare_digest` for secure, constant-time comparison of secrets or tokens.
