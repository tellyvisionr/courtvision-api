import os

# Must be set before app.main is imported so the startup check doesn't raise.
os.environ.setdefault("BALLDONTLIE_API_KEY", "test-api-key")
os.environ.setdefault("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")
