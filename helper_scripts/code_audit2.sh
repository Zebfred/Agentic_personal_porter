#!/bin/bash

# =================================================================
# Project Auditor Script
# Purpose: Export a log counting dirs, .py files, imports, and functions.
# Usage: Run at the root of your project src.
# =================================================================

LOG_FILE="project_audit.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "------------------------------------------------------------" > $LOG_FILE
echo "PROJECT AUDIT - $TIMESTAMP" >> $LOG_FILE
echo "------------------------------------------------------------" >> $LOG_FILE

# Use a Python heredoc to handle the complex parsing of .py files
python3 << EOF >> $LOG_FILE
import os
import ast

def get_file_metadata(filepath):
    """Parses a .py file and returns lists of imports and function names."""
    functions = []
    imports = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                # Extract Functions
                if isinstance(node, ast.FunctionDef):
                    functions.append(f"def {node.name}")
                elif isinstance(node, ast.AsyncFunctionDef):
                    functions.append(f"async def {node.name}")
                
                # Extract Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")
                        
    except Exception as e:
        return [f"Error parsing imports: {str(e)}"], [f"Error parsing functions: {str(e)}"]
    return imports, functions

# Start scanning
root_dir = "."
for root, dirs, files in os.walk(root_dir):
    # Skip hidden directories like .git or __pycache__
    if any(part.startswith('.') or part == "__pycache__" for part in root.split(os.sep)):
        continue
    
    # Filter for .py files, excluding __init__.py
    py_files = sorted([f for f in files if f.endswith('.py') and f != '__init__.py'])
    
    if not py_files:
        continue

    # Directory header
    display_name = root.replace("./", "") if root != "." else "root"
    print(f"\ndir - {display_name}")
    
    # Analyze each file
    for py_file in py_files:
        path = os.path.join(root, py_file)
        base_name = py_file.replace(".py", "")
        
        imports, funcs = get_file_metadata(path)
        
        print(f"python_script_name - {base_name}")
        
        # Format Imports
        import_str = "\n".join(imports) if imports else "None"
        print(f"\n{base_name}_imports - \n{import_str}")
        
        # Format Functions
        func_str = "\n".join(funcs) if funcs else "None"
        print(f"\n{base_name}_functions - \n{func_str}")
        print("-" * 30)

EOF

echo "" >> $LOG_FILE
echo "Audit complete. Results saved to $LOG_FILE"
echo "Keep working upwards, sir!"