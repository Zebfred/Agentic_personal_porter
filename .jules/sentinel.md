## 2024-05-24 - API Key Timing Attack Vulnerability
**Vulnerability:** The API key validation used a simple string comparison (`!=`) which is vulnerable to timing attacks. An attacker could potentially guess the API key by measuring the time it takes for the server to respond, as the string comparison returns `False` as soon as it finds a mismatching character.
**Learning:** Security-sensitive string comparisons like API keys, tokens, or passwords must use constant-time comparison functions to prevent timing attacks.
**Prevention:** Always use `hmac.compare_digest()` or a similar constant-time comparison function when checking sensitive tokens or passwords.
