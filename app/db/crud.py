"""Upsert helpers — idempotent writes from balldontlie API responses.

Each function accepts the corresponding Pydantic model and persists it to
the database without creating duplicates. Callers are responsible for
committing the session.
"""

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import GameRow, GameStatsRow, PlayerRow, SeasonAverageRow, TeamRow
from app.models import Game, GameStats, Player, SeasonAverage, Team


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


async def upsert_game(session: AsyncSession, game: Game) -> None:
    await upsert_team(session, game.home_team)
    await upsert_team(session, game.visitor_team)

    stmt = (
        insert(GameRow)
        .values(
            id=game.id,
            date=game.date,
            season=game.season,
            status=game.status,
            postseason=game.postseason,
            home_team_id=game.home_team.id,
            visitor_team_id=game.visitor_team.id,
            home_team_score=game.home_team_score,
            visitor_team_score=game.visitor_team_score,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "status": game.status,
                "home_team_score": game.home_team_score,
                "visitor_team_score": game.visitor_team_score,
            },
        )
    )
    await session.execute(stmt)


async def upsert_game_stats(session: AsyncSession, stats: GameStats) -> None:
    await upsert_player(session, stats.player)
    await upsert_team(session, stats.team)
    await upsert_game(session, stats.game)

    stmt = (
        insert(GameStatsRow)
        .values(
            id=stats.id,
            player_id=stats.player.id,
            game_id=stats.game.id,
            team_id=stats.team.id,
            min=stats.min,
            pts=stats.pts,
            ast=stats.ast,
            reb=stats.reb,
            oreb=stats.oreb,
            dreb=stats.dreb,
            stl=stats.stl,
            blk=stats.blk,
            turnover=stats.turnover,
            pf=stats.pf,
            plus_minus=stats.plus_minus,
            fgm=stats.fgm,
            fga=stats.fga,
            fg_pct=stats.fg_pct,
            fg3m=stats.fg3m,
            fg3a=stats.fg3a,
            fg3_pct=stats.fg3_pct,
            ftm=stats.ftm,
            fta=stats.fta,
            ft_pct=stats.ft_pct,
        )
        .on_conflict_do_update(
            constraint="uq_game_stats_player_game",
            set_={
                "min": stats.min,
                "pts": stats.pts,
                "ast": stats.ast,
                "reb": stats.reb,
                "oreb": stats.oreb,
                "dreb": stats.dreb,
                "stl": stats.stl,
                "blk": stats.blk,
                "turnover": stats.turnover,
                "pf": stats.pf,
                "plus_minus": stats.plus_minus,
                "fgm": stats.fgm,
                "fga": stats.fga,
                "fg_pct": stats.fg_pct,
                "fg3m": stats.fg3m,
                "fg3a": stats.fg3a,
                "fg3_pct": stats.fg3_pct,
                "ftm": stats.ftm,
                "fta": stats.fta,
                "ft_pct": stats.ft_pct,
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


async def get_player_game_stats(
    session: AsyncSession,
    player_id: int,
) -> list[GameStatsRow]:
    """Return all game stats for a player ordered by game date.

    Eagerly loads the game relationship so callers can access
    game.home_team_id and game.visitor_team_id without extra queries.
    """
    result = await session.execute(
        select(GameStatsRow)
        .where(GameStatsRow.player_id == player_id)
        .join(GameRow, GameStatsRow.game_id == GameRow.id)
        .order_by(GameRow.date)
        .options(selectinload(GameStatsRow.game))
    )
    return list(result.scalars().all())


async def get_team_games(
    session: AsyncSession,
    team_id: int,
) -> list[GameRow]:
    """Return all games involving a team (home or away), ordered by date."""
    result = await session.execute(
        select(GameRow)
        .where(or_(GameRow.home_team_id == team_id, GameRow.visitor_team_id == team_id))
        .order_by(GameRow.date)
    )
    return list(result.scalars().all())


async def get_head_to_head_games(
    session: AsyncSession,
    team_a_id: int,
    team_b_id: int,
) -> list[GameRow]:
    """Return all games between two specific teams, ordered by date."""
    result = await session.execute(
        select(GameRow)
        .where(
            or_(
                (GameRow.home_team_id == team_a_id) & (GameRow.visitor_team_id == team_b_id),
                (GameRow.home_team_id == team_b_id) & (GameRow.visitor_team_id == team_a_id),
            )
        )
        .order_by(GameRow.date)
    )
    return list(result.scalars().all())
