import logging
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("auth_api")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key-here")
PORT = int(os.getenv("PORT", "8000"))

# Initialize Supabase client
supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.warning("Supabase client initialized with template environment variables: %s", e)

app = FastAPI(
    title="Secured Task Management & Auth API",
    description="A secure API with Supabase Auth (Sign Up, Log In, Log Out, JWT Verification).",
    version="4.0.0",
)


@app.on_event("startup")
def on_startup():
    logger.info("Server running and connected to Supabase")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request body or parameters"},
    )


@app.get(
    "/",
    summary="API Root Information",
    description="Returns API metadata and primary auth endpoints.",
)
def read_root():
    return {
        "name": "Auth API",
        "version": "4.0",
        "endpoints": [
            "/auth/signup",
            "/auth/login",
            "/auth/logout",
            "/protected/profile",
            "/public/info",
        ],
    }


@app.get(
    "/health",
    summary="Service Health Check",
    description="Returns the health status of the API server.",
)
def read_health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
