"""
LangGraph nodes — each node performs one step of the hint pipeline.

Pipeline flow:
  check_cache → [cache_hit → return] OR [classify_topic → enrich_context → generate_hints → store_cache]
"""
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from app.graph.state import HintState
from app.tools.neo4j_tool import neo4j_tool
from app.tools.redis_cache import redis_cache
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        google_api_key=settings.GEMINI_API_KEY,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_output_tokens=settings.LLM_MAX_TOKENS,
    )


# ─── Node 1: Check Redis cache ──────────────────────────────────────────────

def node_check_cache(state: HintState) -> HintState:
    """Check if we already generated hints for this user+problem combo."""
    req = state["request"]
    cached = redis_cache.get_hints(req["user_id"], req["problem_slug"])
    if cached:
        return {
            **state,
            "cache_hit": True,
            "hints": cached,
        }
    return {**state, "cache_hit": False}


# ─── Node 2: Classify topic via Neo4j ────────────────────────────────────────

def node_classify_topic(state: HintState) -> HintState:
    """Map the problem tags to a Neo4j topic slug."""
    req = state["request"]
    topic = neo4j_tool.classify_topic(req["problem_title"], req["tags"])
    logger.info(f"Classified '{req['problem_slug']}' → topic: {topic}")
    return {**state, "topic": topic}


# ─── Node 3: Enrich with graph context ───────────────────────────────────────

def node_enrich_context(state: HintState) -> HintState:
    """Fetch prerequisites and related topics from Neo4j for richer hints."""
    topic = state.get("topic", "arrays-strings")
    prerequisites = neo4j_tool.get_prerequisites(topic)
    related = neo4j_tool.get_related_topics(topic)
    logger.info(f"Prerequisites: {prerequisites}, Related: {related}")
    return {
        **state,
        "prerequisites": prerequisites,
        "related_topics": related,
        "context_docs": [],  # Pinecone RAG — wired in Sprint 5
    }


# ─── Node 4: Generate hints with LLM ─────────────────────────────────────────

def node_generate_hints(state: HintState) -> HintState:
    """Call the LLM to generate N progressive Socratic hints, tailored to the user's current code."""
    req = state["request"]
    prerequisites = state.get("prerequisites", [])
    related = state.get("related_topics", [])
    user_code = req.get("user_code", "").strip()

    prereq_str = ", ".join(t["name"] for t in prerequisites) if prerequisites else "none"
    related_str = ", ".join(t["name"] for t in related) if related else "none"

    num_hints = min(req.get("hint_level", 3), settings.MAX_HINTS_PER_PROBLEM)

    system_prompt = """You are DSA Buddy — an expert competitive programming tutor.
Your role is to guide students using the Socratic method: NEVER give away the full solution.
When the student shares their code or approach, analyze EXACTLY what they are trying to do.
Point out what is correct, where they are going wrong, and nudge them toward the right path.
Generate hints that progressively reveal more information, from high-level intuition to specific details.
Each hint should be one clear, actionable sentence. Output ONLY a JSON array of strings."""

    # Build code context block
    if user_code:
        code_context = f"""
Student's current code approach:
```
{user_code[:1500]}
```
Analyze this approach specifically. Point out what's right, what's wrong, and guide them forward."""
    else:
        code_context = "No code provided yet — give general progressive hints."

    user_prompt = f"""Generate exactly {num_hints} progressive hints for this problem:

Problem: {req['problem_title']}
Difficulty: {req['difficulty']}
Tags: {', '.join(req['tags'])}
Prerequisite topics the student should know: {prereq_str}
What this problem teaches (next topics): {related_str}

{code_context}

Rules:
- Hint 1: Address the student's specific approach or give the key insight if no code provided
- Hint 2: Point to the correct data structure or algorithm family
- Hint 3: Describe the key algorithmic step they're missing
- Hint 4: Describe the correct iteration/traversal approach in their context
- Hint 5 (if requested): Describe the exact fix or implementation detail

IMPORTANT: If user code is provided, make hints SPECIFIC to their code, not generic.
Output format (JSON array only, no markdown):
["hint 1 text", "hint 2 text", ...]"""

    # Graceful fallback if no API key configured
    if not settings.GEMINI_API_KEY:
        logger.warning("No GEMINI_API_KEY — using fallback hints")
        hints = _fallback_hints(req["problem_title"], num_hints)
        return {**state, "hints": hints}

    try:
        llm = _get_llm()
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        import json
        raw = response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        hints = json.loads(raw.strip())
        if not isinstance(hints, list):
            raise ValueError("LLM did not return a list")
        logger.info(f"Generated {len(hints)} hints for {req['problem_slug']}")
        return {**state, "hints": hints}
    except Exception as e:
        logger.error(f"LLM hint generation failed: {e}")
        return {**state, "hints": _fallback_hints(req["problem_title"], num_hints), "error": str(e)}


def _fallback_hints(title: str, count: int) -> list[str]:
    """Rule-based fallback when LLM is unavailable."""
    templates = [
        f"Think carefully about what data structure would give you O(1) lookups for '{title}'.",
        "Consider whether you need to look at each element more than once.",
        "A hash map can store relationships between elements as you iterate.",
        "Process elements left-to-right and check what you've already seen.",
        "The answer can be constructed in a single pass — no nested loops needed.",
    ]
    return templates[:count]


# ─── Node 5: Store in Redis cache ────────────────────────────────────────────

def node_store_cache(state: HintState) -> HintState:
    """Persist the generated hints in Redis for future requests."""
    req = state["request"]
    hints = state.get("hints", [])
    if hints:
        redis_cache.set_hints(req["user_id"], req["problem_slug"], hints)
    return state


# ─── Routing function ─────────────────────────────────────────────────────────

def route_after_cache_check(state: HintState) -> str:
    """If cache hit → return results directly; else → run pipeline."""
    return "return_cached" if state.get("cache_hit") else "classify_topic"
