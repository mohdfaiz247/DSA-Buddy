from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_tags():
    # Scaffold
    return ["array", "hash-table", "dynamic-programming", "math", "string"]
