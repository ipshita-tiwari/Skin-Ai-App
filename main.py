"""Root ASGI entry so `uvicorn main:app` and `uvicorn backend.main:app` both work."""
from backend.main import app

__all__ = ["app"]
