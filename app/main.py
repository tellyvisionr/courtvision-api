# app/main.py

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
import httpx

from app.clients.balldontlie import BallDontLieClient
from app.db import crud
from app.db.database import engine, get_session
from app.db.models import Base
from app.instrumentation import instrument_app
from app.logging_config import setup_logging
from app.middleware import AccessLogMiddleware, RequestIDMiddleware
from app.models import (
    CompareResponse,
    ErrorResponse,
    PlayerSearchResponse,
    SeasonAveragesResponse,
)
from app.services import ingest, predict
from app.telemetry import init_telemetry

# --- Config / Env ---
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")  # load .env from repo root explicitly

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
BALLDONTLIE_BASE_URL = os.getenv("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")

if not BALLDONTLIE_API_KEY:
    raise RuntimeError("Missing BALLDONTLIE_API_KEY environment variable")

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
init_telemetry()

logger = logging.getLogger(__name__)


def _safe(value: object) -> str:
    """Sanitize a value for safe logging — prevents log injection (CWE-117).

    Converts to string and strips carriage returns and newlines so that
    attacker-controlled input cannot forge additional log lines.
    """
    return str(value).replace("\r", "").replace("\n", "")


# --- Lifespan: create DB tables on startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")
    except Exception:
        # DB unavailable (e.g. CI, local dev without postgres) — start anyway.
        logger.warning("Database unavailable — starting without persistence")
    yield


# --- App ---
app = FastAPI(title="Courtvision API", version="0.1.0", lifespan=lifespan)

instrument_app(app)

# Middleware: add AccessLog first so RequestID runs first (Starlette reverses order).
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIDMiddleware)


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
    session=Depends(get_session),
):
    """Search for players by name and persist results to the database."""
    try:
        result = await client.search_players(name)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Upstream HTTP %d during player search %s", e.response.status_code, _safe(name)
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except httpx.TransportError as e:
        logger.warning("Transport error during player search: %s", e)
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}") from e

    for player in result.data:
        await crud.upsert_player(session, player)
    await session.commit()
    logger.info("Persisted %d players for query %s", len(result.data), _safe(name))

    return result


@app.get(
    "/players/{player_id}/season-averages",
    response_model=SeasonAveragesResponse,
    responses={503: {"model": ErrorResponse}},
)
async def get_season_averages(
    player_id: int,
    season: int = Query(..., description="NBA season year, e.g. 2023"),
    client: BallDontLieClient = Depends(get_bdl_client),
    session=Depends(get_session),
):
    """Get season averages for a player and persist results to the database."""
    try:
        result = await client.get_season_averages(player_id, season)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Upstream HTTP %d for player %s season averages",
            e.response.status_code,
            _safe(player_id),
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except httpx.TransportError as e:
        logger.warning("Transport error fetching season averages: %s", e)
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}") from e

    for avg in result.data:
        await crud.upsert_season_average(session, avg)
    await session.commit()

    return result


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
        logger.warning("Upstream HTTP %d during compare search", e.response.status_code)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except httpx.TransportError as e:
        logger.warning("Transport error during compare: %s", e)
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}") from e

    if not r1.data:
        raise HTTPException(status_code=404, detail=f"Player not found: {player1!r}")
    if not r2.data:
        raise HTTPException(status_code=404, detail=f"Player not found: {player2!r}")

    try:
        avg1 = await client.get_season_averages(r1.data[0].id, season)
        avg2 = await client.get_season_averages(r2.data[0].id, season)
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream HTTP %d fetching compare averages", e.response.status_code)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except httpx.TransportError as e:
        logger.warning("Transport error fetching compare averages: %s", e)
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}") from e

    return CompareResponse(
        player1=avg1.data[0] if avg1.data else None,
        player2=avg2.data[0] if avg2.data else None,
    )


@app.post(
    "/ingest/{season}",
    responses={503: {"model": ErrorResponse}},
)
async def ingest_season_data(
    season: int,
    client: BallDontLieClient = Depends(get_bdl_client),
    session=Depends(get_session),
):
    """Bulk ingest all teams, games, and player box scores for a season.

    Long-running — intended for manual invocation, not latency-sensitive paths.
    Returns a summary of how many rows were written.
    """
    logger.info("Starting season %s ingestion", _safe(season))
    try:
        summary = await ingest.ingest_season(client, session, season)
    except httpx.TransportError as e:
        logger.warning("Transport error during ingestion: %s", e)
        raise HTTPException(status_code=503, detail=f"Upstream unreachable: {e}") from e
    logger.info("Completed season %s ingestion: %s", _safe(season), _safe(summary))
    return summary


@app.get(
    "/predict/player",
    responses={400: {"model": ErrorResponse}},
)
async def predict_player(
    player_id: int = Query(..., description="Player ID from balldontlie"),
    opponent_team_id: int = Query(..., description="Opponent team ID"),
    session=Depends(get_session),
):
    """Predict player stats (pts/ast/reb) against a specific opponent.

    Uses linear regression trained on the player's historical game logs.
    Requires data ingestion via POST /ingest/{season} first.
    """
    result = await predict.predict_player_game(session, player_id, opponent_team_id)
    if "error" in result:
        logger.info(
            "Insufficient data for player %s vs team %s: %s",
            _safe(player_id),
            _safe(opponent_team_id),
            _safe(result.get("error")),
        )
        raise HTTPException(status_code=400, detail=result)
    logger.info(
        "Player %s prediction vs team %s: pts=%s",
        _safe(player_id),
        _safe(opponent_team_id),
        _safe(result["predicted_pts"]),
    )
    return result


@app.get(
    "/predict/game",
    responses={400: {"model": ErrorResponse}},
)
async def predict_game(
    home_team_id: int = Query(..., description="Home team ID"),
    away_team_id: int = Query(..., description="Away team ID"),
    session=Depends(get_session),
):
    """Predict game outcome (win probability) for a matchup.

    Uses logistic regression trained on historical game results.
    Requires data ingestion via POST /ingest/{season} first.
    """
    result = await predict.predict_game_outcome(session, home_team_id, away_team_id)
    if "error" in result:
        logger.info(
            "Insufficient data for game %s vs %s: %s",
            _safe(home_team_id),
            _safe(away_team_id),
            _safe(result.get("error")),
        )
        raise HTTPException(status_code=400, detail=result)
    logger.info(
        "Game prediction %s vs %s: home_win=%s",
        _safe(home_team_id),
        _safe(away_team_id),
        _safe(result["home_win_probability"]),
    )
    return result
