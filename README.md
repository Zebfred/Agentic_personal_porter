# Agentic Personal Porter

## Introduction & Vision

Welcome, Hero. Your journey is uniquely yours, and every step, planned or unplanned, holds value. The Agentic Personal Porter is your non-judgmental digital companion on this adventure. It isn't just another productivity tracker—it is a sovereign intelligence layer designed to compassionately bridge the gap between your stated intentions and your actual actions.

By leveraging holistic frameworks like Maslow's Hierarchy of Needs and extracting deep context from your "Origin Story" and "Ambitions," we aim to capture a nuanced picture of your state. The Porter helps you understand the "why" behind your choices, find meaning in what you do, and align your daily grind with a fulfilling existence.

## The Mach 2 Ecosystem (Current MVP)

We are currently operating within the **Mach 2** lifecycle—a system defined by its rigid, reliable ability to ingest user reality vs. human intention.

*   **Twin-Track Ingestion:** Seamlessly pulls your planned *Intentions* from Google Calendar into a local MongoDB landing zone, formats them, and merges them securely into the Neo4j Identity Graph.
*   **The 20-Second Recon Loop:** A lightning-fast, glassmorphic frontend UI designed for rapid verification of daily events, driving cognitive load to near-zero.
*   **Agentic Reflection:** Sophisticated CrewAI workflows spin up specialized autonomous agents (Socratic Coaches, GTKY Librarians) to analyze the numeric delta ($\Delta$) between your Intent vs. Actuals, generating deep, non-critical insights.
*   **Sovereign Memory:** Every log, task, and reflection is saved as an interconnected node-pattern within a private, locally-hosted Neo4j graph database, establishing a localized "digital brain."

## Repository Architecture & Documentation

This repository relies on a sprawling ecosystem of agents and meticulous documentation. **If you are contributing, you MUST read the respective documentation.**

*   **[`src/`](src/):** The core intelligence engine containing the Python Flask backend (`app.py`), the specialized Agent architectures (`src/agents/`), Neo4j/Mongo database clients (`src/database/`), and integrations (`src/integrations/`).
*   **[`frontend/`](frontend/):** The client-side application featuring Vanilla JS (`app.js`, `script.js`) and Tailwind CSS to drive the interactive Hero's Inventory and Activity Dashboards.
*   **[`Documentation/`](Documentation/):** The single source of truth for the project. 
    *   **[`Documentation/Current_Future_work/`](Documentation/Current_Future_work/):** Contains the official `MACH2_ROADMAP.md`, `MACH3_beyond_ROADMAP.md`, and all `ACTIVE_*.md` tracker files mapping current development sprints.
    *   **[`Documentation/architecture/`](Documentation/architecture/):** Contains the definitive `AGENT_REGISTRY.md`, Neo4j `DATABASE_SCHEMA.md`, and the `SCRIPT_REGISTRY.md`.
    *   **[`.agent/rules/rules.md`](.agent/rules/rules.md):** The strict operational boundaries for any AI operating inside this repository.

## Setup & Installation

### 1. Zero-Trust Security Configuration (`.auth/`)
All environment variables, highly personal mappings, and Google OAuth tokens **must** be stored securely in an isolated `.auth/` directory at the project root. This directory is strictly `.gitignore`d. 

Create `.auth/.env` and supply:
```env
GROQ_API_KEY="your_groq_api_key"
NEO4J_URI="bolt://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_password"
MONGO_URI="mongodb://localhost:27017/"
```
Ensure your `category_mapping.json` (as shown in `data/category_mapping.example.json`) is also placed in `.auth/`.

### 2. Environment & Dependencies
This project uses Python 3.11+.
```bash
conda create --name agentic_porter python=3.11
conda activate agentic_porter
pip install -r requirements.txt
```

### 3. Running the Ecosystem
The application currently requires running the API and Frontend concurrently.

**Terminal 1 (Backend API):**
```bash
python src/app.py
```

**Terminal 2 (Frontend UI):**
Open `frontend/index.html` via Visual Studio Code's **Live Server** extension, or serve it on a secondary port.

## The Future: Mach 3 & Beyond

The upcoming **Mach 3** iteration will shift focus from raw data ingestion to advanced agent networking. Upcoming architectures include the **First-Serving Porter** (a front-man manager outputting weighted daily recommendations) and the **Analyzer Porter** (using regression to calculate hard numerical "Hero Numbers" indicating forward progress).

Read the full future breakdown in [`Documentation/Current_Future_work/MACH3_beyond_ROADMAP.md`](Documentation/Current_Future_work/MACH3_beyond_ROADMAP.md).