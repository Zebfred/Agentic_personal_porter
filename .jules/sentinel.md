## 2025-03-22 - [Timing Attack Vulnerability in Authentication]
**Vulnerability:** A non-constant time string comparison (`==`) was used for both API key checking and user login in `src/app.py`. This exposes the application to timing attacks, allowing attackers to potentially brute-force keys by analyzing response times.
**Learning:** Even seemingly standard string comparisons are not secure for sensitive secrets like passwords or API keys.
**Prevention:** Always use `hmac.compare_digest()` for comparing secrets, tokens, or passwords to ensure constant-time verification.
