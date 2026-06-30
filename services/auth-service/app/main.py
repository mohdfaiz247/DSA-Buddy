from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, oauth

app = FastAPI(title="DSA Buddy - Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="", tags=["Auth"])
app.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auth"}
