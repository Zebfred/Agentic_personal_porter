"""
Defines evaluation test cases for the Agentic Personal Porter's
categorization and orchestration (tool-routing) behaviors.

Categorization tests: evaluates pillar classification accuracy.
Routing tests: evaluates whether the Porter selects the correct tool
               and extracts the correct arguments from user input.
"""

from typing import List, Dict, Any

def get_categorization_test_cases() -> List[Dict[str, Any]]:
    """Returns test cases for the Categorizer node (pillar classification).

    Each case has a journal_entry, actuals context, and expected Hero Pillar.
    """
    return [
        {
            "id": "tc_001",
            "journal_entry": "Intention: Work deeply. Actual: Fell down a rabbit hole of tutorials and abstract thought.",
            "actuals_str": "- Coding Session (Wealth/Career)",
            "expected_pillar": "2. Mind"
        },
        {
            "id": "tc_002",
            "journal_entry": "Intention: Go to the gym for 1 hour. Actual: Went for a 2 hour run instead and felt great.",
            "actuals_str": "- Gym Session (Body/Health)",
            "expected_pillar": "3. Body/Health"
        },
        {
            "id": "tc_003",
            "journal_entry": "Intention: Relax and do nothing. Actual: Called my mom and talked for an hour.",
            "actuals_str": "- Empty block",
            "expected_pillar": "4. Heart/Social"
        },
        {
            "id": "tc_004",
            "journal_entry": "Intention: Review my stock portfolio. Actual: Built a new budget spreadsheet.",
            "actuals_str": "- Finance Review (Wealth/Career)",
            "expected_pillar": "5. Wealth/Career"
        }
    ]

def get_routing_test_cases() -> List[Dict[str, Any]]:
    """Returns test cases for the First-Serving Porter's tool routing.

    Each case validates that the Porter picks the correct tool and extracts
    the correct arguments from natural language input. Covers all 7 tools
    plus a multi-step reasoning case.

    Fields:
        id: Unique test case identifier.
        input_text: The user's natural language query.
        expected_tool: The tool name the Porter should invoke first.
        expected_args: Dict of key argument checks. Values are substrings
                       that must appear in the tool call's argument values.
        profile: A label describing the reasoning complexity.
    """
    return [
        {
            "id": "tr_001",
            "input_text": (
                "Please update my hero ambition to include my new goal "
                "of writing a book by the end of the year."
            ),
            "expected_tool": "update_artifact",
            "expected_args": {"artifact_name": "ambition"},
            "profile": "simple_delegation"
        },
        {
            "id": "tr_002",
            "input_text": "What did I do on 2026-04-17?",
            "expected_tool": "consult_time_keeper",
            "expected_args": {"date_iso": "2026-04-17"},
            "profile": "temporal_extraction"
        },
        {
            "id": "tr_003",
            "input_text": (
                "What's the overall vibe of my progress on my health goals?"
            ),
            "expected_tool": "chroma_vibe_check",
            "expected_args": {"query": "health"},
            "profile": "conceptual_search"
        },
        {
            "id": "tr_004",
            "input_text": (
                "Search my calendar for any career-related events this month."
            ),
            "expected_tool": "weaviate_hybrid_search",
            "expected_args": {"pillar": "Career"},
            "profile": "structured_search"
        },
        {
            "id": "tr_005",
            "input_text": "Are there any events I haven't verified yet?",
            "expected_tool": "fetch_unverified_audits",
            "expected_args": {},
            "profile": "audit_delegation"
        },
        {
            "id": "tr_006",
            "input_text": (
                "Can you scan my origin story for any gaps in my timeline?"
            ),
            "expected_tool": "scan_origin_story",
            "expected_args": {},
            "profile": "identity_delegation"
        },
        {
            "id": "tr_007",
            "input_text": (
                "Route this to the Socratic Mirror for deeper reflection "
                "on my recent patterns."
            ),
            "expected_tool": "route_to_subagent",
            "expected_args": {"agent_name": "Socratic"},
            "profile": "agent_routing"
        },
        {
            "id": "tr_008",
            "input_text": (
                "Give me a breakdown of my week vs my goals and "
                "highlight anything surprising."
            ),
            "expected_tool": "__multi__",
            "expected_args": {},
            "profile": "multi_step_reasoning"
        },
    ]
