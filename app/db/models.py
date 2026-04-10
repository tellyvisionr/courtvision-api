"""SQLAlchemy ORM table definitions.

Schema mirrors the Pydantic response models in app/models.py so that data
fetched from the balldontlie API can be persisted as-is. The tables are also
suitable as a training dataset for ML workloads (each row is one
player-season or player-game observation).
"""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TeamRow(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie ID
    conference: Mapped[str | None] = mapped_column(String)
    division: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String)
    abbreviation: Mapped[str | None] = mapped_column(String(10))

    players: Mapped[list["PlayerRow"]] = relationship(back_populates="team")


class PlayerRow(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie ID
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    position: Mapped[str | None] = mapped_column(String(10))
    height: Mapped[str | None] = mapped_column(String(20))
    weight: Mapped[str | None] = mapped_column(String(20))
    jersey_number: Mapped[str | None] = mapped_column(String(10))
    college: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    draft_year: Mapped[int | None] = mapped_column(Integer)
    draft_round: Mapped[int | None] = mapped_column(Integer)
    draft_number: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))

    team: Mapped["TeamRow | None"] = relationship(back_populates="players")
    season_averages: Mapped[list["SeasonAverageRow"]] = relationship(back_populates="player")
    game_stats: Mapped[list["GameStatsRow"]] = relationship(back_populates="player")


class SeasonAverageRow(Base):
    """One row per player per season — natural key is (player_id, season).

    All counting/shooting stats are nullable because the API may not return
    every field for every player-season, and NULLs are cleaner than 0s when
    training an ML model.
    """

    __tablename__ = "season_averages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)

    games_played: Mapped[int | None] = mapped_column(Integer)
    pts: Mapped[float | None] = mapped_column(Float)
    ast: Mapped[float | None] = mapped_column(Float)
    reb: Mapped[float | None] = mapped_column(Float)
    stl: Mapped[float | None] = mapped_column(Float)
    blk: Mapped[float | None] = mapped_column(Float)
    turnover: Mapped[float | None] = mapped_column(Float)
    min: Mapped[str | None] = mapped_column(String(10))
    fgm: Mapped[float | None] = mapped_column(Float)
    fga: Mapped[float | None] = mapped_column(Float)
    fg_pct: Mapped[float | None] = mapped_column(Float)
    fg3m: Mapped[float | None] = mapped_column(Float)
    fg3a: Mapped[float | None] = mapped_column(Float)
    fg3_pct: Mapped[float | None] = mapped_column(Float)
    ftm: Mapped[float | None] = mapped_column(Float)
    fta: Mapped[float | None] = mapped_column(Float)
    ft_pct: Mapped[float | None] = mapped_column(Float)

    player: Mapped["PlayerRow"] = relationship(back_populates="season_averages")

    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_season_averages_player_season"),
    )


class GameRow(Base):
    """One row per NBA game."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie ID
    date: Mapped[str] = mapped_column(String)
    season: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str | None] = mapped_column(String(50))
    postseason: Mapped[bool | None] = mapped_column(Boolean)
    home_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    visitor_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))
    home_team_score: Mapped[int | None] = mapped_column(Integer)
    visitor_team_score: Mapped[int | None] = mapped_column(Integer)

    game_stats: Mapped[list["GameStatsRow"]] = relationship(back_populates="game")


class GameStatsRow(Base):
    """One row per player per game (box score line).

    Natural key is (player_id, game_id) — a player can only have one line
    per game.
    """

    __tablename__ = "game_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie stats ID
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"))

    min: Mapped[str | None] = mapped_column(String(10))
    pts: Mapped[int | None] = mapped_column(Integer)
    ast: Mapped[int | None] = mapped_column(Integer)
    reb: Mapped[int | None] = mapped_column(Integer)
    oreb: Mapped[int | None] = mapped_column(Integer)
    dreb: Mapped[int | None] = mapped_column(Integer)
    stl: Mapped[int | None] = mapped_column(Integer)
    blk: Mapped[int | None] = mapped_column(Integer)
    turnover: Mapped[int | None] = mapped_column(Integer)
    pf: Mapped[int | None] = mapped_column(Integer)
    plus_minus: Mapped[int | None] = mapped_column(Integer)
    fgm: Mapped[int | None] = mapped_column(Integer)
    fga: Mapped[int | None] = mapped_column(Integer)
    fg_pct: Mapped[float | None] = mapped_column(Float)
    fg3m: Mapped[int | None] = mapped_column(Integer)
    fg3a: Mapped[int | None] = mapped_column(Integer)
    fg3_pct: Mapped[float | None] = mapped_column(Float)
    ftm: Mapped[int | None] = mapped_column(Integer)
    fta: Mapped[int | None] = mapped_column(Integer)
    ft_pct: Mapped[float | None] = mapped_column(Float)

    player: Mapped["PlayerRow"] = relationship(back_populates="game_stats")
    game: Mapped["GameRow"] = relationship(back_populates="game_stats")

    __table_args__ = (UniqueConstraint("player_id", "game_id", name="uq_game_stats_player_game"),)
