from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/google")
async def login_via_google():
    # Scaffold for Google OAuth
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = "http://localhost/api/auth/oauth/google/callback"
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile"
    return RedirectResponse(auth_url)

@router.get("/google/callback")
async def google_callback(code: str):
    # This is a scaffold. We'd exchange code for token here.
    return {"message": "OAuth successful (Scaffold)", "code": code}
