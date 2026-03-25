# Mach 2 Roadmap: The "Twin-Track" System

This is the definitive tracking document for formalizing the completion of **Mach 2** of the Agentic Personal Porter. 
Mach 2 is defined by the rigid, reliable ability to ingest user reality vs. human intention.

## Core Milestones to Completion

### 1. Achieve Consistent Data Idempotency
- [ ] **Mongo Landing Zone:** Implement daily bulk pulls from Google Calendar that land directly into a MongoDB cluster.
- [ ] **Format & Clean:** Pre-process the raw GCal strings into structured, AI-ready JSON inside the landing zone.
- [ ] **Neo4j Merge Validation:** The `MERGE` logic pushing from Mongo to Neo4j must be rigorously tested against massive historical JSON samples to guarantee repeated syncs never degrade the graph or create duplicate "ghost" relationships.

### 2. Finalize the "Daily Recon" UI
- [ ] **The 20-Second Loop:** The frontend (`index.html` / `app.js`) must prioritize a lightning-fast verification loop. 
- [ ] **Low Cognitive Load:** Agent-inferred labels for activities must be visibly flagged on the frontend, easily correctable, and confirmable with a single click.
- [ ] **Artifact Integration:** Update `inject_hero_foundation` to pull smoothly from new frontend input UI rather than existing strictly as a backend script.

### 3. Expand Socratic Reflection Prompts
- [ ] **Context Upgrade:** The backend reflection agent must be given expanded logic to detect "The Fog of War" (untracked hours).
- [ ] **Nuanced Reflection:** Must successfully differentiate between "Restorative Rest" (a biological necessity and psychological win) vs. "Mindless Stagnation."

### 4. Establish a Robust Backup Strategy
- [ ] **Auth Quarantine:** Fully secure the `.auth` directory holding keys, maps, and tokens.
- [ ] **Database Snapshots:** Set up automated cron-jobs or scripts ensuring regular, secure Neo4j graph exports to prevent catastrophic data loss.

## Upcoming Backend Automation Enhancements
- **Future Feature [Rolling Historical Seeding]:** Currently, `helper_scripts/seed_calendar.py` triggers exactly one month of back-dated imports. We plan to build an iterative loop where, after a successful month is ingested and verified, the agent automatically executes the *previous* month (Months 1 -> 2, Months 2 -> 3) on a weekly basis. This prevents overloading the Neo4j graph with 14k+ events in a single massive pull, allowing for organic "Time-Series" growth that agents can reason upon properly without missing context constraints.
