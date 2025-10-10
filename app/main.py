from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(title="CourtVision API", version="0.1.1")
BASE_URL = "https://www.balldontlie.io/api/v1"
TIMEOUT = 10  # seconds

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/player/{name}")
def player_stats(name: str, season: int = 2024):
    try:
        # 1) find player (limit to best match)
        r = requests.get(
            f"{BASE_URL}/players",
            params={"search": name, "per_page": 1},
            timeout=TIMEOUT
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Upstream players error: {r.status_code}")
        body = r.json()
        data = body.get("data") or []
        if not data:
            raise HTTPException(status_code=404, detail="Player not found")

        player = data[0]
        player_id = player["id"]

        # 2) season averages
        s = requests.get(
            f"{BASE_URL}/season_averages",
            params={"season": season, "player_ids[]": player_id},
            timeout=TIMEOUT
        )
        if s.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Upstream averages error: {s.status_code}")

        averages = (s.json() or {}).get("data") or []
        if not averages:
            # try helpful message before giving up
            raise HTTPException(
                status_code=404,
                detail=f"No season averages for {player['first_name']} {player['last_name']} in {season}. "
                       f"Try a different season (e.g., ?season=2023)."
            )

        avg = averages[0]
        return {
            "id": player_id,
            "name": f"{player['first_name']} {player['last_name']}",
            "team": (player.get("team") or {}).get("full_name"),
            "season": season,
            "ppg": round(avg.get("pts", 0.0), 2),
            "apg": round(avg.get("ast", 0.0), 2),
            "rpg": round(avg.get("reb", 0.0), 2),
            "spg": round(avg.get("stl", 0.0), 2),
            "bpg": round(avg.get("blk", 0.0), 2),
            "fg_pct": round(avg.get("fg_pct", 0.0), 3),
            "fg3_pct": round(avg.get("fg3_pct", 0.0), 3),
            "ft_pct": round(avg.get("ft_pct", 0.0), 3),
        }
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except requests.exceptions.RequestException as e:
        # DNS, connection reset, etc.
        raise HTTPException(status_code=502, detail=f"Upstream request error: {str(e)}")
    except ValueError:
        # JSON decode errors
        raise HTTPException(status_code=502, detail="Invalid JSON from upstream")
