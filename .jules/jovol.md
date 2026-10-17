# Jovol's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, architectural insights, and React/Next.js functional component design patterns accumulated by **Jovol** (JS Functional Component Specialist) during the development and maintenance of the personal porter application.

## 2026-10-11 - Spec Kit Primitive Assembly vs Raw Style Drift
**Learning:** Allowing AI agents or developers to write arbitrary Tailwind utility chains for every individual view causes visual inconsistency, layout drift, and unmaintainable UI code that breaks the glassmorphic aesthetic.
**Action:** Always assemble views in `components/views/` by importing and arranging verified atomic primitives from `components/spec-kit/` (e.g., `Card`, `Button`, `StatDisplay`, `LayoutShell`, `MetricRing`) governed by `COMPONENT_REGISTRY.md`. Do not introduce ad-hoc CSS classes when a Spec Kit primitive exists.

## 2026-10-11 - Server Components Default & Client Boundary Discipline
**Learning:** Overusing `'use client'` at the root of component trees forces unnecessary JavaScript to download to the client, sacrifices SEO/SSG benefits, and prevents secure, direct server-layer data fetching from MongoDB or Neo4j.
**Action:** Treat React Server Components (RSC) as the default in Next.js App Router (`app/`). Isolate client-side state, event handlers, and browser APIs into small, focused leaf components marked with `'use client'`.

## 2026-10-11 - Strict Prop Interface Typing and Glassmorphic Tokens
**Learning:** Loose JavaScript props (`props.variant`, `props.data`) or missing TypeScript interfaces lead to runtime undefined errors and broken component rendering when props evolve.
**Action:** Every functional component must define an explicit TypeScript `Props` interface (e.g. `interface CardProps { title: string; variant?: 'glass' | 'solid'; children: React.ReactNode; }`). Centralize glassmorphic styles into semantic design tokens (`--glass-surface`, `--glass-border`) rather than hardcoding fragmented utility strings.

## 2026-10-11 - Route Group Perimeter Isolation (LLC vs Porter)
**Learning:** Mixing corporate landing page concerns with authenticated personal porter operations creates routing conflicts, authorization leaks, and bloated bundles.
**Action:** Enforce strict Next.js route groups: `app/(marketing)/` for high-speed SSG corporate pages, `app/(dashboard)/` for authenticated SSR personal porter tools, and `app/api/` for edge proxies communicating with Flask/GCP backends.
