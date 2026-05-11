import os
import re
from pathlib import Path

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    
    # Remove `sys.path.append(...)` lines
    content = re.sub(r'^[ \t]*sys\.path\.append\(.*?\)[ \t]*\n', '', content, flags=re.MULTILINE)
    
    # Remove `if str(root) not in sys.path:` lines
    content = re.sub(r'^[ \t]*if str\(.*?\) not in sys\.path:[ \t]*\n', '', content, flags=re.MULTILINE)
    
    # Remove `if str(project_root) not in sys.path:` and `sys.path.append(str(project_root))`
    content = re.sub(r'^[ \t]*root = Path\(__file__\).*?\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^[ \t]*project_root = Path\(__file__\).*?\n', '', content, flags=re.MULTILINE)
    
    # Clean up empty lines that might have been left
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # If the file has `print(`, we will replace it with `logger.info(`
    # But ONLY if it's a standalone print statement, not e.g., something like `repr = print(...)`
    # A simple regex for print statement at the start of a line (with optional whitespace):
    has_print = bool(re.search(r'^[ \t]*print\(', content, flags=re.MULTILINE))
    
    if has_print:
        content = re.sub(r'^([ \t]*)print\(', r'\1logger.info(', content, flags=re.MULTILINE)
        
        # Now we need to ensure the logger is imported
        if 'logging.getLogger' not in content and 'setup_logger' not in content:
            # Add logger import at the top (after docstrings or first import)
            logger_setup = "import logging\nfrom src.utils.logging_config import setup_logger\nlogger = setup_logger(__name__)\n"
            
            # Find the first import statement
            match = re.search(r'^(import |from )', content, flags=re.MULTILINE)
            if match:
                idx = match.start()
                content = content[:idx] + logger_setup + content[idx:]
            else:
                content = logger_setup + content
    
    if content != original_content:
        # Make a backup
        backup_path = f"{filepath}.bk"
        with open(backup_path, 'w') as f:
            f.write(original_content)
            
        with open(filepath, 'w') as f:
            f.write(content)
        logger.info(f"Refactored {filepath}")

def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    
    # Process src/ and scripts/
    for target_dir in [root_dir / 'src', root_dir / 'scripts', root_dir / 'tests']:
        if not target_dir.exists():
            continue
            
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith('.py'):
                    process_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
