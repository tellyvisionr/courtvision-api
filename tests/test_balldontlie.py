"""
Tests for BallDontLieClient and the player/compare endpoints.

Mocked tests use respx to intercept httpx calls — no real network traffic.
Integration tests (marked with @pytest.mark.integration) hit the live API
and are skipped automatically when BALLDONTLIE_API_KEY is not a real key.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import httpx
from httpx import ASGITransport, AsyncClient, Response
import pytest
import respx

from app.clients.balldontlie import BallDontLieClient
from app.main import app, get_bdl_client

BASE = "https://api.balldontlie.io/v1"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    "team": {
        "id": 14,
        "conference": "West",
        "division": "Pacific",
        "city": "Los Angeles",
        "name": "Lakers",
        "full_name": "Los Angeles Lakers",
        "abbreviation": "LAL",
    },
}

PLAYER_CURRY = {
    "id": 115,
    "first_name": "Stephen",
    "last_name": "Curry",
    "position": "G",
    "height": "6-2",
    "weight": "185",
    "jersey_number": "30",
    "college": "Davidson",
    "country": "USA",
    "draft_year": 2009,
    "draft_round": 1,
    "draft_number": 7,
    "team": {
        "id": 10,
        "conference": "West",
        "division": "Pacific",
        "city": "Golden State",
        "name": "Warriors",
        "full_name": "Golden State Warriors",
        "abbreviation": "GSW",
    },
}

SEARCH_LEBRON = {"data": [PLAYER_LEBRON], "meta": {"next_cursor": None, "per_page": 25}}
SEARCH_CURRY = {"data": [PLAYER_CURRY], "meta": {"next_cursor": None, "per_page": 25}}
SEARCH_EMPTY = {"data": [], "meta": {"next_cursor": None, "per_page": 25}}

AVG_LEBRON = {
    "player_id": 237,
    "season": 2023,
    "games_played": 71,
    "pts": 25.7,
    "ast": 8.3,
    "reb": 7.3,
    "stl": 1.3,
    "blk": 0.5,
    "turnover": 3.5,
    "min": "35:11",
    "fgm": 9.6,
    "fga": 19.9,
    "fg_pct": 0.541,
    "fg3m": 2.4,
    "fg3a": 6.6,
    "fg3_pct": 0.41,
    "ftm": 4.1,
    "fta": 5.5,
    "ft_pct": 0.757,
}

AVG_CURRY = {
    "player_id": 115,
    "season": 2023,
    "games_played": 74,
    "pts": 26.4,
    "ast": 5.1,
    "reb": 4.5,
    "stl": 0.9,
    "blk": 0.4,
    "turnover": 3.0,
    "min": "33:32",
    "fgm": 10.0,
    "fga": 20.5,
    "fg_pct": 0.492,
    "fg3m": 4.8,
    "fg3a": 11.7,
    "fg3_pct": 0.408,
    "ftm": 1.6,
    "fta": 1.8,
    "ft_pct": 0.923,
}

AVERAGES_LEBRON = {"data": [AVG_LEBRON]}
AVERAGES_CURRY = {"data": [AVG_CURRY]}
AVERAGES_EMPTY = {"data": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client() -> AsyncClient:
    """Return an AsyncClient wired to the FastAPI test app."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ===========================================================================
# BallDontLieClient unit tests
# ===========================================================================


async def test_search_players_returns_model():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_LEBRON))
        async with BallDontLieClient(api_key="test") as client:
            result = await client.search_players("LeBron")

    assert len(result.data) == 1
    player = result.data[0]
    assert player.id == 237
    assert player.first_name == "LeBron"
    assert player.team is not None
    assert player.team.abbreviation == "LAL"


async def test_search_players_empty_results():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_EMPTY))
        async with BallDontLieClient(api_key="test") as client:
            result = await client.search_players("zzz_no_match")

    assert result.data == []


async def test_search_players_http_error_bubbles():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )
        async with BallDontLieClient(api_key="bad-key") as client:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await client.search_players("anyone")

    assert exc_info.value.response.status_code == 401


async def test_get_season_averages_returns_model():
    async with respx.mock:
        respx.get(f"{BASE}/season_averages").mock(return_value=Response(200, json=AVERAGES_LEBRON))
        async with BallDontLieClient(api_key="test") as client:
            result = await client.get_season_averages(player_id=237, season=2023)

    assert len(result.data) == 1
    avg = result.data[0]
    assert avg.player_id == 237
    assert avg.pts == pytest.approx(25.7)
    assert avg.season == 2023


async def test_get_season_averages_empty():
    async with respx.mock:
        respx.get(f"{BASE}/season_averages").mock(return_value=Response(200, json=AVERAGES_EMPTY))
        async with BallDontLieClient(api_key="test") as client:
            result = await client.get_season_averages(player_id=999, season=2000)

    assert result.data == []


async def test_retry_on_transport_error_then_success():
    """Client retries up to 3 times on TransportError and eventually succeeds."""
    call_count = 0

    async def flaky(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("simulated failure", request=request)
        return Response(200, json=SEARCH_LEBRON)

    async with respx.mock:
        respx.get(f"{BASE}/players").mock(side_effect=flaky)
        async with BallDontLieClient(api_key="test") as client:
            result = await client.search_players("LeBron")

    assert call_count == 3
    assert result.data[0].id == 237


async def test_retry_exhausted_raises_transport_error():
    """After 3 failed attempts, TransportError is re-raised."""

    async def always_fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("always fails", request=request)

    async with respx.mock:
        respx.get(f"{BASE}/players").mock(side_effect=always_fail)
        async with BallDontLieClient(api_key="test") as client:
            with pytest.raises(httpx.TransportError):
                await client.search_players("anyone")


async def test_client_requires_context_manager():
    client = BallDontLieClient(api_key="test")
    with pytest.raises(AssertionError, match="async with"):
        await client._get("/players")


# ===========================================================================
# /players/search endpoint tests
# ===========================================================================


async def test_endpoint_players_search_success():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_LEBRON))
        async with _client() as ac:
            r = await ac.get("/players/search", params={"name": "LeBron"})

    assert r.status_code == 200
    body = r.json()
    assert body["data"][0]["id"] == 237
    assert body["data"][0]["last_name"] == "James"


async def test_endpoint_players_search_empty():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_EMPTY))
        async with _client() as ac:
            r = await ac.get("/players/search", params={"name": "zzz"})

    assert r.status_code == 200
    assert r.json()["data"] == []


async def test_endpoint_players_search_missing_name_param():
    async with _client() as ac:
        r = await ac.get("/players/search")
    assert r.status_code == 422


async def test_endpoint_players_search_upstream_error():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(429, text="rate limited"))
        async with _client() as ac:
            r = await ac.get("/players/search", params={"name": "anyone"})

    assert r.status_code == 429


# ===========================================================================
# /players/{id}/season-averages endpoint tests
# ===========================================================================


async def test_endpoint_season_averages_success():
    async with respx.mock:
        respx.get(f"{BASE}/season_averages").mock(return_value=Response(200, json=AVERAGES_LEBRON))
        async with _client() as ac:
            r = await ac.get("/players/237/season-averages", params={"season": 2023})

    assert r.status_code == 200
    avg = r.json()["data"][0]
    assert avg["player_id"] == 237
    assert avg["pts"] == pytest.approx(25.7)


async def test_endpoint_season_averages_missing_season_param():
    async with _client() as ac:
        r = await ac.get("/players/237/season-averages")
    assert r.status_code == 422


async def test_endpoint_season_averages_invalid_player_id():
    async with _client() as ac:
        r = await ac.get("/players/not-a-number/season-averages", params={"season": 2023})
    assert r.status_code == 422


async def test_endpoint_season_averages_upstream_404():
    async with respx.mock:
        respx.get(f"{BASE}/season_averages").mock(return_value=Response(404, text="not found"))
        async with _client() as ac:
            r = await ac.get("/players/999/season-averages", params={"season": 2023})

    assert r.status_code == 404


# ===========================================================================
# /compare endpoint tests
# ===========================================================================


async def test_endpoint_compare_success():
    async with respx.mock:
        players_route = respx.get(f"{BASE}/players")
        players_route.side_effect = [
            Response(200, json=SEARCH_LEBRON),
            Response(200, json=SEARCH_CURRY),
        ]
        averages_route = respx.get(f"{BASE}/season_averages")
        averages_route.side_effect = [
            Response(200, json=AVERAGES_LEBRON),
            Response(200, json=AVERAGES_CURRY),
        ]
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "LeBron James", "player2": "Stephen Curry", "season": 2023},
            )

    assert r.status_code == 200
    body = r.json()
    assert body["player1"]["player_id"] == 237
    assert body["player2"]["player_id"] == 115
    assert body["player1"]["pts"] == pytest.approx(25.7)
    assert body["player2"]["pts"] == pytest.approx(26.4)


async def test_endpoint_compare_player1_not_found():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_EMPTY))
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "unknown", "player2": "LeBron", "season": 2023},
            )

    assert r.status_code == 404
    assert "unknown" in r.json()["detail"]


async def test_endpoint_compare_player2_not_found():
    async with respx.mock:
        players_route = respx.get(f"{BASE}/players")
        players_route.side_effect = [
            Response(200, json=SEARCH_LEBRON),
            Response(200, json=SEARCH_EMPTY),
        ]
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "LeBron", "player2": "unknown", "season": 2023},
            )

    assert r.status_code == 404
    assert "unknown" in r.json()["detail"]


async def test_endpoint_compare_no_averages_returns_none_fields():
    async with respx.mock:
        players_route = respx.get(f"{BASE}/players")
        players_route.side_effect = [
            Response(200, json=SEARCH_LEBRON),
            Response(200, json=SEARCH_CURRY),
        ]
        respx.get(f"{BASE}/season_averages").mock(return_value=Response(200, json=AVERAGES_EMPTY))
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "LeBron James", "player2": "Stephen Curry", "season": 1900},
            )

    assert r.status_code == 200
    body = r.json()
    assert body["player1"] is None
    assert body["player2"] is None


async def test_endpoint_compare_missing_params():
    async with _client() as ac:
        r = await ac.get("/compare", params={"player1": "LeBron"})
    assert r.status_code == 422


# ===========================================================================
# Error-branch coverage via dependency override (no retry delay)
# ===========================================================================


def _override(exc: Exception):
    """Return a get_bdl_client override whose methods all raise *exc*."""
    mock = AsyncMock(spec=BallDontLieClient)
    mock.search_players.side_effect = exc
    mock.get_season_averages.side_effect = exc

    async def _dep():
        yield mock

    return _dep


async def test_endpoint_players_search_503_on_transport_error():
    app.dependency_overrides[get_bdl_client] = _override(httpx.ConnectError("fail"))
    try:
        async with _client() as ac:
            r = await ac.get("/players/search", params={"name": "test"})
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_bdl_client, None)


async def test_endpoint_season_averages_503_on_transport_error():
    app.dependency_overrides[get_bdl_client] = _override(httpx.ConnectError("fail"))
    try:
        async with _client() as ac:
            r = await ac.get("/players/237/season-averages", params={"season": 2023})
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_bdl_client, None)


async def test_endpoint_compare_503_on_search_transport_error():
    app.dependency_overrides[get_bdl_client] = _override(httpx.ConnectError("fail"))
    try:
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "LeBron", "player2": "Curry", "season": 2023},
            )
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_bdl_client, None)


async def test_endpoint_compare_503_on_averages_transport_error():
    """TransportError raised only during get_season_averages (after search succeeds)."""
    from app.models import Player, PlayerSearchResponse

    mock = AsyncMock(spec=BallDontLieClient)
    mock.search_players.return_value = PlayerSearchResponse(
        data=[
            Player(id=237, first_name="LeBron", last_name="James"),
            Player(id=115, first_name="Stephen", last_name="Curry"),
        ]
    )
    mock.get_season_averages.side_effect = httpx.ConnectError("fail")

    async def _dep():
        yield mock

    app.dependency_overrides[get_bdl_client] = _dep
    try:
        async with _client() as ac:
            r = await ac.get(
                "/compare",
                params={"player1": "LeBron", "player2": "Curry", "season": 2023},
            )
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_bdl_client, None)


# ===========================================================================
# Legacy route coverage
# ===========================================================================


async def test_legacy_players_endpoint():
    async with respx.mock:
        respx.get(f"{BASE}/players").mock(return_value=Response(200, json=SEARCH_LEBRON))
        async with _client() as ac:
            r = await ac.get("/players/LeBron")

    assert r.status_code == 200
    assert r.json()["data"][0]["id"] == 237


async def test_legacy_teams_endpoint():
    teams_payload = {
        "data": [
            {
                "id": 14,
                "name": "Lakers",
                "full_name": "Los Angeles Lakers",
                "abbreviation": "LAL",
                "city": "Los Angeles",
                "conference": "West",
                "division": "Pacific",
            }
        ],
        "meta": {},
    }
    async with respx.mock:
        respx.get(f"{BASE}/teams").mock(return_value=Response(200, json=teams_payload))
        async with _client() as ac:
            r = await ac.get("/teams/Lakers")

    assert r.status_code == 200
    assert r.json()["data"][0]["abbreviation"] == "LAL"


# ===========================================================================
# /health
# ===========================================================================


async def test_health():
    async with _client() as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ===========================================================================
# Integration tests (skipped unless a real API key is configured)
# ===========================================================================

_REAL_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
_HAS_REAL_KEY = bool(_REAL_KEY) and _REAL_KEY != "test-api-key"


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_REAL_KEY, reason="No real BALLDONTLIE_API_KEY set")
async def test_integration_search_players():
    async with BallDontLieClient() as client:
        result = await client.search_players("LeBron")
    assert len(result.data) > 0
    assert any(p.first_name == "LeBron" for p in result.data)


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_REAL_KEY, reason="No real BALLDONTLIE_API_KEY set")
async def test_integration_season_averages():
    async with BallDontLieClient() as client:
        result = await client.get_season_averages(player_id=237, season=2023)
    # May be empty if season data is unavailable, but should not raise
    assert isinstance(result.data, list)


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_REAL_KEY, reason="No real BALLDONTLIE_API_KEY set")
async def test_integration_compare_endpoint():
    async with _client() as ac:
        r = await ac.get(
            "/compare",
            params={"player1": "LeBron James", "player2": "Stephen Curry", "season": 2023},
        )
    assert r.status_code == 200
    body = r.json()
    assert "player1" in body
    assert "player2" in body
