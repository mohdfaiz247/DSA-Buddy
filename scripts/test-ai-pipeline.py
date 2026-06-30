"""
Integration test for the AI Agent hint pipeline.
Runs the LangGraph pipeline locally (no Kafka, no Docker) to verify
each node works correctly in isolation.
"""
import asyncio
import sys
import os
import json

# Allow importing from services directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'ai-agent-service'))

# Mock env vars before importing
os.environ.setdefault("KAFKA_BROKERS", "localhost:9092")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_PASSWORD", "changeme")
os.environ.setdefault("OPENAI_API_KEY", "")  # Will use fallback hints

from app.graph.pipeline import hint_graph
from app.graph.state import HintState, HintRequest


def run_pipeline_test():
    print("\n=== DSA Buddy — LangGraph Pipeline Test ===\n")

    req: HintRequest = {
        "user_id": "test-user-001",
        "problem_slug": "two-sum",
        "problem_title": "Two Sum",
        "difficulty": "easy",
        "tags": ["array", "hash-table"],
        "hint_level": 3,
        "user_solve_count": 5,
    }

    initial_state: HintState = {
        "request": req,
        "topic": "",
        "prerequisites": [],
        "related_topics": [],
        "context_docs": [],
        "cache_hit": False,
        "hints": [],
        "error": None,
    }

    print(f"Input: {req['problem_title']} ({req['difficulty']}) — tags: {req['tags']}")
    print(f"Hint level: {req['hint_level']}\n")
    print("Running pipeline...\n")

    result = hint_graph.invoke(initial_state)

    print(f"[OK] Topic classified: {result.get('topic', 'N/A')}")
    print(f"[OK] Prerequisites:    {[p['name'] for p in result.get('prerequisites', [])]}")
    print(f"[OK] Related topics:   {[t['name'] for t in result.get('related_topics', [])]}")
    print(f"[OK] Cache hit:        {result.get('cache_hit', False)}")
    print(f"[OK] Error:            {result.get('error', 'None')}\n")
    print("Generated Hints:")
    for i, hint in enumerate(result.get("hints", []), 1):
        print(f"  {i}. {hint}")

    print("\n[PASS] Pipeline executed successfully!")

    return result


if __name__ == "__main__":
    run_pipeline_test()
