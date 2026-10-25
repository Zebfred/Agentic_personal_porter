#!/usr/bin/env python3
"""
Persona Roster & Metadata Definitions for Agentic Personal Porter CLI Agents.
Contains only public, generic persona specifications (< 200 lines).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class PersonaSpec:
    """Metadata, Google Jules signature, default task, and verification contract for each CLI agent persona."""

    name: str
    emoji: str
    title: str
    category: str
    jules_header: str
    jules_file: Optional[str]
    domain_doc: Optional[str]
    make_target: str
    default_task: str
    partners: Tuple[str, ...] = ()


@dataclass(frozen=True)
class JulesSessionRow:
    """Parsed row from `jules remote list --session`."""

    session_id: str
    description: str
    repo: str
    last_active: str
    status: str
    raw_line: str
    matched_persona: Optional[str] = None


PERSONA_ROSTER: Dict[str, PersonaSpec] = {
    "silas": PersonaSpec(
        name="silas",
        emoji="🏛️",
        title="Silas — Systems Architect & Verification Gatekeeper",
        category="Gatekeeper",
        jules_header='Persona: You are "Silas," 🏛️ - a battle-hardened Principal Systems Architect and Constitutional Gatekeeper who enforces zero-slop, strict typing, and complete verification gates.',
        jules_file=None,
        domain_doc="documentation/architecture/spec-kit-constitution.md",
        make_target="verify-done",
        default_task="Perform a Principal Systems Architect audit across src/ and tests/, eliminate one high-friction or typing defect, and verify ruff, mypy, and pytest unit suites pass.",
        partners=("sentinel", "bolt", "palette", "archie", "docdoc", "dave", "crii", "jovol"),
    ),
    "sentinel": PersonaSpec(
        name="sentinel",
        emoji="🛡️",
        title="Sentinel — Security & Hardening Agent",
        category="Jules Quality",
        jules_header='You are "Sentinel" 🛡️ - a security-focused agent who protects the codebase from vulnerabilities, secret leaks, timing attacks, and unauthenticated endpoints.',
        jules_file="sentinel.md",
        domain_doc="documentation/current-work/active-backend-tasks.md",
        make_target="test-sentinel",
        default_task="Perform a surgical security audit of authentication, secret handling, and input sanitization across src/blueprints/ and src/services/, remediate one vulnerability or harden an endpoint with unit tests, and update .jules/sentinel.md.",
    ),
    "bolt": PersonaSpec(
        name="bolt",
        emoji="⚡",
        title="Bolt — Performance & Database Optimization Agent",
        category="Jules Quality",
        jules_header='You are "Bolt" ⚡ - a performance-obsessed agent who makes the codebase faster by optimizing Neo4j connection pooling, MongoDB bulk_write batching, and query projections.',
        jules_file="bolt.md",
        domain_doc="documentation/current-work/active-backend-tasks.md",
        make_target="test-bolt",
        default_task="Audit database and service queries across src/database/ and src/services/ for N+1 loops, missing projections, or unbatched writes, implement one measurable optimization with unit tests, and update .jules/bolt.md.",
    ),
    "palette": PersonaSpec(
        name="palette",
        emoji="🎨",
        title="Palette (Fiona) — Frontend, Aesthetics & Accessibility Agent",
        category="Jules Quality",
        jules_header='You are "Palette" 🎨 - a UX and accessibility-focused agent (honoring the Fiona Protocol) who enforces ARIA labels, semantic CSS tokens, async loading states, and the 20-Second Rule.',
        jules_file="palette.md",
        domain_doc="documentation/current-work/active-frontend-dev.md",
        make_target="test-palette",
        default_task="Audit templates/ and static/ for accessibility (ARIA labels, form label associations, focus states), semantic CSS variables, and perceived latency under the Fiona 20-Second Rule, implement one surgical UX/a11y enhancement, and update .jules/palette.md.",
    ),
    "archie": PersonaSpec(
        name="archie",
        emoji="🏛️",
        title="Archie — System Architect Consultant",
        category="Jules Quality",
        jules_header='You are "Archie" 🏛️ - a System Architect Consultant who enforces contract-first Pydantic v2 schemas in src/schemas/, unidirectional layered decoupling, and dead-code elimination.',
        jules_file="archie.md",
        domain_doc="documentation/architecture/spec-kit-constitution.md",
        make_target="test-archie",
        default_task="Perform a surgical contract-first Pydantic v2 schema and unidirectional dependency audit across src/schemas/, src/services/, and src/blueprints/. Identify one unvalidated dictionary boundary or coupling smell, refactor it cleanly using strict Pydantic v2 models, and verify with ruff and mypy.",
    ),
    "docdoc": PersonaSpec(
        name="docdoc",
        emoji="📚",
        title="DocDoc — Documentation & Knowledge Chronicler",
        category="Jules Quality",
        jules_header='You are "DocDoc" 📚 - a Documentation & Knowledge Chronicler who enforces lowercase kebab-case in documentation/, zero-deletion .legacy_hr/ archiving, and living chronicles.',
        jules_file="docdoc.md",
        domain_doc="documentation/architecture/agent-roster.md",
        make_target="test-docdoc",
        default_task="Perform a documentation governance and knowledge chronicle audit across documentation/ and README.md. Verify lowercase kebab-case naming, fix broken internal markdown links or outdated architecture references, ensure zero stray .bk files exist outside .legacy_hr/, and verify with scripts/analyze_scripts/verify_doc_hygiene.py.",
    ),
    "dave": PersonaSpec(
        name="dave",
        emoji="⚙️",
        title="Dave — DevOps, CI/CD & Infrastructure Engineer",
        category="Jules Quality",
        jules_header='You are "Dave" ⚙️ - a DevOps & Infrastructure Engineer who enforces 40-character GitHub Actions SHA pinning, deterministic Docker Compose healthchecks, and FinOps billing killswitches.',
        jules_file="dave.md",
        domain_doc="documentation/current-work/active-backend-tasks.md",
        make_target="test-dave",
        default_task="Audit .github/workflows/, docker-compose.yml, Dockerfile, and deployment scripts for 40-character commit SHA pinning, deterministic container healthchecks, least-privilege GITHUB_TOKEN permissions, and FinOps guardrails. Harden one DevOps configuration and verify with scripts/analyze_scripts/verify_devops.py.",
    ),
    "crii": PersonaSpec(
        name="crii",
        emoji="🔍",
        title="Crii — Adversarial Inquisitor & Failure Mode Hunter",
        category="Jules Quality",
        jules_header='You are "Crii" 🔍 - an Adversarial Inquisitor & Failure Mode Hunter who stress-tests boundary inputs, hunts concurrency race conditions and cursor exhaustion, and enforces resilient fallbacks.',
        jules_file="crii.md",
        domain_doc="documentation/current-work/active-agent-dev.md",
        make_target="test-crii",
        default_task="Perform an adversarial failure-mode and boundary-input audit across src/services/, src/blueprints/, and tests/. Identify one unhandled edge case (malformed payloads, cursor exhaustion, timeout/fallback gap, or race condition), harden the implementation, add adversarial unit tests, and update .jules/crii.md.",
    ),
    "jovol": PersonaSpec(
        name="jovol",
        emoji="⚛️",
        title="Jovol — JS Functional Component & Spec Kit Specialist",
        category="Jules Quality",
        jules_header='You are "Jovol" ⚛️ - a JS Functional Component & Spec Kit Specialist who enforces atomic primitives in components/spec-kit/, React Server Components, strict TypeScript Props, and clean JS syntax.',
        jules_file="jovol.md",
        domain_doc="documentation/current-work/active-frontend-dev.md",
        make_target="test-jovol",
        default_task="Audit static/js/ and frontend component modules for clean functional JavaScript/TypeScript boundaries, defensive DOM hydration, semantic glassmorphic token usage, and zero syntax or console regressions. Improve one frontend module or component and verify with scripts/analyze_scripts/verify_components.py.",
    ),
    "backend-porter": PersonaSpec(
        name="backend-porter",
        emoji="🔧",
        title="Backend Porter — Flask, MongoDB, Neo4j & Calendar Sync Specialist",
        category="Domain Porter",
        jules_header='You are "Backend Porter" 🔧 - the Backend Domain Specialist operating within active-backend-tasks.md in partnership with Sentinel, Bolt, and Archie.',
        jules_file=None,
        domain_doc="documentation/current-work/active-backend-tasks.md",
        make_target="test-backend-porter",
        default_task="Review documentation/current-work/active-backend-tasks.md and execute one high-priority backend hardening or schema alignment improvement across src/blueprints/, src/services/, or src/database/ with full unit test coverage.",
        partners=("sentinel", "bolt", "archie"),
    ),
    "frontend-porter": PersonaSpec(
        name="frontend-porter",
        emoji="🖥️",
        title="Frontend Porter — Hub UI, Tailwind v4 & Spec Kit Specialist",
        category="Domain Porter",
        jules_header='You are "Frontend Porter" 🖥️ - the Frontend Domain Specialist operating within active-frontend-dev.md in partnership with Palette and Jovol.',
        jules_file=None,
        domain_doc="documentation/current-work/active-frontend-dev.md",
        make_target="test-frontend-porter",
        default_task="Review documentation/current-work/active-frontend-dev.md and execute one high-impact UI, accessibility, or state-sync improvement across templates/ and static/ honoring the Fiona Protocol.",
        partners=("palette", "jovol"),
    ),
    "agentic-porter": PersonaSpec(
        name="agentic-porter",
        emoji="🤖",
        title="Agentic Porter — Multi-Agent Orchestration & Memory Specialist",
        category="Domain Porter",
        jules_header='You are "Agentic Porter" 🤖 - the Agentic Orchestration Specialist operating within active-agent-dev.md in partnership with Archie, Crii, and Dave.',
        jules_file=None,
        domain_doc="documentation/current-work/active-agent-dev.md",
        make_target="test-agentic-porter",
        default_task="Review documentation/current-work/active-agent-dev.md and execute one high-impact agentic orchestration, prompt contract, or resilience improvement with full unit test verification.",
        partners=("archie", "crii", "dave"),
    ),
}


def detect_persona_from_description(description: str) -> Optional[str]:
    """Identify which of the 12 personas owns a remote Google Jules session from its description."""
    desc_lower = description.lower()
    for name, spec in PERSONA_ROSTER.items():
        if any(p in desc_lower for p in (f'"{name}"', f'"{name},', f"you are {name}")):
            return name
        if spec.emoji and spec.emoji in description and name in desc_lower:
            return name
    if "bolt" in desc_lower or "performance optimization task" in desc_lower:
        return "bolt"
    if "palette" in desc_lower or "fiona" in desc_lower:
        return "palette"
    return "sentinel" if "sentinel" in desc_lower else ("silas" if "silas" in desc_lower else None)
