"""Pytest fixtures: synthetic KB DB (no real kb.db) + TestClient."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = db.make_fixture_db(tmp_path / "kb.db")
    monkeypatch.setenv("KB_DB_PATH", str(db_path))
    # Isolate the metrics store too, so GET / (which sets a signed visitor
    # cookie) and the metrics endpoints never touch the live metrics.db.
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.db"))
    import importlib

    import metrics as _metrics
    import server as _server

    _metrics.init_metrics()  # point the shared module singleton at the temp db
    importlib.reload(_server)
    return TestClient(_server.app)
