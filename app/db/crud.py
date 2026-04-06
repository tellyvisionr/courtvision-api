"""Upsert helpers — idempotent writes from balldontlie API responses.

Each function accepts the corresponding Pydantic model and persists it to
the database without creating duplicates.  Callers are responsible for
committing the session.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlayerRow, SeasonAverageRow, TeamRow
from app.models import Player, SeasonAverage, Team


async def upsert_team(session: AsyncSession, team: Team) -> None:
    stmt = (
        insert(TeamRow)
        .values(
            id=team.id,
            conference=team.conference,
            division=team.division,
            city=team.city,
            name=team.name,
            full_name=team.full_name,
            abbreviation=team.abbreviation,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "conference": team.conference,
                "division": team.division,
                "city": team.city,
                "name": team.name,
                "full_name": team.full_name,
                "abbreviation": team.abbreviation,
            },
        )
    )
    await session.execute(stmt)


async def upsert_player(session: AsyncSession, player: Player) -> None:
    # Ensure the player's team exists before inserting the FK reference.
    if player.team is not None:
        await upsert_team(session, player.team)

    stmt = (
        insert(PlayerRow)
        .values(
            id=player.id,
            first_name=player.first_name,
            last_name=player.last_name,
            position=player.position,
            height=player.height,
            weight=player.weight,
            jersey_number=player.jersey_number,
            college=player.college,
            country=player.country,
            draft_year=player.draft_year,
            draft_round=player.draft_round,
            draft_number=player.draft_number,
            team_id=player.team.id if player.team else None,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "first_name": player.first_name,
                "last_name": player.last_name,
                "position": player.position,
                "height": player.height,
                "weight": player.weight,
                "jersey_number": player.jersey_number,
                "college": player.college,
                "country": player.country,
                "draft_year": player.draft_year,
                "draft_round": player.draft_round,
                "draft_number": player.draft_number,
                "team_id": player.team.id if player.team else None,
            },
        )
    )
    await session.execute(stmt)


async def upsert_season_average(session: AsyncSession, avg: SeasonAverage) -> None:
    stmt = (
        insert(SeasonAverageRow)
        .values(
            player_id=avg.player_id,
            season=avg.season,
            games_played=avg.games_played,
            pts=avg.pts,
            ast=avg.ast,
            reb=avg.reb,
            stl=avg.stl,
            blk=avg.blk,
            turnover=avg.turnover,
            min=avg.min,
            fgm=avg.fgm,
            fga=avg.fga,
            fg_pct=avg.fg_pct,
            fg3m=avg.fg3m,
            fg3a=avg.fg3a,
            fg3_pct=avg.fg3_pct,
            ftm=avg.ftm,
            fta=avg.fta,
            ft_pct=avg.ft_pct,
        )
        .on_conflict_do_update(
            constraint="uq_season_averages_player_season",
            set_={
                "games_played": avg.games_played,
                "pts": avg.pts,
                "ast": avg.ast,
                "reb": avg.reb,
                "stl": avg.stl,
                "blk": avg.blk,
                "turnover": avg.turnover,
                "min": avg.min,
                "fgm": avg.fgm,
                "fga": avg.fga,
                "fg_pct": avg.fg_pct,
                "fg3m": avg.fg3m,
                "fg3a": avg.fg3a,
                "fg3_pct": avg.fg3_pct,
                "ftm": avg.ftm,
                "fta": avg.fta,
                "ft_pct": avg.ft_pct,
            },
        )
    )
    await session.execute(stmt)


async def get_season_averages_for_player(
    session: AsyncSession, player_id: int
) -> list[SeasonAverageRow]:
    """Return all stored season rows for a player, ordered by season."""
    result = await session.execute(
        select(SeasonAverageRow)
        .where(SeasonAverageRow.player_id == player_id)
        .order_by(SeasonAverageRow.season)
    )
    return list(result.scalars().all())
