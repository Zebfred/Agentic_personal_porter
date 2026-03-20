---
trigger: always_on
---

# Rules for Agentic Personal Porter

## Documentation Organization

**CRITICAL: All markdown (.md) documentation files MUST be placed in the `Documentation/` directory.**

### Rules:
1. **Never create markdown files in the project root** - All `.md` files (except `README.md`) must be in `Documentation/`
2. **When generating documentation**, always use the path: `Documentation/FILENAME.md`
3. **If asked to create documentation**, automatically place it in `Documentation/` without asking
4. **Exception**: `README.md` can stay in root (standard practice)
5. **Always create backups for all files changed.**
6. **Never delete files.** All outdated files must be moved to the `.legacy_hr` directory present at the project root. Ensure `.legacy_hr` remains in `.gitignore` and `.cursorignore` to prevent old code from polluting the AI token context window.
7. **Strict Domain Scoping:** Agent chats will individually be responsible for doing development in exactly one domain as outlined in their respective `Documentation/Current_Future_work/ACTIVE_[Domain].md` document. At the start of every session, the assigned agent MUST independently read their specific ACTIVE document before proposing any code edits. As the agent performs tasks in this document, it must be updated to note human verification of completion. 
8. **Verification Requirement:** Upon an agent's task completion, a verification script, test, or Checklist MUST be used if applicable to their task or domain.
9. **Mandatory Cleanup:** Upon an agent's task completion, the agent MUST independently move any lingering `.bk` files into the `.legacy_hr` directory rather than leaving them scattered in active directories.

 

### Examples:
- ✅ `Documentation/IMPLEMENTATION_SUMMARY.md`
- ✅ `Documentation/QUICK_START.md`
- ✅ `Documentation/ARCHITECTURE.md`
- ❌ `IMPLEMENTATION_SUMMARY.md` (in root)
- ❌ `QUICK_START.md` (in root)

### When to Create Documentation:
- Implementation summaries
- Feature documentation
- Setup guides
- Architecture documentation
- API documentation
- Troubleshooting guides
- Any explanatory markdown files

## Code Organization

### Import Paths:
- Always use absolute imports with `src.` prefix when importing from the main application
- Example: `from src.main import run_crew`
- Add project root to `sys.path` in entry point files (like `src/app.py`) to support direct execution

### File Structure:
- Main application code: `src/`
- Front-end: `frontend/`
- RAG system: `rag_system/`
- Scripts: `scripts/`
- Tests: `tests/`
- Documentation: `Documentation/`

## Code Style

### Python:
- Use type hints where appropriate
- Follow PEP 8 style guidelines
- Add docstrings to functions and classes
- Use meaningful variable names

### Error Handling:
- Provide clear, actionable error messages
- Include traceback for debugging in development
- Return appropriate HTTP status codes

## Testing

- Run tests before committing major changes
- Update tests when modifying functionality
- Keep test files organized in `tests/` directory

## Git Workflow

- Create feature branches for significant changes
- Use descriptive commit messages
- Test thoroughly before merging to main