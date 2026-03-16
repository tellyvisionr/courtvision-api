# app/main.py

from fastapi import FastAPI, HTTPException
from pathlib import Path
import os
import httpx
from dotenv import load_dotenv

# --- Config / Env ---
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")  # load .env from repo root explicitly

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
BALLDONTLIE_BASE_URL = os.getenv("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")

if not BALLDONTLIE_API_KEY:
    raise RuntimeError("Missing BALLDONTLIE_API_KEY environment variable")

# --- App ---
app = FastAPI(title="Courtvision API", version="0.1.0")

# --- Upstream helper ---
async def fetch_from_balldontlie(endpoint: str, params: dict | None = None):
    headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}
    url = f"{BALLDONTLIE_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            # Bubble up upstream status to the client for transparency
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/players/{player_name}")
async def get_player(player_name: str):
    """Search players by name"""
    data = await fetch_from_balldontlie("players", {"search": player_name})
    return data

@app.get("/teams")
async def get_teams():
    """Return all NBA teams"""
    data = await fetch_from_balldontlie("teams")
    return data
