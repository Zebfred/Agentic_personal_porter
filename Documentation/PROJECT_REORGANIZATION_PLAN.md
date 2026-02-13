# Project Reorganization Plan

## Current Issues

1. **Root directory clutter**: Too many Python files at root level
2. **Front-end files scattered**: HTML/JS files not in dedicated directory
3. **Helper scripts mixed**: Some in `helper_scripts/`, some at root
4. **Documentation split**: Some in `Documentation/`, some at root
5. **RAG system incomplete**: `rag_core/` exists but `rag_service.py` and `build_rag_index.py` are at root
6. **Inconsistent naming**: Mix of naming conventions

## Proposed Structure

```
Agentic_personal_porter/
├── README.md
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── .cursorignore
├── docker-compose.yml
├── Dockerfile
│
├── src/                          # Main application source code
│   ├── __init__.py
│   ├── app.py                    # Flask app (renamed from server.py)
│   ├── main.py                   # CrewAI workflow
│   │
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   ├── journal.py            # Journal processing endpoint
│   │   └── calendar.py           # Calendar endpoints
│   │
│   ├── agents/                   # CrewAI agents
│   │   ├── __init__.py
│   │   ├── goal_ingester.py
│   │   ├── reflection_agent.py
│   │   └── inventory_curator.py
│   │
│   ├── database/                 # Database integrations
│   │   ├── __init__.py
│   │   ├── neo4j_db.py
│   │   └── models.py             # Data models/schemas
│   │
│   ├── integrations/             # External service integrations
│   │   ├── __init__.py
│   │   ├── google_calendar.py   # Renamed from google_calendar_authentication_helper.py
│   │   └── groq_client.py        # Groq API client (if needed)
│   │
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       └── helpers.py
│
├── frontend/                     # Front-end application
│   ├── index.html
│   ├── inventory.html
│   ├── js/
│   │   ├── app.js
│   │   └── script.js
│   ├── css/
│   │   └── styles.css            # If any custom CSS
│   └── assets/                   # Images, fonts, etc.
│
├── rag_system/                   # RAG system (ResearchAgent)
│   ├── __init__.py
│   ├── service.py                # FastAPI service (renamed from rag_service.py)
│   ├── build_index.py            # Renamed from build_rag_index.py
│   │
│   ├── core/                     # RAG core components
│   │   ├── __init__.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── query_engine.py
│   │
│   └── pipeline/                 # Data pipeline
│       ├── __init__.py
│       ├── paper_scraper.py
│       ├── pdf_extractor.py
│       └── chunking.py
│
├── scripts/                      # Utility scripts
│   ├── check_status.py
│   ├── setup_env.py              # Environment setup helper
│   └── migration/                # Database migration scripts (future)
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── unit/
│   │   ├── test_agents.py
│   │   ├── test_database.py
│   │   └── test_integrations.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_rag_service.py
│   └── rag/                       # RAG-specific tests
│       ├── test_chunking.py
│       ├── test_embeddings.py
│       ├── test_vector_store.py
│       └── test_query_engine.py
│
├── docs/                         # All documentation
│   ├── README.md                 # Main project docs
│   ├── QUICK_START.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── api_design.md
│   │   └── database_schema.md
│   ├── development/
│   │   ├── setup.md
│   │   ├── testing.md
│   │   └── deployment.md
│   ├── features/
│   │   ├── calendar_integration.md
│   │   ├── neo4j_schema.md
│   │   └── rag_system.md
│   └── notes/                     # Development notes
│       └── (moved from txt_notes/)
│
├── data/                         # Data directory (already exists)
│   ├── chroma_db/
│   ├── papers/
│   ├── extracted_text/
│   └── chunks_*.json
│
└── config/                       # Configuration files
    ├── logging.yaml              # Logging configuration
    └── settings.py               # App settings
```

## Migration Steps

### Phase 1: Create New Structure (Non-Breaking)
1. Create new directories
2. Move files to new locations
3. Update imports
4. Update paths in scripts

### Phase 2: Update Imports
1. Update all Python imports
2. Update front-end paths
3. Update test imports
4. Update Docker paths

### Phase 3: Update Configuration
1. Update Dockerfile paths
2. Update docker-compose.yml
3. Update pytest.ini
4. Update any hardcoded paths

### Phase 4: Testing & Validation
1. Run all tests
2. Verify Flask server starts
3. Verify front-end works
4. Verify RAG service works

## File Mapping

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `server.py` | `src/app.py` | Main Flask app |
| `main.py` | `src/main.py` | CrewAI workflow |
| `neo4j_db.py` | `src/database/neo4j_db.py` | Database module |
| `google_calendar_authentication_helper.py` | `src/integrations/google_calendar.py` | Renamed for clarity |
| `check_status.py` | `scripts/check_status.py` | Utility script |
| `rag_service.py` | `rag_system/service.py` | FastAPI service |
| `build_rag_index.py` | `rag_system/build_index.py` | Index builder |
| `rag_core/` | `rag_system/core/` | RAG core components |
| `data_pipeline/` | `rag_system/pipeline/` | Data pipeline |
| `app.js` | `frontend/js/app.js` | Front-end JS |
| `script.js` | `frontend/js/script.js` | Front-end JS |
| `index.html` | `frontend/index.html` | Front-end HTML |
| `inventory.html` | `frontend/inventory.html` | Front-end HTML |
| `Documentation/` | `docs/` | All documentation |
| `txt_notes/` | `docs/notes/` | Development notes |
| `helper_scripts/` | `scripts/` | Utility scripts |
| `QUICK_START.md` | `docs/QUICK_START.md` | Documentation |
| `IMPLEMENTATION_SUMMARY.md` | `docs/IMPLEMENTATION_SUMMARY.md` | Documentation |

## Benefits

1. **Clear separation of concerns**: Each component in its own directory
2. **Easier navigation**: Logical grouping of related files
3. **Better scalability**: Easy to add new features
4. **Standard Python structure**: Follows Python project best practices
5. **Cleaner root**: Only essential files at root level
6. **Better testing**: Organized test structure
7. **Documentation centralization**: All docs in one place

## Considerations

1. **Import paths**: All imports will need updating
2. **Docker paths**: Dockerfile and docker-compose.yml need updates
3. **Front-end paths**: HTML files need to reference new JS locations
4. **Environment variables**: May need path updates
5. **Git history**: Consider using `git mv` to preserve history

## Alternative: Gradual Migration

If full reorganization is too risky, we can do it gradually:

1. **Phase 1**: Move front-end files to `frontend/`
2. **Phase 2**: Move RAG system to `rag_system/`
3. **Phase 3**: Move main app to `src/`
4. **Phase 4**: Consolidate documentation

This allows testing at each phase.
