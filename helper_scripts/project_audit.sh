#!/bin/bash

# =================================================================
# Project Auditor Script
# Purpose: Export a log counting dirs, .py files, and functions.
# Usage: Run at the root of your project src.
# =================================================================

LOG_FILE="project_audit.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "------------------------------------------------------------" > $LOG_FILE
echo "PROJECT AUDIT - $TIMESTAMP" >> $LOG_FILE
echo "------------------------------------------------------------" >> $LOG_FILE

# Use a Python heredoc to handle the complex parsing of .py files and functions
python3 << EOF >> $LOG_FILE
import os
import ast

def get_functions(filepath):
    """Parses a .py file and returns a list of function names."""
    functions = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.AsyncFunctionDef):
                    functions.append(f"async {node.name}")
    except Exception as e:
        return [f"Error parsing: {str(e)}"]
    return functions

# Start scanning
root_dir = "."
for root, dirs, files in os.walk(root_dir):
    # Skip hidden directories like .git or __pycache__
    if any(part.startswith('.') or part == "__pycache__" for part in root.split(os.sep)):
        continue
    
    # Filter for .py files, excluding __init__.py
    py_files = [f for f in files if f.endswith('.py') and f != '__init__.py']
    
    if not py_files and root == root_dir:
        continue

    # Format output for the Directory
    display_name = root.replace("./", "") if root != "." else "root"
    print(f"\n📂 {display_name} - {len(py_files)} .py scripts")
    
    # Analyze each file
    for py_file in sorted(py_files):
        path = os.path.join(root, py_file)
        funcs = get_functions(path)
        func_list_str = ", ".join(funcs) if funcs else "no functions defined"
        print(f"   |_ {py_file} has {len(funcs)} functions: [{func_list_str}]")

EOF

echo "" >> $LOG_FILE
echo "Audit complete. Results saved to $LOG_FILE"
echo "Keep working upwards, sir!"
