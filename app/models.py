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


class PlayerSearchResponse(BaseModel):
    data: list[Player]


class SeasonAveragesResponse(BaseModel):
    data: list[SeasonAverage]


class CompareResponse(BaseModel):
    player1: SeasonAverage | None = None
    player2: SeasonAverage | None = None


class ErrorResponse(BaseModel):
    detail: str
