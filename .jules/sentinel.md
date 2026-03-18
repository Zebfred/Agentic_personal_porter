## 2025-02-14 - Fix Insecure Deserialization of Google Calendar Tokens
**Vulnerability:** Google Calendar credentials were being serialized and stored as a `pickle` file (`token.pickle`).
**Learning:** `pickle` deserialization can result in arbitrary code execution if the file is tampered with by an attacker.
**Prevention:** Always use secure, language-agnostic data serialization formats like JSON (via `Credentials.from_authorized_user_file` and `to_json()`) instead of binary `pickle` objects to store sensitive user credentials or states.
