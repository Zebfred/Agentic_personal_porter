from src.database.context_engine import SovereignContextEngine
from src.agents.gtky_identity_architect import GTKYIdentityArchitect

def get_context(username="Hero"):
    """
    Canonical implementation of get_context.
    Loads the Neo4j Graph Snapshot and the Identity Artifacts for full context.
    """
    engine = SovereignContextEngine()
    hero_context = engine.get_hero_snapshot(username=username)
    engine.close()
    
    # Load the JSON Artifacts
    architect = GTKYIdentityArchitect()
    hero_context['ambition'] = architect.get_ambition()
    hero_context['detriments'] = architect.get_detriments()
    
    return hero_context
