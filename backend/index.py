# Vercel entrypoint: exposes the FastAPI ASGI app.
from app.main import app  # noqa: F401
