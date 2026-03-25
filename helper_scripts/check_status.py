"""
Status check script to verify all system components are working.

This script checks:
- Neo4j database connection
- Environment variables in the .auth directory
- Google Calendar credentials in the .auth directory
- Flask server readiness
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can import src modules
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.path_utils import load_env_vars, get_auth_file

# Dynamically load from .auth/.env
load_env_vars()

def check_environment_variables():
    """Check if required environment variables are set."""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES CHECK (Reading from .auth/.env)")
    print("="*60)
    
    required_vars = {
        'GROQ_API_KEY': 'Groq API key for LLM access',
        'NEO4J_URI': 'Neo4j database URI',
        'NEO4J_USERNAME': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password',
    }
    
    all_good = True
    
    print("\nRequired Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'KEY' in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NOT SET - {description}")
            all_good = False
            
    return all_good


def check_neo4j_connection():
    """Check if Neo4j database is accessible."""
    print("\n" + "="*60)
    print("NEO4J DATABASE CHECK")
    print("="*60)
    
    try:
        from src.database.neo4j_client import get_driver
        
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, username, password]):
            print("  ❌ Missing Neo4j environment variables")
            return False
        
        print(f"  Connecting to: {uri}")
        print(f"  Username: {username}")
        
        driver = get_driver()
        
        # Test connection with a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record['test'] == 1:
                print("  ✅ Neo4j connection successful")
                
                # Get database info
                db_info = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
                for record in db_info:
                    print(f"     Component: {record['name']}, Version: {record['version']}")
                
                # Count nodes
                node_count = session.run("MATCH (n) RETURN count(n) as count").single()
                if node_count:
                    print(f"     Total nodes in database: {node_count['count']}")
                
                driver.close()
                return True
            else:
                print("  ❌ Neo4j connection test failed")
                driver.close()
                return False
                
    except ImportError as e:
        print(f"  ❌ Cannot import neo4j_client module: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Neo4j connection failed: {e}")
        return False


def check_google_calendar_credentials():
    """Check if Google Calendar credentials exist in .auth."""
    print("\n" + "="*60)
    print("GOOGLE CALENDAR CREDENTIALS CHECK (.auth directory)")
    print("="*60)
    
    credentials_file = Path(get_auth_file("credentials.json"))
    token_file = Path(get_auth_file("token.pickle"))
    
    if credentials_file.exists():
        print(f"  ✅ credentials.json found ({credentials_file.stat().st_size} bytes)")
    else:
        print(f"  ❌ credentials.json NOT FOUND in .auth/")
        print("     This file should contain OAuth 2.0 credentials from Google Cloud Console")
        return False
    
    if token_file.exists():
        print("  ✅ token.pickle found in .auth/")
    else:
        print("  ⚠️  token.pickle NOT FOUND in .auth/")
        print("     OAuth flow will need to be completed on first run")
    
    try:
        from src.integrations.google_calendar import get_calendar_service
        print("  ✅ src/integrations/google_calendar.py can be imported")
        
        # Only test service if token exists (otherwise it will prompt)
        if token_file.exists():
            try:
                service = get_calendar_service()
                print("  ✅ Calendar service initialized successfully")
                return True
            except Exception as e:
                print(f"  ⚠️  Calendar service initialization failed: {e}")
                print("     This may require re-authentication")
                return False
        else:
            print("  ⚠️  Cannot test service without token.pickle")
            return True  # Not a failure, just needs auth
            
    except ImportError as e:
        print(f"  ❌ Cannot import calendar helper: {e}")
        return False


def check_flask_readiness():
    """Check if Flask server can start."""
    print("\n" + "="*60)
    print("FLASK SERVER READINESS CHECK")
    print("="*60)
    
    try:
        from src import app
        print("  ✅ src/app.py can be imported")
        
        # Check if app is defined
        if hasattr(app, 'app'):
            print("  ✅ Flask app is defined")
            routes = [rule.rule for rule in app.app.url_map.iter_rules()]
            print(f"  ✅ Found {len(routes)} routes")
            return True
        else:
            print("  ❌ Flask app not found in src/app.py")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking Flask: {e}")
        return False





def main():
    """Run all status checks."""
    print("="*60)
    print("AGENTIC PERSONAL PORTER - STATUS CHECK")
    print("="*60)
    print(f"Working directory: {Path.cwd()}")
    print(f"Python version: {sys.version}")
    
    results = {
        'environment': check_environment_variables(),
        'neo4j': check_neo4j_connection(),
        'google_calendar': check_google_calendar_credentials(),
        'flask': check_flask_readiness(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component.upper()}: {'PASS' if status else 'FAIL'}")
    
    if all_passed:
        print("\n🎉 All checks passed! System dependencies are ready to use.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
