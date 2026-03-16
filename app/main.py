# app/main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from pathlib import Path
import os
import httpx
from dotenv import load_dotenv

from app.clients.balldontlie import BallDontLieClient
from app.models import (
    CompareResponse,
    ErrorResponse,
    PlayerSearchResponse,
    SeasonAveragesResponse,
)

# --- Config / Env ---
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")  # load .env from repo root explicitly

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
BALLDONTLIE_BASE_URL = os.getenv("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")

if not BALLDONTLIE_API_KEY:
    raise RuntimeError("Missing BALLDONTLIE_API_KEY environment variable")

# --- App ---
app = FastAPI(title="Courtvision API", version="0.1.0")

# --- Upstream helper (legacy) ---
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


# --- Dependency ---
async def get_bdl_client():
    async with BallDontLieClient() as client:
        yield client


# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get(
    "/players/search",
    response_model=PlayerSearchResponse,
    responses={503: {"model": ErrorResponse}},
)
async def search_players(
    name: str = Query(..., description="Player name to search for"),
    client: BallDontLieClient = Depends(get_bdl_client),
):
    """Search for players by name."""
    try:
        return await client.search_players(name)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.TransportError as e:
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}")


@app.get(
    "/players/{player_id}/season-averages",
    response_model=SeasonAveragesResponse,
    responses={503: {"model": ErrorResponse}},
)
async def get_season_averages(
    player_id: int,
    season: int = Query(..., description="NBA season year, e.g. 2023"),
    client: BallDontLieClient = Depends(get_bdl_client),
):
    """Get season averages for a player."""
    try:
        return await client.get_season_averages(player_id, season)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.TransportError as e:
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}")


@app.get(
    "/compare",
    response_model=CompareResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def compare_players(
    player1: str = Query(..., description="First player name"),
    player2: str = Query(..., description="Second player name"),
    season: int = Query(..., description="NBA season year, e.g. 2023"),
    client: BallDontLieClient = Depends(get_bdl_client),
):
    """Compare season averages for two players by name."""
    try:
        r1, r2 = await client.search_players(player1), await client.search_players(player2)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.TransportError as e:
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}")

    if not r1.data:
        raise HTTPException(status_code=404, detail=f"Player not found: {player1!r}")
    if not r2.data:
        raise HTTPException(status_code=404, detail=f"Player not found: {player2!r}")

    try:
        avg1 = await client.get_season_averages(r1.data[0].id, season)
        avg2 = await client.get_season_averages(r2.data[0].id, season)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.TransportError as e:
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}")

    return CompareResponse(
        player1=avg1.data[0] if avg1.data else None,
        player2=avg2.data[0] if avg2.data else None,
    )


# --- Legacy routes ---
@app.get("/players/{player_name}")
async def get_player(player_name: str):
    """Search players by name (legacy)."""
    data = await fetch_from_balldontlie("players", {"search": player_name})
    return data


@app.get("/teams/{team_name}")
async def get_teams(team_name: str):
    """Search team by name."""
    data = await fetch_from_balldontlie("teams", {"search": team_name})
    return data
