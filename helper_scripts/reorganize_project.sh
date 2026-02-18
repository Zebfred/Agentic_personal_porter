#!/bin/bash
# Project Reorganization Script
# Run this script to reorganize the project structure
# WARNING: This will move files. Make sure you're on a feature branch!

set -e  # Exit on error

echo "🚀 Starting project reorganization..."
echo "⚠️  Make sure you're on a feature branch and have committed your changes!"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create new directory structure
#echo "📁 Creating new directory structure..."
#mkdir -p src/{api,agents,database,integrations,utils}
#mkdir -p frontend/{js,css,assets}
#mkdir -p rag_system/{core,pipeline}
#mkdir -p scripts/migration
#mkdir -p tests/{unit,integration,rag}
#mkdir -p docs/{architecture,development,features,notes}
#mkdir -p config

# Move main application files
#echo "📦 Moving main application files..."
#git mv server.py src/app.py
#git mv main.py src/main.py
#git mv neo4j_db.py src/database/neo4j_db.py
#git mv google_calendar_authentication_helper.py src/integrations/google_calendar.py

# Move front-end files
echo "🎨 Moving front-end files..."
if [ -f "index.html" ]; then git mv index.html frontend/index.html; fi
if [ -f "inventory.html" ]; then git mv inventory.html frontend/inventory.html; fi
if [ -f "app.js" ]; then git mv app.js frontend/js/app.js; fi
if [ -f "script.js" ]; then git mv script.js frontend/js/script.js; fi

# Move RAG system files
echo "🔍 Moving RAG system files..."
git mv rag_service.py rag_system/service.py
git mv build_rag_index.py rag_system/build_index.py
git mv rag_core rag_system/core
git mv data_pipeline rag_system/pipeline

# Move scripts
echo "🛠️  Moving utility scripts..."
git mv check_status.py scripts/check_status.py
if [ -d "helper_scripts" ]; then
    git mv helper_scripts/* scripts/
    rmdir helper_scripts
fi

# Move documentation
echo "📚 Moving documentation..."
git mv Documentation/* docs/
rmdir Documentation
if [ -d "txt_notes" ]; then
    git mv txt_notes/* docs/notes/
    rmdir txt_notes
fi
if [ -f "QUICK_START.md" ]; then git mv QUICK_START.md docs/QUICK_START.md; fi
if [ -f "IMPLEMENTATION_SUMMARY.md" ]; then git mv IMPLEMENTATION_SUMMARY.md docs/IMPLEMENTATION_SUMMARY.md; fi

# Move tests
echo "🧪 Organizing tests..."
# Keep existing test structure but organize
# Tests can be moved manually if needed

echo "✅ Directory structure created!"
echo ""
echo "⚠️  IMPORTANT: Next steps:"
echo "1. Update all import statements in Python files"
echo "2. Update paths in HTML files (JS/CSS references)"
echo "3. Update Dockerfile and docker-compose.yml paths"
echo "4. Update pytest.ini if needed"
echo "5. Test the application"
echo ""
echo "Run: python scripts/update_imports.py (if we create it)"
echo "Or manually update imports using find/replace"
