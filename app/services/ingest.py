"""Data ingestion service.

Pulls data from the balldontlie API and upserts it into the database.
Designed to be called manually (via the /ingest endpoint) to populate the
dataset that will be used for ML model training.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.balldontlie import BallDontLieClient
from app.db import crud
from app.models import Game, GameStats, Team

# Pause between paginated requests to stay within API rate limits.
_RATE_LIMIT_SLEEP = 0.5


async def ingest_teams(client: BallDontLieClient, session: AsyncSession) -> int:
    """Fetch and upsert all 30 NBA teams. Returns count of teams stored."""
    raw_teams = await client.get_all_teams()
    for raw in raw_teams:
        team = Team(**raw)
        await crud.upsert_team(session, team)
    await session.commit()
    return len(raw_teams)


async def ingest_games(
    client: BallDontLieClient,
    session: AsyncSession,
    season: int,
) -> int:
    """Paginate through all games for a season and upsert each one.

    Commits in batches of 50 games. Returns total count of games stored.
    """
    cursor: int | None = None
    total = 0
    batch: list[Game] = []

    while True:
        response = await client.get_games(season=season, cursor=cursor)
        for raw in response["data"]:
            game = Game(**raw)
            batch.append(game)

        if len(batch) >= 50:
            for game in batch:
                await crud.upsert_game(session, game)
            await session.commit()
            total += len(batch)
            batch = []

        next_cursor = response.get("meta", {}).get("next_cursor")
        if next_cursor is None:
            break
        cursor = next_cursor
        await asyncio.sleep(_RATE_LIMIT_SLEEP)

    # Flush remaining games that didn't fill a full batch.
    if batch:
        for game in batch:
            await crud.upsert_game(session, game)
        await session.commit()
        total += len(batch)

    return total


async def ingest_game_stats(
    client: BallDontLieClient,
    session: AsyncSession,
    game_id: int,
) -> int:
    """Fetch all player box score lines for a game and upsert each one.

    Returns total count of stat rows stored.
    """
    cursor: int | None = None
    total = 0

    while True:
        response = await client.get_game_stats(game_id=game_id, cursor=cursor)
        for raw in response["data"]:
            stats = GameStats(**raw)
            await crud.upsert_game_stats(session, stats)
            total += 1
        await session.commit()

        next_cursor = response.get("meta", {}).get("next_cursor")
        if next_cursor is None:
            break
        cursor = next_cursor
        await asyncio.sleep(_RATE_LIMIT_SLEEP)

    return total


async def ingest_season(
    client: BallDontLieClient,
    session: AsyncSession,
    season: int,
) -> dict:
    """Full ingestion pipeline: teams → games → box scores for every game.

    Returns a summary dict with row counts for each entity type.
    This is intentionally blocking — call it from a background task or
    a one-off admin endpoint, not from a latency-sensitive user request.
    """
    team_count = await ingest_teams(client, session)

    game_count = await ingest_games(client, session, season)

    # Fetch all game IDs we just stored so we can pull stats for each.
    from sqlalchemy import select

    from app.db.models import GameRow

    result = await session.execute(select(GameRow.id).where(GameRow.season == season))
    game_ids = list(result.scalars().all())

    stats_count = 0
    for game_id in game_ids:
        stats_count += await ingest_game_stats(client, session, game_id)
        await asyncio.sleep(_RATE_LIMIT_SLEEP)

    return {
        "season": season,
        "teams": team_count,
        "games": game_count,
        "game_stats": stats_count,
    }
