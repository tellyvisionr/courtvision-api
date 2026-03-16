from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    conference: Optional[str] = None
    division: Optional[str] = None
    city: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    abbreviation: Optional[str] = None


class Player(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    jersey_number: Optional[str] = None
    college: Optional[str] = None
    country: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_number: Optional[int] = None
    team: Optional[Team] = None


class SeasonAverage(BaseModel):
    player_id: int
    season: int
    games_played: Optional[int] = None
    pts: Optional[float] = None
    ast: Optional[float] = None
    reb: Optional[float] = None
    stl: Optional[float] = None
    blk: Optional[float] = None
    turnover: Optional[float] = None
    min: Optional[str] = None
    fgm: Optional[float] = None
    fga: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3m: Optional[float] = None
    fg3a: Optional[float] = None
    fg3_pct: Optional[float] = None
    ftm: Optional[float] = None
    fta: Optional[float] = None
    ft_pct: Optional[float] = None


class PlayerSearchResponse(BaseModel):
    data: List[Player]


class SeasonAveragesResponse(BaseModel):
    data: List[SeasonAverage]


class CompareResponse(BaseModel):
    player1: Optional[SeasonAverage] = None
    player2: Optional[SeasonAverage] = None


class ErrorResponse(BaseModel):
    detail: str
