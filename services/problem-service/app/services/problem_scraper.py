import httpx
import asyncio
from typing import List, Dict

async def fetch_leetcode_problems(limit: int = 500) -> List[Dict]:
    url = "https://leetcode.com/graphql"
    query = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList: questionList(
        categorySlug: $categorySlug
        limit: $limit
        skip: $skip
        filters: $filters
      ) {
        total: totalNum
        questions: data {
          acRate
          difficulty
          freqBar
          frontendQuestionId: questionFrontendId
          isFavor
          paidOnly: isPaidOnly
          status
          title
          titleSlug
          topicTags {
            name
            id
            slug
          }
          hasSolution
          hasVideoSolution
        }
      }
    }
    """
    
    variables = {
        "categorySlug": "",
        "skip": 0,
        "limit": limit,
        "filters": {}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"query": query, "variables": variables})
        data = response.json()
        
        questions = data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
        
        formatted_problems = []
        for q in questions:
            # Map difficulty correctly
            diff_map = {"Easy": "easy", "Medium": "medium", "Hard": "hard"}
            difficulty = diff_map.get(q.get("difficulty"), "medium")
            
            tags = [tag.get("slug") for tag in q.get("topicTags", [])]
            
            formatted_problems.append({
                "slug": q.get("titleSlug"),
                "title": q.get("title"),
                "difficulty": difficulty,
                "tags": tags,
                "platform": "leetcode"
            })
            
        return formatted_problems
