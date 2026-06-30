import os
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load from environment variables (assuming running via docker or with .env sourced)
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
password = os.getenv("NEO4J_PASSWORD", "change_me_in_prod")
user = "neo4j"

CYPHER_SCRIPT = """
// Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.slug IS UNIQUE;

// Topics
CREATE (arrays:Topic {slug: "arrays", display_name: "Arrays", avg_hours: 3.0, interview_frequency: 0.90})
CREATE (binary_search:Topic {slug: "binary_search", display_name: "Binary Search", avg_hours: 4.0, interview_frequency: 0.72})
CREATE (two_pointers:Topic {slug: "two_pointers", display_name: "Two Pointers", avg_hours: 3.5, interview_frequency: 0.65})
CREATE (prefix_sum:Topic {slug: "prefix_sum", display_name: "Prefix Sum", avg_hours: 2.0, interview_frequency: 0.40})
CREATE (sliding_window:Topic {slug: "sliding_window", display_name: "Sliding Window", avg_hours: 4.5, interview_frequency: 0.60})
CREATE (recursion:Topic {slug: "recursion", display_name: "Recursion", avg_hours: 5.0, interview_frequency: 0.30})
CREATE (dfs:Topic {slug: "dfs", display_name: "Depth-First Search", avg_hours: 6.0, interview_frequency: 0.80})
CREATE (bfs:Topic {slug: "bfs", display_name: "Breadth-First Search", avg_hours: 5.5, interview_frequency: 0.75})
CREATE (backtracking:Topic {slug: "backtracking", display_name: "Backtracking", avg_hours: 6.5, interview_frequency: 0.50})
CREATE (topological_sort:Topic {slug: "topological_sort", display_name: "Topological Sort", avg_hours: 3.0, interview_frequency: 0.45})
CREATE (union_find:Topic {slug: "union_find", display_name: "Union Find", avg_hours: 4.0, interview_frequency: 0.35})
CREATE (binary_search_on_answer:Topic {slug: "binary_search_on_answer", display_name: "Binary Search on Answer", avg_hours: 4.5, interview_frequency: 0.55})
CREATE (hashmap:Topic {slug: "hashmap", display_name: "Hashmap", avg_hours: 2.5, interview_frequency: 0.85})
CREATE (sorting:Topic {slug: "sorting", display_name: "Sorting", avg_hours: 3.5, interview_frequency: 0.50})
CREATE (two_sum_pattern:Topic {slug: "two_sum_pattern", display_name: "Two Sum Pattern", avg_hours: 2.0, interview_frequency: 0.70})
CREATE (heap:Topic {slug: "heap", display_name: "Heap / Priority Queue", avg_hours: 4.0, interview_frequency: 0.65})
CREATE (dijkstra:Topic {slug: "dijkstra", display_name: "Dijkstra's Algorithm", avg_hours: 5.0, interview_frequency: 0.40})
CREATE (k_way_merge:Topic {slug: "k_way_merge", display_name: "K-Way Merge", avg_hours: 3.5, interview_frequency: 0.25})
CREATE (dp_1d:Topic {slug: "dp_1d", display_name: "1D Dynamic Programming", avg_hours: 6.0, interview_frequency: 0.60})
CREATE (dp_2d:Topic {slug: "dp_2d", display_name: "2D Dynamic Programming", avg_hours: 7.0, interview_frequency: 0.50})
CREATE (dp_interval:Topic {slug: "dp_interval", display_name: "Interval DP", avg_hours: 5.5, interview_frequency: 0.20})
CREATE (dp_on_trees:Topic {slug: "dp_on_trees", display_name: "DP on Trees", avg_hours: 6.5, interview_frequency: 0.15})
CREATE (dp_on_graphs:Topic {slug: "dp_on_graphs", display_name: "DP on Graphs", avg_hours: 5.0, interview_frequency: 0.10})
CREATE (linked_list:Topic {slug: "linked_list", display_name: "Linked List", avg_hours: 3.0, interview_frequency: 0.60})

// Edges
CREATE (arrays)-[:PREREQUISITE_OF]->(binary_search)
CREATE (arrays)-[:PREREQUISITE_OF]->(two_pointers)
CREATE (arrays)-[:PREREQUISITE_OF]->(prefix_sum)
CREATE (arrays)-[:PREREQUISITE_OF]->(sliding_window)
CREATE (arrays)-[:PREREQUISITE_OF]->(hashmap)
CREATE (arrays)-[:PREREQUISITE_OF]->(sorting)
CREATE (arrays)-[:PREREQUISITE_OF]->(dp_1d)

CREATE (recursion)-[:PREREQUISITE_OF]->(dfs)
CREATE (recursion)-[:PREREQUISITE_OF]->(bfs)
CREATE (recursion)-[:PREREQUISITE_OF]->(backtracking)

CREATE (dfs)-[:PREREQUISITE_OF]->(topological_sort)
CREATE (dfs)-[:PREREQUISITE_OF]->(union_find)
CREATE (dfs)-[:PREREQUISITE_OF]->(dp_on_trees)

CREATE (binary_search)-[:PREREQUISITE_OF]->(binary_search_on_answer)

CREATE (hashmap)-[:PREREQUISITE_OF]->(two_sum_pattern)

CREATE (heap)-[:PREREQUISITE_OF]->(dijkstra)
CREATE (heap)-[:PREREQUISITE_OF]->(k_way_merge)

CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_2d)
CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_interval)
CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_on_trees)

CREATE (topological_sort)-[:PREREQUISITE_OF]->(dp_on_graphs)
"""

def seed_database():
    logger.info(f"Connecting to Neo4j at {uri}...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return

    with driver.session() as session:
        # First, clear existing to make script idempotent if needed (optional)
        session.run("MATCH (n:Topic) DETACH DELETE n")
        
        # We need to run statement by statement since neo4j python driver 
        # doesn't like multi-statement strings out of the box in a single run() 
        # unless wrapped in a transaction properly or split. 
        # A simpler way is to split by newline or CREATE blocks, or use apoc.
        # Let's execute the full cypher script using a transaction.
        
        # Create constraint separately
        try:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.slug IS UNIQUE;")
        except Exception as e:
            logger.warning(f"Constraint creation info: {e}")

        # Let's execute the creation in a single block using MERGE instead of CREATE to be safe, 
        # or just run it since we deleted all Topics.
        # Actually, python neo4j driver requires queries to be separated if they are distinct statements,
        # but a giant block of CREATEs without semicolons works as one statement!
        
        query = """
        CREATE (arrays:Topic {slug: "arrays", display_name: "Arrays", avg_hours: 3.0, interview_frequency: 0.90})
        CREATE (binary_search:Topic {slug: "binary_search", display_name: "Binary Search", avg_hours: 4.0, interview_frequency: 0.72})
        CREATE (two_pointers:Topic {slug: "two_pointers", display_name: "Two Pointers", avg_hours: 3.5, interview_frequency: 0.65})
        CREATE (prefix_sum:Topic {slug: "prefix_sum", display_name: "Prefix Sum", avg_hours: 2.0, interview_frequency: 0.40})
        CREATE (sliding_window:Topic {slug: "sliding_window", display_name: "Sliding Window", avg_hours: 4.5, interview_frequency: 0.60})
        CREATE (recursion:Topic {slug: "recursion", display_name: "Recursion", avg_hours: 5.0, interview_frequency: 0.30})
        CREATE (dfs:Topic {slug: "dfs", display_name: "Depth-First Search", avg_hours: 6.0, interview_frequency: 0.80})
        CREATE (bfs:Topic {slug: "bfs", display_name: "Breadth-First Search", avg_hours: 5.5, interview_frequency: 0.75})
        CREATE (backtracking:Topic {slug: "backtracking", display_name: "Backtracking", avg_hours: 6.5, interview_frequency: 0.50})
        CREATE (topological_sort:Topic {slug: "topological_sort", display_name: "Topological Sort", avg_hours: 3.0, interview_frequency: 0.45})
        CREATE (union_find:Topic {slug: "union_find", display_name: "Union Find", avg_hours: 4.0, interview_frequency: 0.35})
        CREATE (binary_search_on_answer:Topic {slug: "binary_search_on_answer", display_name: "Binary Search on Answer", avg_hours: 4.5, interview_frequency: 0.55})
        CREATE (hashmap:Topic {slug: "hashmap", display_name: "Hashmap", avg_hours: 2.5, interview_frequency: 0.85})
        CREATE (sorting:Topic {slug: "sorting", display_name: "Sorting", avg_hours: 3.5, interview_frequency: 0.50})
        CREATE (two_sum_pattern:Topic {slug: "two_sum_pattern", display_name: "Two Sum Pattern", avg_hours: 2.0, interview_frequency: 0.70})
        CREATE (heap:Topic {slug: "heap", display_name: "Heap / Priority Queue", avg_hours: 4.0, interview_frequency: 0.65})
        CREATE (dijkstra:Topic {slug: "dijkstra", display_name: "Dijkstra's Algorithm", avg_hours: 5.0, interview_frequency: 0.40})
        CREATE (k_way_merge:Topic {slug: "k_way_merge", display_name: "K-Way Merge", avg_hours: 3.5, interview_frequency: 0.25})
        CREATE (dp_1d:Topic {slug: "dp_1d", display_name: "1D Dynamic Programming", avg_hours: 6.0, interview_frequency: 0.60})
        CREATE (dp_2d:Topic {slug: "dp_2d", display_name: "2D Dynamic Programming", avg_hours: 7.0, interview_frequency: 0.50})
        CREATE (dp_interval:Topic {slug: "dp_interval", display_name: "Interval DP", avg_hours: 5.5, interview_frequency: 0.20})
        CREATE (dp_on_trees:Topic {slug: "dp_on_trees", display_name: "DP on Trees", avg_hours: 6.5, interview_frequency: 0.15})
        CREATE (dp_on_graphs:Topic {slug: "dp_on_graphs", display_name: "DP on Graphs", avg_hours: 5.0, interview_frequency: 0.10})
        CREATE (linked_list:Topic {slug: "linked_list", display_name: "Linked List", avg_hours: 3.0, interview_frequency: 0.60})
        
        CREATE (arrays)-[:PREREQUISITE_OF]->(binary_search)
        CREATE (arrays)-[:PREREQUISITE_OF]->(two_pointers)
        CREATE (arrays)-[:PREREQUISITE_OF]->(prefix_sum)
        CREATE (arrays)-[:PREREQUISITE_OF]->(sliding_window)
        CREATE (arrays)-[:PREREQUISITE_OF]->(hashmap)
        CREATE (arrays)-[:PREREQUISITE_OF]->(sorting)
        CREATE (arrays)-[:PREREQUISITE_OF]->(dp_1d)

        CREATE (recursion)-[:PREREQUISITE_OF]->(dfs)
        CREATE (recursion)-[:PREREQUISITE_OF]->(bfs)
        CREATE (recursion)-[:PREREQUISITE_OF]->(backtracking)

        CREATE (dfs)-[:PREREQUISITE_OF]->(topological_sort)
        CREATE (dfs)-[:PREREQUISITE_OF]->(union_find)
        CREATE (dfs)-[:PREREQUISITE_OF]->(dp_on_trees)

        CREATE (binary_search)-[:PREREQUISITE_OF]->(binary_search_on_answer)

        CREATE (hashmap)-[:PREREQUISITE_OF]->(two_sum_pattern)

        CREATE (heap)-[:PREREQUISITE_OF]->(dijkstra)
        CREATE (heap)-[:PREREQUISITE_OF]->(k_way_merge)

        CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_2d)
        CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_interval)
        CREATE (dp_1d)-[:PREREQUISITE_OF]->(dp_on_trees)

        CREATE (topological_sort)-[:PREREQUISITE_OF]->(dp_on_graphs)
        """
        session.run(query)
        logger.info("Successfully seeded Neo4j graph with 24 topics and edges.")

        # Verify
        result = session.run("MATCH (n:Topic) RETURN count(n) as count")
        count = result.single()["count"]
        logger.info(f"Verification: Found {count} Topic nodes.")

    driver.close()

if __name__ == "__main__":
    seed_database()
