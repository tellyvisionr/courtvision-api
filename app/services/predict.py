"""ML prediction service.

Trains simple scikit-learn models on historical game data stored in the
database and returns predictions. Models are intentionally lightweight —
the goal is to demonstrate an end-to-end ML pipeline (ingest → store →
feature engineering → fit → serve), not production-grade forecasting.
"""

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud

_MIN_PLAYER_GAMES = 10
_MIN_TEAM_GAMES = 20


async def predict_player_game(
    session: AsyncSession,
    player_id: int,
    opponent_team_id: int,
) -> dict:
    """Predict pts/ast/reb for a player in a game against a specific opponent.

    Uses LinearRegression trained on the player's full game log history.
    Features: home/away context, opponent match flag, chronological index.
    """
    all_stats = await crud.get_player_game_stats(session, player_id)

    # Exclude DNPs (no box score recorded).
    valid_stats = [s for s in all_stats if s.pts is not None]

    if len(valid_stats) < _MIN_PLAYER_GAMES:
        return {
            "error": "Insufficient data",
            "games_found": len(valid_stats),
            "minimum_required": _MIN_PLAYER_GAMES,
        }

    X_rows, y_pts, y_ast, y_reb = [], [], [], []

    for i, stat in enumerate(valid_stats):
        is_home = 1 if stat.team_id == stat.game.home_team_id else 0
        opponent = stat.game.visitor_team_id if is_home else stat.game.home_team_id
        is_vs_opponent = 1 if opponent == opponent_team_id else 0
        X_rows.append([is_home, is_vs_opponent, i])
        y_pts.append(stat.pts)
        y_ast.append(stat.ast if stat.ast is not None else 0)
        y_reb.append(stat.reb if stat.reb is not None else 0)

    X = np.array(X_rows, dtype=float)
    y_pts_arr = np.array(y_pts, dtype=float)
    y_ast_arr = np.array(y_ast, dtype=float)
    y_reb_arr = np.array(y_reb, dtype=float)

    model_pts = LinearRegression().fit(X, y_pts_arr)
    model_ast = LinearRegression().fit(X, y_ast_arr)
    model_reb = LinearRegression().fit(X, y_reb_arr)

    # Predict the next game: assume home, vs the specified opponent.
    X_pred = np.array([[1, 1, len(valid_stats)]], dtype=float)

    pred_pts = max(0.0, float(model_pts.predict(X_pred)[0]))
    pred_ast = max(0.0, float(model_ast.predict(X_pred)[0]))
    pred_reb = max(0.0, float(model_reb.predict(X_pred)[0]))

    return {
        "player_id": player_id,
        "opponent_team_id": opponent_team_id,
        "predicted_pts": round(pred_pts, 1),
        "predicted_ast": round(pred_ast, 1),
        "predicted_reb": round(pred_reb, 1),
        "sample_size": len(valid_stats),
        "r2_pts": round(float(model_pts.score(X, y_pts_arr)), 3),
        "r2_ast": round(float(model_ast.score(X, y_ast_arr)), 3),
        "r2_reb": round(float(model_reb.score(X, y_reb_arr)), 3),
        "model": "LinearRegression",
        "features": ["is_home", "is_vs_opponent", "game_index"],
    }


async def predict_game_outcome(
    session: AsyncSession,
    home_team_id: int,
    away_team_id: int,
) -> dict:
    """Predict win probability for a home team vs away team matchup.

    Uses LogisticRegression trained on historical game results for both teams.
    """
    home_games = await crud.get_team_games(session, home_team_id)
    away_games = await crud.get_team_games(session, away_team_id)
    h2h_games = await crud.get_head_to_head_games(session, home_team_id, away_team_id)

    total_games = len(home_games) + len(away_games)
    if total_games < _MIN_TEAM_GAMES:
        return {
            "error": "Insufficient data",
            "games_found": total_games,
            "minimum_required": _MIN_TEAM_GAMES,
        }

    # Deduplicate — h2h games appear in both team lists.
    seen: set[int] = set()
    all_games = []
    for game in home_games + away_games:
        if game.id not in seen:
            seen.add(game.id)
            all_games.append(game)

    # Avg points scored per team across all their games.
    def _pts_scored(games: list, team_id: int) -> float:
        scored = [
            (g.home_team_score if g.home_team_id == team_id else g.visitor_team_score)
            for g in games
            if g.home_team_score is not None and g.visitor_team_score is not None
        ]
        return float(np.mean(scored)) if scored else 0.0

    home_avg_pts = _pts_scored(home_games, home_team_id)
    away_avg_pts = _pts_scored(away_games, away_team_id)

    # Head-to-head record.
    h2h_home_wins, h2h_away_wins = 0, 0
    for g in h2h_games:
        if g.home_team_score is None or g.visitor_team_score is None:
            continue
        home_won = g.home_team_score > g.visitor_team_score
        if g.home_team_id == home_team_id:
            h2h_home_wins += 1 if home_won else 0
            h2h_away_wins += 0 if home_won else 1
        else:
            h2h_home_wins += 0 if home_won else 1
            h2h_away_wins += 1 if home_won else 0

    # Build feature matrix across all games involving either team.
    X_rows, targets, score_diffs = [], [], []
    for game in all_games:
        if game.home_team_score is None or game.visitor_team_score is None:
            continue
        is_home_team_home = 1 if game.home_team_id == home_team_id else 0
        is_matchup = (
            1
            if (
                (game.home_team_id == home_team_id and game.visitor_team_id == away_team_id)
                or (game.home_team_id == away_team_id and game.visitor_team_id == home_team_id)
            )
            else 0
        )
        diff = game.home_team_score - game.visitor_team_score
        score_diffs.append(diff)
        # Target: did home_team_id win this particular game?
        if is_home_team_home:
            won = 1 if game.home_team_score > game.visitor_team_score else 0
        else:
            won = 1 if game.visitor_team_score > game.home_team_score else 0
        X_rows.append([is_home_team_home, is_matchup, diff])
        targets.append(won)

    # Fallback when all outcomes are identical (model can't fit).
    if len(set(targets)) < 2:
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_win_probability": round(float(np.mean(targets)), 3),
            "home_team_avg_pts": round(home_avg_pts, 1),
            "away_team_avg_pts": round(away_avg_pts, 1),
            "head_to_head": {"home_wins": h2h_home_wins, "away_wins": h2h_away_wins},
            "sample_size": len(X_rows),
            "model": "LogisticRegression",
        }

    X = np.array(X_rows, dtype=float)
    y = np.array(targets, dtype=int)
    mean_diff = float(np.mean(score_diffs)) if score_diffs else 0.0

    model = LogisticRegression(max_iter=200).fit(X, y)
    proba = float(model.predict_proba(np.array([[1, 1, mean_diff]]))[0][1])

    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_win_probability": round(proba, 3),
        "home_team_avg_pts": round(home_avg_pts, 1),
        "away_team_avg_pts": round(away_avg_pts, 1),
        "head_to_head": {"home_wins": h2h_home_wins, "away_wins": h2h_away_wins},
        "sample_size": len(X_rows),
        "model": "LogisticRegression",
    }
