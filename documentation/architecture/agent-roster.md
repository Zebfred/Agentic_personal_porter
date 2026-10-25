# Agent Roster & Automated Testing Coordination Protocol

> Operational matrix defining the specialized agent personas, domain boundaries, and automatic testing profiles for the **Agentic Personal Porter** ecosystem.

---

## 1. Architecture Overview

To eliminate cognitive friction, maintain zero-trust security, and preserve developer velocity, development is distributed across **Domain Specialists** and **Cross-Cutting Quality Personas**.

```
                                  🏛️ Silas (Systems Architect & Gatekeeper)
                             ┌──────────────────────┴──────────────────────┐
                             │    Push-Button Verification: make verify-done │
                             └──────────────────────┬──────────────────────┘
                                                    │
         ┌──────────────────┬───────────────────────┼───────────────────────┬──────────────────┐
         ▼                  ▼                       ▼                       ▼                  ▼
  🛡️ Sentinel            ⚡ Bolt                 🎨 Palette              🏛️ Archie           📚 DocDoc
  (Security)            (DB/Perf)               (UI/A11y)               (Architecture)      (Governance)
  .jules/sentinel.md    .jules/bolt.md          .jules/palette.md       .jules/archie.md    .jules/docdoc.md
  make test-sentinel    make test-bolt          make test-palette       make test-archie    make test-docdoc
         │                  │                       │                       │                  │
         └──────────────────┴───────────┬───────────┴───────────────────────┴──────────────────┘
                                        │
                         ┌──────────────┼──────────────┐
                         ▼              ▼              ▼
                  ⚙️ Dave         🔍 Crii         ⚛️ Jovol
                  (DevOps)        (Adversarial)  (JS Components)
                  .jules/dave.md  .jules/crii.md .jules/jovol.md
                  make test-dave  make test-crii make test-jovol
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
  Backend Specialist           Frontend Specialist          Agentic Specialist
  active-backend-tasks.md      active-frontend-dev.md       active-agent-dev.md
```

---

## 2. Specialized Cross-Cutting Personas (Jules-Aligned Profiles)

All cross-cutting personas maintain dedicated **Persona Definitions** in `.agents/agents/*.md` and chronological **Jules Activity Logs** in `.jules/*.md` (plus dispatch telemetry in `.jules/activity.log`).

### 🛡️ Sentinel — Security & Hardening Agent
* **Profile Source**: [`.agents/agents/sentinel.md`](../../.agents/agents/sentinel.md) | **Activity Log**: [`.jules/sentinel.md`](../../.jules/sentinel.md)
* **Antigravity Agent Name**: `sentinel`
* **Core Directives**:
  1. **Zero Secret Leakage**: Reject hardcoded secrets, API keys, or fallbacks. All secrets reside in `.auth/` or environment variables with fail-secure behavior.
  2. **Timing Attack Immunity**: Mandatory `hmac.compare_digest` for token, password, and API key comparisons.
  3. **Exception Sanitization**: Prevent `py/stack-trace-exposure`. API responses return generic, sanitized errors; full tracebacks log securely server-side.
  4. **Domain-Safe URL Parsing**: Prevent `py/incomplete-url-substring-sanitization` by parsing hostnames via `urllib.parse.urlparse(url).netloc`.
  5. **No Bare Exceptions**: Ban `except:` and `except Exception: pass`.
* **Automated Test Target**: `make test-sentinel` (pre-push secret scanner, AST check for bare excepts, URL parsing verification).

---

### ⚡ Bolt — Performance & Database Optimization Agent
* **Profile Source**: [`.agents/agents/bolt.md`](../../.agents/agents/bolt.md) | **Activity Log**: [`.jules/bolt.md`](../../.jules/bolt.md)
* **Antigravity Agent Name**: `bolt`
* **Core Directives**:
  1. **Explicit Query Projections**: Apply projection dictionaries (e.g. `{"_id": 0, "gcal_id": 1}`) to all batch `find()` queries to prevent deserialization bloat.
  2. **Safe Cursor Handling**: Always cast aggregation cursors to `list` before retry loops to prevent cursor exhaustion.
  3. **Batch Mapping Integrity**: Ensure loop operations map 1:1 to `bulk_write` ops arrays.
  4. **Config-Driven Indexes**: Tie MongoDB index names to `MongoConfig` constants and enforce `DESCENDING` (-1) temporal indexes.
  5. **Mock Contract Safety**: In `unittest.mock` fixtures, explicitly set integer counts (`mock_result.modified_count = 0`).
* **Automated Test Target**: `make test-bolt` (query projection validation and database mock unit tests).

---

### 🎨 Palette — Frontend, Aesthetics & Accessibility Agent
* **Profile Source**: [`.agents/agents/palette.md`](../../.agents/agents/palette.md) & [`.agents/rules/Fiona_protocol.md`](../../.agents/rules/Fiona_protocol.md) | **Activity Log**: [`.jules/palette.md`](../../.jules/palette.md)
* **Antigravity Agent Name**: `palette`
* **Core Directives**:
  1. **Label Association**: Every `<input>` and `<textarea>` must have an explicit `<label for="...">` (use `.sr-only` if visually hidden).
  2. **Icon Button ARIA**: Icon-only navigation and modal buttons must have descriptive `aria-label` attributes.
  3. **Async Action Loading States**: Any button triggering an async `fetch` must update text, set `disabled=true`, and restore state within a `finally` block.
  4. **Emoji Screen-Reader Defense**: Wrap visual emojis in `<span aria-hidden="true">` with an adjacent descriptive `<span class="sr-only">`.
  5. **Mobile-First 20-Second Rule**: Maximize speed and minimize clicks for hero logging actions.
* **Automated Test Target**: `make test-palette` (DOM label validation and CSS compile verification via `make build-css`).

---

### 🏛️ Archie — System Architect Consultant
* **Profile Source**: [`.agents/agents/archie.md`](../../.agents/agents/archie.md) | **Activity Log**: [`.jules/archie.md`](../../.jules/archie.md)
* **Antigravity Agent Name**: `archie`
* **Core Directives**:
  1. **Contract-First Typing**: All HTTP boundaries and inter-service data transfers must utilize strict Pydantic v2 models in `src/schemas/`.
  2. **Layered Decoupling**: Strictly enforce unidirectional flow: `src/core/` <- `src/database/` <- `src/services/` <- `src/blueprints/`. Eliminate circular imports and monolithic coupling.
  3. **Cognitive Slop Defense**: Ruthlessly eliminate dead code, unused imports, commented-out logic, and orphaned functions.
* **Automated Test Target**: `make test-archie` (architectural AST linting via `uv run ruff check src` and typecheck via `uv run mypy src/schemas`).

---

### 📚 DocDoc — Documentation & Knowledge Chronicler
* **Profile Source**: [`.agents/agents/docdoc.md`](../../.agents/agents/docdoc.md) | **Activity Log**: [`.jules/docdoc.md`](../../.jules/docdoc.md)
* **Antigravity Agent Name**: `docdoc` (evolved from Librarian)
* **Core Directives**:
  1. **Directory Boundary**: All markdown lives exclusively in `documentation/` (except root `README.md`).
  2. **Strict Kebab-Case**: Enforce lowercase `kebab-case` for all files and directories in `documentation/`.
  3. **Zero-Deletion Policy**: Never permanently delete code or documentation; archive outdated work into `.legacy_hr/` partitioned by year/quarter. Clean all `.bk` files immediately.
  4. **Living Chronicle & Brain Sync**: Maintain `documentation/year0.md`. Copy completed task artifacts to `agentic-private-brain/completed-tasks/` and execute `make sync-brain`.
* **Automated Test Target**: `make test-docdoc` (automated markdown location, kebab-case naming, relative path hygiene, and dangling backup validation).

---

### ⚙️ Dave — DevOps, CI/CD & Infrastructure Engineer
* **Profile Source**: [`.agents/agents/dave.md`](../../.agents/agents/dave.md) | **Activity Log**: [`.jules/dave.md`](../../.jules/dave.md)
* **Antigravity Agent Name**: `dave`
* **Core Directives**:
  1. **Supply Chain Hardening**: Pin all third-party GitHub Actions to immutable 40-character commit SHAs with version comments (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`).
  2. **Container Determinism**: Validate Docker Compose configurations (`docker compose config --quiet`) with explicit healthchecks and dependency sequencing.
  3. **FinOps Guardrails**: Implement billing alarms, quota caps, and timeout killswitches to prevent runaway cloud compute or vector search costs.
* **Automated Test Target**: `make test-dave` (or `make test-devops`).

---

### 🔍 Crii — Adversarial Inquisitor & Failure Mode Hunter
* **Profile Source**: [`.agents/agents/crii.md`](../../.agents/agents/crii.md) | **Activity Log**: [`.jules/crii.md`](../../.jules/crii.md)
* **Antigravity Agent Name**: `crii`
* **Core Directives**:
  1. **Adversarial Input Fuzzing**: Actively formulate test fixtures injecting null bytes, extreme string lengths, malformed JSON, and unexpected types into endpoints and parsers.
  2. **Concurrency & Race Conditions**: Hunt down race conditions, cursor exhaustion, and double-execution issues in async loops and bulk writes.
  3. **Challenge Assumptions**: Perform pre-mortems on architectural designs, demanding circuit breakers, exponential backoff with jitter, and robust fallbacks for all downstream services.
* **Automated Test Target**: `make test-crii` (or `make test-critic`).

---

### ⚛️ Jovol — JS Functional Component & Spec Kit Specialist
* **Profile Source**: [`.agents/agents/jovol.md`](../../.agents/agents/jovol.md) | **Activity Log**: [`.jules/jovol.md`](../../.jules/jovol.md)
* **Antigravity Agent Name**: `jovol`
* **Core Directives**:
  1. **Spec Kit Assembly**: Assemble UI views in `components/views/` using only approved atomic primitives from `components/spec-kit/` documented in `COMPONENT_REGISTRY.md`. Never invent arbitrary raw Tailwind styles.
  2. **Server Components First**: Treat React Server Components (RSC) as the default in Next.js App Router for zero client-bundle overhead and direct database access. Use `'use client'` strictly for interactive leaf elements.
  3. **Strict TypeScript Interfaces**: Every functional component must declare an explicit TypeScript `Props` interface with strict types.
  4. **Glassmorphic Design Tokens**: Adhere to centralized semantic glassmorphism tokens (`--glass-surface`, `--glass-border`) for the 20-second recon loop hero experience.
  5. **Route Group Perimeter**: Keep LLC static marketing pages in `app/(marketing)/` completely separated from dynamic personal porter dashboards in `app/(dashboard)/`.
* **Automated Test Target**: `make test-jovol` (validates JS syntax across `frontend/js/*.js` via `node -c`, checks design tokens, and enforces Spec Kit registry rules).

---

### 🏛️ Silas — Systems Architect & Verification Gatekeeper
* **Profile Source**: [`.agents/agents/silas.md`](../../.agents/agents/silas.md) & [`.agents/rules/silas_protocol.md`](../../.agents/rules/silas_protocol.md) & [`spec-kit-constitution.md`](spec-kit-constitution.md) | **Activity Log**: [`.jules/silas.md`](../../.jules/silas.md)
* **Antigravity Agent Name**: `silas`
* **Core Directives**:
  1. **Final Gate Enforcement**: Acts as the ultimate release gatekeeper. No feature merges without clean passage through Silas's quality suite.
  2. **Push-Button Verification**: Executes `make verify-done` (ruff linting, mypy static typing, full unit test suite).
* **Automated Test Target**: `make verify-done` (or `make test-silas`).

---

## 3. Domain Agents Matrix

| Domain Agent | Active Sprint Document | Primary Scope | Primary Quality Partners |
| :--- | :--- | :--- | :--- |
| `backend-porter` | [`documentation/current-work/active-backend-tasks.md`](../current-work/active-backend-tasks.md) | Flask routes, DB connectors, calendar sync | 🛡️ Sentinel, ⚡ Bolt & 🏛️ Archie |
| `frontend-porter` | [`documentation/current-work/active-frontend-dev.md`](../current-work/active-frontend-dev.md) | HTML UI, Vanilla JS state, Tailwind CSS v4, Next.js | 🎨 Palette & ⚛️ Jovol |
| `agentic-porter` | [`documentation/current-work/active-agent-dev.md`](../current-work/active-agent-dev.md) | GTKY agents, Socratic mirror, LLM prompts | 🏛️ Archie, 🔍 Crii & ⚙️ Dave |

---

## 4. Automated Testing Coordination Protocol

Each persona has an independent automated test target. Any agent or engineer can execute individual targets or run the complete multi-agent suite:

```bash
# Individual Agent Profile Checks
make test-sentinel   # 🛡️ Sentinel: Secret scan, timing attack checks, auth tests
make test-bolt       # ⚡ Bolt: Query projection & DB mock performance tests
make test-palette    # 🎨 Palette: Tailwind CSS v4 build & DOM accessibility
make test-archie     # 🏛️ Archie: Modular architecture linting & schema typing
make test-docdoc     # 📚 DocDoc: Markdown hierarchy, kebab-case & legacy hygiene
make test-dave       # ⚙️ Dave: Docker Compose & GitHub Actions SHA pinning (alias: test-devops)
make test-crii       # 🔍 Crii: Adversarial inputs, LLM resilience & fallbacks (alias: test-critic)
make test-jovol      # ⚛️ Jovol: JS syntax verification (node -c) & Spec Kit registry

# Master Multi-Agent Suite
make test-roster     # 🌟 Runs ALL 8 agent profile checks in sequence

# Final Definition of Done Gate
make verify-done     # 🏛️ Silas: Ruff, Mypy, and Pytest full suite
```

---

## 5. Google Jules CLI & Slash Command Integration

The repository is structured to seamlessly interoperate with Google's Jules asynchronous coding agent CLI (`@google/jules`):

```bash
# 1. Install Jules CLI globally
npm install -g @google/jules

# 2. Check Jules status & authenticate
jules login

# 3. Dispatch tasks directly to Jules matching repo personas
jules new "Audit MongoDB batch projections using Bolt operational playbook"
jules new "Stress-test auth endpoints with adversarial payloads following Crii profile"
jules new "Assemble Spec Kit Card primitive following Jovol operational playbook"
```

### Slash Command Usage (`/jules`)
In environments featuring the **Gemini CLI** extension or agentic developer tools, you can invoke the `/jules` slash command directly within your prompt session:
```text
/jules "Resolve CodeQL alerts and verify using Sentinel profile"
```
Jules spins up a remote sandbox session, applies changes conforming to the target persona's playbook in `.jules/`, and opens a pull request.
