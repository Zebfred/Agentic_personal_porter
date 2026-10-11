# DevOps's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, infrastructure automation, container orchestration, and CI/CD security accumulated during the development and maintenance of the personal porter application.

## 2026-10-11 - Mandatory 40-Character SHA Pinning in GitHub Actions
**Learning:** Referencing mutable Git tags (e.g. `actions/checkout@v4` or `@v3`) in GitHub Actions workflows exposes the CI/CD pipeline to supply chain attacks if upstream tags are maliciously retargeted or hijacked.
**Action:** Pin all third-party GitHub Actions to immutable, full 40-character commit SHAs (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`) accompanied by an inline comment noting the human-readable release tag (`# v4.2.2`).

## 2026-10-11 - Docker Compose Configuration and Healthcheck Determinism
**Learning:** Unverified Docker Compose configurations and absent service healthchecks lead to silent startup failures, racing dependencies (e.g. Flask starting before MongoDB is listening), and unstable deployment scripts.
**Action:** Always validate container definitions with `docker compose config --quiet`. Specify deterministic container names, explicit healthchecks (`test: ["CMD","mongosh","--eval","db.adminCommand('ping')"]`), and dependency ordering (`condition: service_healthy`).

## 2026-10-11 - Fail-Safe FinOps and Cloud Resource Killswitches
**Learning:** Cloud resources left running or auto-scaling indefinitely during agentic loops or automated batch runs can rapidly consume budget and cause runaway billing spikes.
**Action:** Enforce strict budget alarms, hard daily quota caps, and automated timeout killswitches on cloud-hosted compute and vector search clusters.
