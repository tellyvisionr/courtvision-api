# CourtVision API

A basketball statistics microservice wrapping the [balldontlie.io](https://www.balldontlie.io) API, built to demonstrate end-to-end DevOps and platform engineering practices.

Built with **FastAPI**, persisted in **PostgreSQL**, containerized with **Docker**, provisioned with **Terraform**, and deployed to **AWS ECS Fargate** via a **GitHub Actions CI/CD pipeline**.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy (async) |
| Infrastructure | Terraform, AWS ECS/Fargate, ALB, ECR, SSM |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Monitoring | AWS CloudWatch |

---

## API Endpoints

| Route | Method | Description |
|---|---|---|
| `/health` | GET | Service heartbeat |
| `/players/search?name=` | GET | Search players by name — results persisted to DB |
| `/players/{player_id}/season-averages?season=` | GET | Season averages for a player — results persisted to DB |
| `/compare?player1=&player2=&season=` | GET | Compare two players' season stats side by side |
| `/ingest/{season}` | POST | Bulk ingest all games and player stats for a season |

### Legacy routes (deprecated)

| Route | Description |
|---|---|
| `/players/{name}` | Original player search — use `/players/search?name=` instead |
| `/teams/{name}` | Original team lookup |

---

## Local Development

### Prerequisites
- Docker Desktop
- A [balldontlie.io](https://www.balldontlie.io) API key

### Setup

1. Copy the example env file and fill in your API key:
   ```bash
   cp .env_example .env
   # edit .env and set BALLDONTLIE_API_KEY
   ```

2. Start the API and database:
   ```bash
   docker compose up --build
   ```

3. The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Running tests

```bash
pip install -r requirements.txt
pytest --cov=app -v
```

---

## Architecture

```
GitHub push → CI (lint + test) → CD (build → ECR push → ECS deploy → smoke test)
                                          |
                                  AWS ECS Fargate
                                  FastAPI + PostgreSQL
                                          |
                                  Application Load Balancer
```

Infrastructure is provisioned via Terraform under `terraform/`. See `terraform/terraform.tfvars` for required input variables before applying.
