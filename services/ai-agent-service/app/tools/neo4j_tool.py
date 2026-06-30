"""
Neo4j tool — traverses the DSA topic graph to find prerequisite topics
and related problems for a given problem slug/topic.
"""
import logging
from typing import Any
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jTool:
    def __init__(self):
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return self._driver

    def get_prerequisites(self, topic: str) -> list[dict]:
        """Return the immediate prerequisite topics for a given topic slug."""
        driver = self._get_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Topic {slug: $slug})<-[:REQUIRES]-(pre:Topic)
                    RETURN pre.slug AS slug, pre.name AS name
                    """,
                    slug=topic
                )
                return [{"slug": r["slug"], "name": r["name"]} for r in result]
        except Exception as e:
            logger.warning(f"Neo4j prerequisite query failed for {topic}: {e}")
            return []

    def get_related_topics(self, topic: str, limit: int = 5) -> list[dict]:
        """Return topics that come after this one in the graph (next steps)."""
        driver = self._get_driver()
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Topic {slug: $slug})-[:REQUIRES]->(next:Topic)
                    RETURN next.slug AS slug, next.name AS name
                    LIMIT $limit
                    """,
                    slug=topic, limit=limit
                )
                return [{"slug": r["slug"], "name": r["name"]} for r in result]
        except Exception as e:
            logger.warning(f"Neo4j related topics query failed: {e}")
            return []

    def classify_topic(self, problem_title: str, tags: list[str]) -> str:
        """Heuristic: map problem tags to a known topic node slug."""
        tag_to_topic = {
            "dynamic-programming": "dynamic-programming",
            "dp": "dynamic-programming",
            "graph": "graph-traversal",
            "depth-first-search": "depth-first-search",
            "breadth-first-search": "breadth-first-search",
            "binary-search": "binary-search",
            "two-pointers": "two-pointers",
            "sliding-window": "sliding-window",
            "hash-table": "hashing",
            "heap": "heaps-priority-queues",
            "priority-queue": "heaps-priority-queues",
            "trie": "trie",
            "tree": "binary-trees",
            "linked-list": "linked-lists",
            "stack": "stacks-queues",
            "queue": "stacks-queues",
            "array": "arrays-strings",
            "string": "arrays-strings",
            "sort": "sorting",
            "sorting": "sorting",
            "greedy": "greedy",
            "backtracking": "backtracking",
            "bit-manipulation": "bit-manipulation",
        }
        for tag in tags:
            slug = tag.lower().replace(" ", "-")
            if slug in tag_to_topic:
                return tag_to_topic[slug]
        return "arrays-strings"  # fallback

    def close(self):
        if self._driver:
            self._driver.close()


neo4j_tool = Neo4jTool()
