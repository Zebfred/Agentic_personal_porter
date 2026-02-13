#!/bin/bash

echo "=============================================="
echo "      PROJECT VARIABLE AUDIT: 'THE USUAL SUSPECTS'"
echo "=============================================="
echo "Searching for conflicting variable names across JS, Python, and HTML..."
echo ""

# Define the suspicious terms we know are causing trouble
KEYWORDS=("journal_entry" "journal_entry_text" "log_data" "result" "reflection" "date" "start" "summary")

# Define specific files to target (adjust paths if your structure changes)
TARGET_FILES="./src/frontend/js/app.js ./src/backend/server.py ./src/database/neo4j_db.py ./src/frontend/index.html"

for WORD in "${KEYWORDS[@]}"; do
    echo "----------------------------------------------"
    echo "🔎 Searching for: '$WORD'"
    echo "----------------------------------------------"
    
    # Grep with line numbers, color matches, and ignore case
    # using 'git grep' if available for speed, falling back to standard grep
    if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        git grep -n --color=always "$WORD" -- $TARGET_FILES
    else
        grep -rn --color=always "$WORD" $TARGET_FILES
    fi
    echo ""
done

echo "=============================================="
echo "AUDIT COMPLETE."
echo "If you see 'journal_entry' in app.js but 'journal_entry_text' in server.py -> THAT IS YOUR BUG."
echo "=============================================="