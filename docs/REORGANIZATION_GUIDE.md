# Project Reorganization Guide

## Overview

This guide helps you reorganize the Agentic Personal Porter project into a cleaner, more maintainable structure.

## Quick Start (Recommended Approach)

### Option 1: Manual Reorganization (Safest)

1. **Create the new structure** (don't move files yet)
2. **Update imports** in existing files to use new paths
3. **Test everything works**
4. **Then move files** using `git mv` to preserve history
5. **Final testing**

### Option 2: Use the Script (Faster but Riskier)

```bash
# Make sure you're on a feature branch!
git checkout -b refactor/project-reorganization

# Review the script first
cat scripts/reorganize_project.sh

# Run it
./scripts/reorganize_project.sh
```

## Detailed Migration Steps

### Step 1: Create New Directories

```bash
mkdir -p src/{api,agents,database,integrations,utils}
mkdir -p frontend/{js,css,assets}
mkdir -p rag_system/{core,pipeline}
mkdir -p scripts scripts/migration
mkdir -p tests/{unit,integration,rag}
mkdir -p docs/{architecture,development,features,notes}
mkdir -p config
```

### Step 2: Update Python Imports

#### Before:
```python
from neo4j_db import log_to_neo4j
from google_calendar_authentication_helper import get_calendar_service
from main import run_crew
```

#### After:
```python
from src.database.neo4j_db import log_to_neo4j
from src.integrations.google_calendar import get_calendar_service
from src.main import run_crew
```

Or use relative imports within `src/`:
```python
from .database.neo4j_db import log_to_neo4j
from .integrations.google_calendar import get_calendar_service
from .main import run_crew
```

### Step 3: Update Front-End Paths

#### In `index.html` and `inventory.html`:

**Before:**
```html
<script src="app.js"></script>
<script src="script.js"></script>
```

**After:**
```html
<script src="js/app.js"></script>
<script src="js/script.js"></script>
```

### Step 4: Update Dockerfile

**Before:**
```dockerfile
COPY server.py /app/
COPY main.py /app/
```

**After:**
```dockerfile
COPY src/ /app/src/
WORKDIR /app
ENV PYTHONPATH=/app
```

### Step 5: Update docker-compose.yml

Update any volume mounts or working directories.

### Step 6: Update Entry Points

**Before:**
```bash
python server.py
```

**After:**
```bash
python -m src.app
# Or create a run script
```

## Import Update Helper Script

Create `scripts/update_imports.py`:

```python
#!/usr/bin/env python3
"""Helper script to update imports after reorganization."""

import re
import os
from pathlib import Path

IMPORT_MAPPINGS = {
    'from neo4j_db import': 'from src.database.neo4j_db import',
    'from google_calendar_authentication_helper import': 'from src.integrations.google_calendar import',
    'from main import': 'from src.main import',
    'from rag_core': 'from rag_system.core',
    'from data_pipeline': 'from rag_system.pipeline',
    # Add more mappings as needed
}

def update_imports_in_file(filepath):
    """Update imports in a single file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = content.replace(old_import, new_import)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Update imports in all Python files."""
    project_root = Path(__file__).parent.parent
    
    updated_files = []
    for py_file in project_root.rglob('*.py'):
        if update_imports_in_file(py_file):
            updated_files.append(str(py_file))
    
    if updated_files:
        print(f"Updated {len(updated_files)} files:")
        for f in updated_files:
            print(f"  - {f}")
    else:
        print("No files needed updating.")

if __name__ == '__main__':
    main()
```

## Testing After Reorganization

### 1. Test Flask Server
```bash
cd /path/to/project
python -m src.app
# Or: python src/app.py (if __main__ block exists)
```

### 2. Test Front-End
```bash
# Serve frontend/index.html
# Check browser console for errors
```

### 3. Test RAG Service
```bash
python -m rag_system.service
# Or: python rag_system/service.py
```

### 4. Run Tests
```bash
pytest tests/
```

### 5. Test Status Check
```bash
python scripts/check_status.py
```

## Rollback Plan

If something breaks:

```bash
# Revert the reorganization
git reset --hard HEAD~1

# Or selectively revert file moves
git checkout HEAD~1 -- server.py
git checkout HEAD~1 -- main.py
# etc.
```

## Benefits After Reorganization

1. ✅ **Cleaner root directory** - Only essential files
2. ✅ **Better organization** - Related files grouped together
3. ✅ **Easier navigation** - Clear structure
4. ✅ **Scalability** - Easy to add new features
5. ✅ **Standard structure** - Follows Python best practices
6. ✅ **Better testing** - Organized test structure
7. ✅ **Documentation** - All docs in one place

## Common Issues & Solutions

### Issue: Import errors after moving files
**Solution**: Update PYTHONPATH or use relative imports

### Issue: Front-end can't find JS files
**Solution**: Update HTML script src paths

### Issue: Docker can't find files
**Solution**: Update COPY commands in Dockerfile

### Issue: Tests can't import modules
**Solution**: Update pytest.ini or conftest.py with correct paths

## Next Steps After Reorganization

1. Update README.md with new structure
2. Update any CI/CD configurations
3. Update documentation references
4. Consider adding `__init__.py` files for proper Python packages
5. Consider adding setup.py or pyproject.toml for installability
