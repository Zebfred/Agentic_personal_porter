# Quickstart: Evaluating Mach 4 Transition Readiness

**Feature**: Evaluate Current State for Mach 4 Transition
**Date**: 2026-10-04

---

## 1. Prerequisites

Ensure your environment is properly activated:
```bash
# Activate conda environment
conda activate agentic_porter

# Verify python version (3.12+)
python --version

# Verify uv is installed
uv --version
```

---

## 2. Running Diagnostic Audits

### Step 1: Verify Zero-Trust & Tenancy Scoping
Scan the codebase to verify that `request.user_email` is enforced and legacy `HERO_NAME` calls are eradicated:
```bash
# Check for any active single-tenant HERO_NAME references
grep -rn "HERO_NAME" src/ || echo "✓ No active HERO_NAME references in src/"
```

### Step 2: Database Connection & Ingestion Verification
Test local MongoDB and Neo4j connectivity:
```bash
# Verify Neo4j connection pool singleton
uv run python -c "from src.database.neo4j_db import get_neo4j_driver; d = get_neo4j_driver(); print('✓ Neo4j driver initialized:', d)"

# Verify MongoDB collections & indices
uv run python -c "from src.database.mongo_storage import MongoStorage; m = MongoStorage(); print('✓ MongoDB connected:', m.client.server_info()['version'])"
```

### Step 3: Frontend Accessibility Audit
Verify that icon-only navigation controls have descriptive accessible labeling:
```bash
# Audit icon buttons in frontend HTML files
grep -rn "button" frontend/*.html | grep -v "aria-label" || echo "✓ Review complete"
```

---

## 3. Interpreting Results against Constitution Gates

| Gate Check | Required Result | Remediation if Failed |
| :--- | :--- | :--- |
| **Principle I: Zero-Trust** | Secrets in `.auth/` only; no dev fallbacks; constant-time auth (`hmac.compare_digest`). | Move secrets to `.auth/.env`; replace `==` with `hmac.compare_digest`. |
| **Principle II: Multi-Tenancy** | All queries and routes derive tenant from `request.user_email`. | Remove hardcoded identity strings; pass `user_email` context. |
| **Principle III: Database Discipline** | Neo4j singleton pool; MongoDB batched `bulk_write`. | Eliminate per-request driver closures; replace iterative updates with bulk writes. |
| **Principle IV: 20-Second Recon** | Recon flows $\le 3$ clicks; WCAG A11y labels present. | Add `aria-label` to icon buttons; simplify verification steps. |
| **Principle VI: Documentation** | All `.md` files in `documentation/` using `kebab-case.md`. | Move to `documentation/` and rename with kebab-case. |
| **Principle VIII: Preset Supremacy** | Local constitution at `.specify/memory/constitution.md` takes precedence. | Verify symlink points to `documentation/architecture/spec-kit-constitution.md`. |
