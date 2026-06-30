from typing import List, Dict

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.problem_slug: str = None
        self.problem_title: str = None

class TrieIndex:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, title: str, slug: str):
        node = self.root
        # Insert both full title and lowercase for case-insensitive search
        word = title.lower()
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.problem_slug = slug
        node.problem_title = title

    def search(self, prefix: str, limit: int = 10) -> List[Dict[str, str]]:
        node = self.root
        prefix = prefix.lower()
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]

        results = []
        self._dfs(node, results, limit)
        return results

    def _dfs(self, node: TrieNode, results: List[Dict[str, str]], limit: int):
        if len(results) >= limit:
            return
        if node.is_end:
            results.append({"title": node.problem_title, "slug": node.problem_slug})
        for char, child in node.children.items():
            self._dfs(child, results, limit)

# Global singleton
problem_trie = TrieIndex()
