"""
LangGraph State schema for the hint generation pipeline.
"""
from typing import TypedDict, Annotated
import operator


class HintRequest(TypedDict):
    user_id: str
    problem_slug: str
    problem_title: str
    difficulty: str
    tags: list[str]
    hint_level: int            # 1-5 (progressive depth)
    user_solve_count: int
    user_code: str             # User's current code/approach (may be empty)


class HintState(TypedDict):
    # Input
    request: HintRequest

    # Intermediate state
    topic: str                 # Classified DSA topic slug
    prerequisites: list[dict]  # From Neo4j
    related_topics: list[dict] # From Neo4j
    context_docs: list[str]    # From Pinecone RAG (future)
    cache_hit: bool

    # Output
    hints: Annotated[list[str], operator.add]  # accumulated across steps
    error: str | None
