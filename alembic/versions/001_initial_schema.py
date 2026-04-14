"""Initial schema — teams, players, games, season_averages, game_stats.

Revision ID: 001
Revises:
Create Date: 2026-04-13
"""

import sqlalchemy as sa

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conference", sa.String, nullable=True),
        sa.Column("division", sa.String, nullable=True),
        sa.Column("city", sa.String, nullable=True),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("full_name", sa.String, nullable=True),
        sa.Column("abbreviation", sa.String(10), nullable=True),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("first_name", sa.String, nullable=False),
        sa.Column("last_name", sa.String, nullable=False),
        sa.Column("position", sa.String(10), nullable=True),
        sa.Column("height", sa.String(20), nullable=True),
        sa.Column("weight", sa.String(20), nullable=True),
        sa.Column("jersey_number", sa.String(10), nullable=True),
        sa.Column("college", sa.String, nullable=True),
        sa.Column("country", sa.String, nullable=True),
        sa.Column("draft_year", sa.Integer, nullable=True),
        sa.Column("draft_round", sa.Integer, nullable=True),
        sa.Column("draft_number", sa.Integer, nullable=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.String, nullable=False),
        sa.Column("season", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("postseason", sa.Boolean, nullable=True),
        sa.Column("home_team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("visitor_team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("home_team_score", sa.Integer, nullable=True),
        sa.Column("visitor_team_score", sa.Integer, nullable=True),
    )

    op.create_table(
        "season_averages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False, index=True),
        sa.Column("season", sa.Integer, nullable=False, index=True),
        sa.Column("games_played", sa.Integer, nullable=True),
        sa.Column("pts", sa.Float, nullable=True),
        sa.Column("ast", sa.Float, nullable=True),
        sa.Column("reb", sa.Float, nullable=True),
        sa.Column("stl", sa.Float, nullable=True),
        sa.Column("blk", sa.Float, nullable=True),
        sa.Column("turnover", sa.Float, nullable=True),
        sa.Column("min", sa.String(10), nullable=True),
        sa.Column("fgm", sa.Float, nullable=True),
        sa.Column("fga", sa.Float, nullable=True),
        sa.Column("fg_pct", sa.Float, nullable=True),
        sa.Column("fg3m", sa.Float, nullable=True),
        sa.Column("fg3a", sa.Float, nullable=True),
        sa.Column("fg3_pct", sa.Float, nullable=True),
        sa.Column("ftm", sa.Float, nullable=True),
        sa.Column("fta", sa.Float, nullable=True),
        sa.Column("ft_pct", sa.Float, nullable=True),
        sa.UniqueConstraint("player_id", "season", name="uq_season_averages_player_season"),
    )

    op.create_table(
        "game_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False, index=True),
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False, index=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("min", sa.String(10), nullable=True),
        sa.Column("pts", sa.Integer, nullable=True),
        sa.Column("ast", sa.Integer, nullable=True),
        sa.Column("reb", sa.Integer, nullable=True),
        sa.Column("oreb", sa.Integer, nullable=True),
        sa.Column("dreb", sa.Integer, nullable=True),
        sa.Column("stl", sa.Integer, nullable=True),
        sa.Column("blk", sa.Integer, nullable=True),
        sa.Column("turnover", sa.Integer, nullable=True),
        sa.Column("pf", sa.Integer, nullable=True),
        sa.Column("plus_minus", sa.Integer, nullable=True),
        sa.Column("fgm", sa.Integer, nullable=True),
        sa.Column("fga", sa.Integer, nullable=True),
        sa.Column("fg_pct", sa.Float, nullable=True),
        sa.Column("fg3m", sa.Integer, nullable=True),
        sa.Column("fg3a", sa.Integer, nullable=True),
        sa.Column("fg3_pct", sa.Float, nullable=True),
        sa.Column("ftm", sa.Integer, nullable=True),
        sa.Column("fta", sa.Integer, nullable=True),
        sa.Column("ft_pct", sa.Float, nullable=True),
        sa.UniqueConstraint("player_id", "game_id", name="uq_game_stats_player_game"),
    )


def downgrade() -> None:
    op.drop_table("game_stats")
    op.drop_table("season_averages")
    op.drop_table("games")
    op.drop_table("players")
    op.drop_table("teams")
