"""
Seed script — inserts a curated set of LeetCode problems into the problems table.
Run with: docker compose exec postgres psql -U dsabuddy -d dsabuddy -f /tmp/seed_problems.sql
Or run this Python script directly.
"""
import asyncio
import asyncpg
import os

PROBLEMS = [
    # EASY
    ("two-sum", "Two Sum", "easy", ["array", "hash-table"]),
    ("valid-parentheses", "Valid Parentheses", "easy", ["string", "stack"]),
    ("merge-two-sorted-lists", "Merge Two Sorted Lists", "easy", ["linked-list", "recursion"]),
    ("best-time-to-buy-and-sell-stock", "Best Time to Buy and Sell Stock", "easy", ["array", "dynamic-programming"]),
    ("contains-duplicate", "Contains Duplicate", "easy", ["array", "hash-table"]),
    ("maximum-subarray", "Maximum Subarray", "easy", ["array", "divide-and-conquer", "dynamic-programming"]),
    ("climbing-stairs", "Climbing Stairs", "easy", ["math", "dynamic-programming", "memoization"]),
    ("binary-search", "Binary Search", "easy", ["array", "binary-search"]),
    ("reverse-linked-list", "Reverse Linked List", "easy", ["linked-list", "recursion"]),
    ("palindrome-number", "Palindrome Number", "easy", ["math"]),
    ("roman-to-integer", "Roman to Integer", "easy", ["hash-table", "math", "string"]),
    ("single-number", "Single Number", "easy", ["array", "bit-manipulation"]),
    ("majority-element", "Majority Element", "easy", ["array", "hash-table", "divide-and-conquer"]),
    ("missing-number", "Missing Number", "easy", ["array", "hash-table", "bit-manipulation"]),
    ("first-bad-version", "First Bad Version", "easy", ["binary-search", "interactive"]),

    # MEDIUM
    ("add-two-numbers", "Add Two Numbers", "medium", ["linked-list", "math", "recursion"]),
    ("longest-substring-without-repeating-characters", "Longest Substring Without Repeating Characters", "medium", ["hash-table", "string", "sliding-window"]),
    ("container-with-most-water", "Container With Most Water", "medium", ["array", "two-pointers", "greedy"]),
    ("3sum", "3Sum", "medium", ["array", "two-pointers", "sorting"]),
    ("letter-combinations-of-a-phone-number", "Letter Combinations of a Phone Number", "medium", ["hash-table", "string", "backtracking"]),
    ("remove-nth-node-from-end-of-list", "Remove Nth Node From End of List", "medium", ["linked-list", "two-pointers"]),
    ("search-in-rotated-sorted-array", "Search in Rotated Sorted Array", "medium", ["array", "binary-search"]),
    ("combination-sum", "Combination Sum", "medium", ["array", "backtracking"]),
    ("rotate-image", "Rotate Image", "medium", ["array", "math", "matrix"]),
    ("group-anagrams", "Group Anagrams", "medium", ["array", "hash-table", "string", "sorting"]),
    ("jump-game", "Jump Game", "medium", ["array", "dynamic-programming", "greedy"]),
    ("merge-intervals", "Merge Intervals", "medium", ["array", "sorting"]),
    ("unique-paths", "Unique Paths", "medium", ["math", "dynamic-programming", "combinatorics"]),
    ("word-search", "Word Search", "medium", ["array", "backtracking", "matrix"]),
    ("decode-ways", "Decode Ways", "medium", ["string", "dynamic-programming"]),
    ("validate-binary-search-tree", "Validate Binary Search Tree", "medium", ["tree", "depth-first-search", "binary-search-tree"]),
    ("kth-smallest-element-in-a-bst", "Kth Smallest Element in a BST", "medium", ["tree", "depth-first-search", "binary-search-tree"]),
    ("coin-change", "Coin Change", "medium", ["array", "dynamic-programming", "breadth-first-search"]),
    ("product-of-array-except-self", "Product of Array Except Self", "medium", ["array", "prefix-sum"]),
    ("find-minimum-in-rotated-sorted-array", "Find Minimum in Rotated Sorted Array", "medium", ["array", "binary-search"]),
    ("number-of-islands", "Number of Islands", "medium", ["array", "depth-first-search", "breadth-first-search", "union-find", "matrix"]),
    ("course-schedule", "Course Schedule", "medium", ["depth-first-search", "breadth-first-search", "graph", "topological-sort"]),
    ("implement-trie-prefix-tree", "Implement Trie (Prefix Tree)", "medium", ["hash-table", "string", "design", "trie"]),
    ("top-k-frequent-elements", "Top K Frequent Elements", "medium", ["array", "hash-table", "divide-and-conquer", "sorting", "heap"]),
    ("find-all-anagrams-in-a-string", "Find All Anagrams in a String", "medium", ["hash-table", "string", "sliding-window"]),
    ("subarray-sum-equals-k", "Subarray Sum Equals K", "medium", ["array", "hash-table", "prefix-sum"]),
    ("longest-palindromic-substring", "Longest Palindromic Substring", "medium", ["two-pointers", "string", "dynamic-programming"]),
    ("pacific-atlantic-water-flow", "Pacific Atlantic Water Flow", "medium", ["array", "depth-first-search", "breadth-first-search", "matrix"]),

    # HARD
    ("median-of-two-sorted-arrays", "Median of Two Sorted Arrays", "hard", ["array", "binary-search", "divide-and-conquer"]),
    ("regular-expression-matching", "Regular Expression Matching", "hard", ["string", "dynamic-programming", "recursion"]),
    ("trapping-rain-water", "Trapping Rain Water", "hard", ["array", "two-pointers", "dynamic-programming", "stack"]),
    ("n-queens", "N-Queens", "hard", ["array", "backtracking"]),
    ("serialize-and-deserialize-binary-tree", "Serialize and Deserialize Binary Tree", "hard", ["string", "tree", "depth-first-search", "breadth-first-search", "design", "binary-tree"]),
    ("word-ladder-ii", "Word Ladder II", "hard", ["hash-table", "string", "backtracking", "breadth-first-search"]),
    ("sliding-window-maximum", "Sliding Window Maximum", "hard", ["array", "queue", "sliding-window", "heap", "monotonic-queue"]),
    ("minimum-window-substring", "Minimum Window Substring", "hard", ["hash-table", "string", "sliding-window"]),
    ("largest-rectangle-in-histogram", "Largest Rectangle in Histogram", "hard", ["array", "stack", "monotonic-stack"]),
    ("binary-tree-maximum-path-sum", "Binary Tree Maximum Path Sum", "hard", ["dynamic-programming", "tree", "depth-first-search", "binary-tree"]),
]

async def seed():
    db_url = os.getenv("DATABASE_URL", "postgresql://dsabuddy:change_me_in_prod@localhost:5432/dsabuddy")
    # Convert asyncpg-style URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    inserted = 0
    skipped = 0
    for slug, title, difficulty, tags in PROBLEMS:
        try:
            await conn.execute("""
                INSERT INTO problems (slug, title, difficulty, tags, platform)
                VALUES ($1, $2, $3, $4, 'leetcode')
                ON CONFLICT (slug) DO NOTHING
            """, slug, title, difficulty, tags)
            inserted += 1
        except Exception as e:
            print(f"  SKIP {slug}: {e}")
            skipped += 1
    await conn.close()
    print(f"✅ Seeded {inserted} problems ({skipped} already existed)")

if __name__ == "__main__":
    asyncio.run(seed())
