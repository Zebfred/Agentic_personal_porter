July 5th
- address: items with UI
- [x] address outdated style.css (Verified via `make build-css` / `make test-palette`)
  * Note: Committed style.css is stale (missing border-indigo-200, from-indigo-50, to-blue-50 added in Adventure_Time_log.html, and retaining unused invisible, lowercase). Rebuilding via 'npm run build:css' compiles these correctly.
- [x] address failing check on github (Verified: fixed mongomock fixture, GitHub Action 40-char SHAs, and Python 3.14 chromadb~=1.5.9 compatibility)