import os
import tempfile

# Isolate every test session on its own SQLite file, offline, without keys.
_tmp = tempfile.mkdtemp(prefix="sourcer-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["GITHUB_TOKEN"] = ""
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_API_KEY"] = ""
os.environ["FIXTURE_LATENCY_MS"] = "0"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
