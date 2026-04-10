from __future__ import annotations

import os

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models import PlayerSearchResponse, SeasonAveragesResponse

TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


class BallDontLieClient:
    """Async HTTP client for the balldontlie.io v1 API with retries and timeouts."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        # Explicit conditional instead of `or` so mypy can narrow str | None → str.
        resolved_url = (
            base_url
            if base_url is not None
            else os.getenv("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")
        )
        self.base_url = resolved_url.rstrip("/")
        self.api_key = api_key or os.getenv("BALLDONTLIE_API_KEY", "")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BallDontLieClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=TIMEOUT,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
        reraise=True,
    )
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        assert self._client is not None, "Client not started — use `async with BallDontLieClient()`"
        resp = await self._client.get(endpoint, params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_players(self, name: str) -> PlayerSearchResponse:
        """Search players by name."""
        data = await self._get("/players", {"search": name})
        return PlayerSearchResponse(**data)

    async def get_season_averages(self, player_id: int, season: int) -> SeasonAveragesResponse:
        """Fetch season averages for a single player."""
        data = await self._get(
            "/season_averages",
            {"season": season, "player_ids[]": player_id},
        )
        return SeasonAveragesResponse(**data)

    async def get_all_teams(self) -> list[dict]:
        """Fetch all 30 NBA teams (single page, no pagination)."""
        data = await self._get("/teams")
        return data["data"]

    async def get_games(
        self,
        season: int,
        cursor: int | None = None,
        per_page: int = 100,
    ) -> dict:
        """Fetch games for a season with cursor-based pagination.

        Returns the raw API response dict containing 'data' and 'meta'
        so callers can follow the cursor themselves.
        """
        params: dict = {"seasons[]": season, "per_page": per_page}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._get("/games", params)

    async def get_game_stats(
        self,
        game_id: int,
        cursor: int | None = None,
        per_page: int = 100,
    ) -> dict:
        """Fetch player box score stats for a specific game.

        Returns the raw API response dict containing 'data' and 'meta'.
        """
        params: dict = {"game_ids[]": game_id, "per_page": per_page}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._get("/stats", params)
