from __future__ import annotations

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    conference: str | None = None
    division: str | None = None
    city: str | None = None
    name: str | None = None
    full_name: str | None = None
    abbreviation: str | None = None


class Player(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str | None = None
    height: str | None = None
    weight: str | None = None
    jersey_number: str | None = None
    college: str | None = None
    country: str | None = None
    draft_year: int | None = None
    draft_round: int | None = None
    draft_number: int | None = None
    team: Team | None = None


class SeasonAverage(BaseModel):
    player_id: int
    season: int
    games_played: int | None = None
    pts: float | None = None
    ast: float | None = None
    reb: float | None = None
    stl: float | None = None
    blk: float | None = None
    turnover: float | None = None
    min: str | None = None
    fgm: float | None = None
    fga: float | None = None
    fg_pct: float | None = None
    fg3m: float | None = None
    fg3a: float | None = None
    fg3_pct: float | None = None
    ftm: float | None = None
    fta: float | None = None
    ft_pct: float | None = None


class Game(BaseModel):
    id: int
    date: str
    season: int
    status: str | None = None
    postseason: bool | None = None
    home_team_score: int | None = None
    visitor_team_score: int | None = None
    home_team: Team
    visitor_team: Team


class GameStats(BaseModel):
    """Single player's box score for one game."""

    id: int
    player: Player
    team: Team
    game: Game
    min: str | None = None
    pts: int | None = None
    ast: int | None = None
    reb: int | None = None
    oreb: int | None = None
    dreb: int | None = None
    stl: int | None = None
    blk: int | None = None
    turnover: int | None = None
    pf: int | None = None
    plus_minus: int | None = None
    fgm: int | None = None
    fga: int | None = None
    fg_pct: float | None = None
    fg3m: int | None = None
    fg3a: int | None = None
    fg3_pct: float | None = None
    ftm: int | None = None
    fta: int | None = None
    ft_pct: float | None = None


class PlayerSearchResponse(BaseModel):
    data: list[Player]


class SeasonAveragesResponse(BaseModel):
    data: list[SeasonAverage]


class CompareResponse(BaseModel):
    player1: SeasonAverage | None = None
    player2: SeasonAverage | None = None


class ErrorResponse(BaseModel):
    detail: str
