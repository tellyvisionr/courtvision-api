"""Tests for the ML prediction service and /predict endpoints.

All database calls are mocked — no running Postgres required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app, get_session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stat(
    game_id: int,
    player_team_id: int,
    home_team_id: int,
    visitor_team_id: int,
    pts: int | None,
    ast: int | None = 5,
    reb: int | None = 5,
    date: str = "2024-01-01",
) -> MagicMock:
    row = MagicMock()
    row.pts = pts
    row.ast = ast
    row.reb = reb
    row.team_id = player_team_id
    row.game = MagicMock()
    row.game.id = game_id
    row.game.date = date
    row.game.home_team_id = home_team_id
    row.game.visitor_team_id = visitor_team_id
    return row


def _make_game(
    game_id: int,
    home_id: int,
    visitor_id: int,
    home_score: int | None,
    visitor_score: int | None,
    date: str = "2024-01-01",
) -> MagicMock:
    row = MagicMock()
    row.id = game_id
    row.home_team_id = home_id
    row.visitor_team_id = visitor_id
    row.home_team_score = home_score
    row.visitor_team_score = visitor_score
    row.date = date
    return row


def _player_stats(n: int, pts_base: int = 25) -> list[MagicMock]:
    """Build n valid game stat rows with alternating home/away and varied scores."""
    rows = []
    for i in range(n):
        home_id = 14 if i % 2 == 0 else 10
        visitor_id = 10 if i % 2 == 0 else 14
        rows.append(
            _make_stat(
                game_id=1000 + i,
                player_team_id=14,
                home_team_id=home_id,
                visitor_team_id=visitor_id,
                pts=pts_base + (i % 10),
                ast=5 + (i % 4),
                reb=6 + (i % 3),
                date=f"2024-01-{i + 1:02d}",
            )
        )
    return rows


def _team_games(team_id: int, n: int, opponent_id: int = 99) -> list[MagicMock]:
    """Build n game rows for a team with alternating wins and losses."""
    games = []
    for i in range(n):
        home_score = 110 + (i % 10)
        visitor_score = 105 + ((i + 1) % 10)
        if i % 2 == 0:
            games.append(_make_game(2000 + i, team_id, opponent_id, home_score, visitor_score))
        else:
            games.append(_make_game(2000 + i, opponent_id, team_id, visitor_score, home_score))
    return games


# ---------------------------------------------------------------------------
# predict_player_game unit tests
# ---------------------------------------------------------------------------


async def test_predict_player_game_success():
    stats = _player_stats(15)
    session = AsyncMock()

    with patch("app.services.predict.crud.get_player_game_stats", new_callable=AsyncMock) as mock:
        mock.return_value = stats
        from app.services.predict import predict_player_game

        result = await predict_player_game(session, player_id=237, opponent_team_id=10)

    assert "error" not in result
    assert result["player_id"] == 237
    assert result["opponent_team_id"] == 10
    assert result["predicted_pts"] >= 0
    assert result["predicted_ast"] >= 0
    assert result["predicted_reb"] >= 0
    assert result["sample_size"] == 15
    assert result["model"] == "LinearRegression"
    assert result["features"] == ["is_home", "is_vs_opponent", "game_index"]
    assert "r2_pts" in result


async def test_predict_player_game_insufficient_data():
    stats = _player_stats(5)
    session = AsyncMock()

    with patch("app.services.predict.crud.get_player_game_stats", new_callable=AsyncMock) as mock:
        mock.return_value = stats
        from app.services.predict import predict_player_game

        result = await predict_player_game(session, player_id=237, opponent_team_id=10)

    assert "error" in result
    assert result["games_found"] == 5
    assert result["minimum_required"] == 10


async def test_predict_player_game_filters_dnp():
    """15 rows but 10 are DNPs (pts=None) — only 5 valid, should return error."""
    stats = _player_stats(5) + [_make_stat(3000 + i, 14, 14, 10, pts=None) for i in range(10)]
    session = AsyncMock()

    with patch("app.services.predict.crud.get_player_game_stats", new_callable=AsyncMock) as mock:
        mock.return_value = stats
        from app.services.predict import predict_player_game

        result = await predict_player_game(session, player_id=237, opponent_team_id=10)

    assert "error" in result
    assert result["games_found"] == 5


# ---------------------------------------------------------------------------
# predict_game_outcome unit tests
# ---------------------------------------------------------------------------


async def test_predict_game_outcome_success():
    home_games = _team_games(team_id=14, n=15, opponent_id=99)
    away_games = _team_games(team_id=10, n=15, opponent_id=99)
    h2h_games = [
        _make_game(9001, 14, 10, 112, 105),
        _make_game(9002, 10, 14, 108, 115),
    ]
    session = AsyncMock()

    with (
        patch("app.services.predict.crud.get_team_games", new_callable=AsyncMock) as mock_tg,
        patch(
            "app.services.predict.crud.get_head_to_head_games", new_callable=AsyncMock
        ) as mock_h2h,
    ):
        mock_tg.side_effect = [home_games, away_games]
        mock_h2h.return_value = h2h_games
        from app.services.predict import predict_game_outcome

        result = await predict_game_outcome(session, home_team_id=14, away_team_id=10)

    assert "error" not in result
    assert 0.0 <= result["home_win_probability"] <= 1.0
    assert result["home_team_avg_pts"] > 0
    assert result["away_team_avg_pts"] > 0
    assert "home_wins" in result["head_to_head"]
    assert result["model"] == "LogisticRegression"
    assert result["sample_size"] > 0


async def test_predict_game_outcome_insufficient_data():
    session = AsyncMock()

    with (
        patch("app.services.predict.crud.get_team_games", new_callable=AsyncMock) as mock_tg,
        patch(
            "app.services.predict.crud.get_head_to_head_games", new_callable=AsyncMock
        ) as mock_h2h,
    ):
        mock_tg.side_effect = [_team_games(14, 5), _team_games(10, 5)]
        mock_h2h.return_value = []
        from app.services.predict import predict_game_outcome

        result = await predict_game_outcome(session, home_team_id=14, away_team_id=10)

    assert "error" in result
    assert result["games_found"] == 10


# ---------------------------------------------------------------------------
# /predict/player endpoint tests
# ---------------------------------------------------------------------------


async def test_predict_player_endpoint_success():
    canned = {
        "player_id": 237,
        "opponent_team_id": 10,
        "predicted_pts": 26.3,
        "predicted_ast": 7.1,
        "predicted_reb": 7.4,
        "sample_size": 50,
        "r2_pts": 0.12,
        "r2_ast": 0.08,
        "r2_reb": 0.05,
        "model": "LinearRegression",
        "features": ["is_home", "is_vs_opponent", "game_index"],
    }

    async def _mock_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = _mock_session

    with patch("app.main.predict.predict_player_game", new_callable=AsyncMock) as mock_pred:
        mock_pred.return_value = canned
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/predict/player", params={"player_id": 237, "opponent_team_id": 10})

    app.dependency_overrides.pop(get_session, None)

    assert r.status_code == 200
    assert r.json()["predicted_pts"] == 26.3


async def test_predict_player_endpoint_400_on_insufficient_data():
    async def _mock_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = _mock_session

    with patch("app.main.predict.predict_player_game", new_callable=AsyncMock) as mock_pred:
        mock_pred.return_value = {
            "error": "Insufficient data",
            "games_found": 3,
            "minimum_required": 10,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/predict/player", params={"player_id": 237, "opponent_team_id": 10})

    app.dependency_overrides.pop(get_session, None)

    assert r.status_code == 400


# ---------------------------------------------------------------------------
# /predict/game endpoint tests
# ---------------------------------------------------------------------------


async def test_predict_game_endpoint_success():
    canned = {
        "home_team_id": 14,
        "away_team_id": 10,
        "home_win_probability": 0.612,
        "home_team_avg_pts": 112.3,
        "away_team_avg_pts": 108.7,
        "head_to_head": {"home_wins": 3, "away_wins": 2},
        "sample_size": 30,
        "model": "LogisticRegression",
    }

    async def _mock_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = _mock_session

    with patch("app.main.predict.predict_game_outcome", new_callable=AsyncMock) as mock_pred:
        mock_pred.return_value = canned
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/predict/game", params={"home_team_id": 14, "away_team_id": 10})

    app.dependency_overrides.pop(get_session, None)

    assert r.status_code == 200
    assert r.json()["home_win_probability"] == 0.612


async def test_predict_game_endpoint_400_on_insufficient_data():
    async def _mock_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = _mock_session

    with patch("app.main.predict.predict_game_outcome", new_callable=AsyncMock) as mock_pred:
        mock_pred.return_value = {
            "error": "Insufficient data",
            "games_found": 8,
            "minimum_required": 20,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/predict/game", params={"home_team_id": 14, "away_team_id": 10})

    app.dependency_overrides.pop(get_session, None)

    assert r.status_code == 400
