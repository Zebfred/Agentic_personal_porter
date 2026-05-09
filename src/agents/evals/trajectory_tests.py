"""
Defines evaluation test cases for the Agentic Personal Porter's categorization and routing behaviors.
"""

from typing import List, Dict, Any

def get_categorization_test_cases() -> List[Dict[str, Any]]:
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
    return [
        {
            "id": "tr_001",
            "input_text": "Please update my hero ambition to include my new goal of writing a book by the end of the year.",
            "expected_tool": "update_artifact"
        },
        {
            "id": "tr_002",
            "input_text": "What did I do on 2026-04-17?",
            "expected_tool": "consult_time_keeper"
        },
        {
            "id": "tr_003",
            "input_text": "What's the overall vibe of my progress on my health goals?",
            "expected_tool": "chroma_vibe_check"
        }
    ]
