"""
LangGraph pipeline definition — compiles the hint generation graph.

Graph topology:
                          ┌──────────────────┐
                          │  check_cache     │
                          └──────┬───────────┘
                    cache hit ╱       ╲ miss
                            ╱           ╲
               ┌────────────────┐   ┌──────────────────┐
               │ return_cached  │   │  classify_topic  │
               └────────────────┘   └──────────────────┘
                                            │
                                    ┌───────────────┐
                                    │ enrich_context│
                                    └───────────────┘
                                            │
                                    ┌───────────────┐
                                    │ generate_hints│
                                    └───────────────┘
                                            │
                                    ┌───────────────┐
                                    │  store_cache  │
                                    └───────────────┘
                                            │
                                           END
"""
import logging
from langgraph.graph import StateGraph, END
from app.graph.state import HintState
from app.graph.nodes import (
    node_check_cache,
    node_classify_topic,
    node_enrich_context,
    node_generate_hints,
    node_store_cache,
    route_after_cache_check,
)

logger = logging.getLogger(__name__)


def build_hint_graph():
    """Compile the LangGraph hint generation pipeline."""
    graph = StateGraph(HintState)

    # Register nodes
    graph.add_node("check_cache", node_check_cache)
    graph.add_node("return_cached", lambda s: s)   # pass-through terminal
    graph.add_node("classify_topic", node_classify_topic)
    graph.add_node("enrich_context", node_enrich_context)
    graph.add_node("generate_hints", node_generate_hints)
    graph.add_node("store_cache", node_store_cache)

    # Entry point
    graph.set_entry_point("check_cache")

    # Conditional routing after cache check
    graph.add_conditional_edges(
        "check_cache",
        route_after_cache_check,
        {
            "return_cached": "return_cached",
            "classify_topic": "classify_topic",
        }
    )

    # Linear pipeline
    graph.add_edge("classify_topic", "enrich_context")
    graph.add_edge("enrich_context", "generate_hints")
    graph.add_edge("generate_hints", "store_cache")

    # Terminal edges
    graph.add_edge("return_cached", END)
    graph.add_edge("store_cache", END)

    compiled = graph.compile()
    logger.info("LangGraph hint pipeline compiled successfully")
    return compiled


# Singleton compiled graph
hint_graph = build_hint_graph()
