"""Tests for the data ingestion service and /ingest/{season} endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import app, get_bdl_client

BASE = "https://api.balldontlie.io/v1"

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TEAM_LAL = {
    "id": 14,
    "conference": "West",
    "division": "Pacific",
    "city": "Los Angeles",
    "name": "Lakers",
    "full_name": "Los Angeles Lakers",
    "abbreviation": "LAL",
}

TEAM_GSW = {
    "id": 10,
    "conference": "West",
    "division": "Pacific",
    "city": "Golden State",
    "name": "Warriors",
    "full_name": "Golden State Warriors",
    "abbreviation": "GSW",
}

PLAYER_LEBRON = {
    "id": 237,
    "first_name": "LeBron",
    "last_name": "James",
    "position": "F",
    "height": "6-9",
    "weight": "250",
    "jersey_number": "23",
    "college": None,
    "country": "USA",
    "draft_year": 2003,
    "draft_round": 1,
    "draft_number": 1,
    "team": TEAM_LAL,
}

GAME_1 = {
    "id": 1001,
    "date": "2024-01-15",
    "season": 2024,
    "status": "Final",
    "postseason": False,
    "home_team_score": 110,
    "visitor_team_score": 105,
    "home_team": TEAM_LAL,
    "visitor_team": TEAM_GSW,
}

GAME_2 = {
    "id": 1002,
    "date": "2024-01-16",
    "season": 2024,
    "status": "Final",
    "postseason": False,
    "home_team_score": 120,
    "visitor_team_score": 115,
    "home_team": TEAM_GSW,
    "visitor_team": TEAM_LAL,
}

STAT_ROW = {
    "id": 5001,
    "min": "35:00",
    "pts": 28,
    "ast": 7,
    "reb": 8,
    "oreb": 1,
    "dreb": 7,
    "stl": 1,
    "blk": 0,
    "turnover": 3,
    "pf": 2,
    "plus_minus": 5,
    "fgm": 10,
    "fga": 20,
    "fg_pct": 0.5,
    "fg3m": 2,
    "fg3a": 5,
    "fg3_pct": 0.4,
    "ftm": 6,
    "fta": 7,
    "ft_pct": 0.857,
    "player": PLAYER_LEBRON,
    "team": TEAM_LAL,
    "game": GAME_1,
}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# ingest_teams
# ---------------------------------------------------------------------------


async def test_ingest_teams():
    from app.services.ingest import ingest_teams

    mock_client = AsyncMock()
    mock_client.get_all_teams.return_value = [TEAM_LAL, TEAM_GSW]

    mock_session = AsyncMock()
    with patch("app.services.ingest.crud.upsert_team", new_callable=AsyncMock) as mock_upsert:
        count = await ingest_teams(mock_client, mock_session)

    assert count == 2
    assert mock_upsert.call_count == 2
    mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# ingest_games — pagination
# ---------------------------------------------------------------------------


async def test_ingest_games_paginates():
    """Two pages of results then next_cursor=None stops the loop."""
    from app.services.ingest import ingest_games

    page1 = {"data": [GAME_1], "meta": {"next_cursor": 99, "per_page": 1}}
    page2 = {"data": [GAME_2], "meta": {"next_cursor": None, "per_page": 1}}

    mock_client = AsyncMock()
    mock_client.get_games.side_effect = [page1, page2]

    mock_session = AsyncMock()
    with patch("app.services.ingest.crud.upsert_game", new_callable=AsyncMock):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            count = await ingest_games(mock_client, mock_session, season=2024)

    assert count == 2
    assert mock_client.get_games.call_count == 2
    # First call: no cursor; second call: cursor=99
    mock_client.get_games.assert_any_call(season=2024, cursor=None)
    mock_client.get_games.assert_any_call(season=2024, cursor=99)


async def test_ingest_games_single_page():
    from app.services.ingest import ingest_games

    page = {"data": [GAME_1], "meta": {"next_cursor": None, "per_page": 100}}

    mock_client = AsyncMock()
    mock_client.get_games.return_value = page

    mock_session = AsyncMock()
    with patch("app.services.ingest.crud.upsert_game", new_callable=AsyncMock):
        count = await ingest_games(mock_client, mock_session, season=2024)

    assert count == 1


# ---------------------------------------------------------------------------
# ingest_game_stats
# ---------------------------------------------------------------------------


async def test_ingest_game_stats():
    from app.services.ingest import ingest_game_stats

    page = {"data": [STAT_ROW], "meta": {"next_cursor": None, "per_page": 100}}

    mock_client = AsyncMock()
    mock_client.get_game_stats.return_value = page

    mock_session = AsyncMock()
    with patch("app.services.ingest.crud.upsert_game_stats", new_callable=AsyncMock) as mock_ups:
        count = await ingest_game_stats(mock_client, mock_session, game_id=1001)

    assert count == 1
    mock_ups.assert_called_once()
    mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# /ingest/{season} endpoint
# ---------------------------------------------------------------------------


async def test_ingest_endpoint_returns_summary():
    """Endpoint returns the summary dict from ingest_season."""
    expected = {"season": 2024, "teams": 30, "games": 82, "game_stats": 1640}

    mock_bdl = AsyncMock()

    async def _override():
        yield mock_bdl

    app.dependency_overrides[get_bdl_client] = _override

    with patch("app.main.ingest.ingest_season", new_callable=AsyncMock) as mock_ingest:
        mock_ingest.return_value = expected
        async with _client() as ac:
            r = await ac.post("/ingest/2024")

    app.dependency_overrides.pop(get_bdl_client, None)

    assert r.status_code == 200
    assert r.json() == expected


async def test_ingest_endpoint_503_on_transport_error():
    mock_bdl = AsyncMock()

    async def _override():
        yield mock_bdl

    app.dependency_overrides[get_bdl_client] = _override

    with patch("app.main.ingest.ingest_season", new_callable=AsyncMock) as mock_ingest:
        mock_ingest.side_effect = httpx.ConnectError("upstream down")
        async with _client() as ac:
            r = await ac.post("/ingest/2024")

    app.dependency_overrides.pop(get_bdl_client, None)

    assert r.status_code == 503
