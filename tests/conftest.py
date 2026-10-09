import json
import os
from pathlib import Path

import httpx
import pytest

from core.client import WiseClient
from core.config import Settings

# Synthetic test key only; set before importing the configured ASGI entry point.
os.environ["WISE_MCP_SIGNING_SECRET"] = "ab" * 32

from server import create_app

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "docs/endpoint-policy.json").read_text())
INCLUDED = [p for p in POLICY if p["decision"] == "include"]
EXCLUDED = [p for p in POLICY if p["decision"] == "exclude"]


def envelope(data=None, **meta):
    return {"data": data, "extra": None, "meta": {"success": True, "status": 200, **meta}}


@pytest.fixture
def settings():
    return Settings(_env_file=None, api_base_url="https://api.example.test/api")


def app_with_backend(settings, handler):
    backend = WiseClient(settings, transport=httpx.MockTransport(handler))
    return create_app(settings, client=backend)
