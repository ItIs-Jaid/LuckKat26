"""Tests for the localhost-interaction-metrics backend (metrics.py + server router).

Uses a TEMP metrics.db (via METRICS_DB_PATH) and never the live file. The shared
`client` fixture in conftest.py isolates both kb/kb.db and metrics.db per test.
"""
from __future__ import annotations

import pytest

import metrics


@pytest.fixture
def metrics_env(tmp_path, monkeypatch):
    """Point the shared metrics module at an isolated temp DB with a known secret."""
    monkeypatch.setenv("METRICS_SECRET", "test-secret")
    monkeypatch.setenv("METRICS_DB_PATH", str(tmp_path / "metrics.db"))
    metrics.init_metrics()  # re-resolve path/secret and (re)create tables
    return metrics


@pytest.fixture
def signed_cookie(client, monkeypatch):
    """A valid signed METRICS_VISITOR cookie minted under the app's secret."""
    monkeypatch.setenv("METRICS_SECRET", "test-secret")
    metrics.init_metrics()  # keep the shared module on the same temp DB
    _, value = metrics.issue_visitor()
    return value


# --- cookie scheme ---------------------------------------------------------

def test_cookie_roundtrip(metrics_env):
    vid, value = metrics_env.issue_visitor()
    assert "." in value
    assert metrics_env.validate_cookie(value) == vid


def test_tampered_cookie_is_rejected(metrics_env):
    vid, value = metrics_env.issue_visitor()
    _vid, sig = value.rsplit(".", 1)
    tampered = f"{_vid}.{sig[:-1]}0" if sig else f"{_vid}.x"
    assert metrics_env.validate_cookie(tampered) is None
    # malformed / missing inputs never raise and always return None
    assert metrics_env.validate_cookie("not-a-cookie") is None
    assert metrics_env.validate_cookie("vidwithnodot") is None
    assert metrics_env.validate_cookie("vid.") is None
    assert metrics_env.validate_cookie("") is None
    assert metrics_env.validate_cookie(None) is None


def test_wrong_secret_is_rejected(metrics_env, monkeypatch):
    vid, value = metrics_env.issue_visitor()  # signed under "test-secret"
    monkeypatch.setenv("METRICS_SECRET", "different-secret")
    assert metrics_env.validate_cookie(value) is None


# --- log_event + summary ---------------------------------------------------

def test_log_event_then_summary(metrics_env):
    m = metrics_env
    vid1, _ = m.issue_visitor()
    vid2, _ = m.issue_visitor()
    m.log_event(vid1, "page_view")
    m.log_event(vid1, "table_select", table="libraries")
    m.log_event(vid1, "search", meta="fastapi")
    m.log_event(vid2, "table_select", table="languages")

    s = m.summary()
    assert s["visits"] == 2
    assert s["unique_visitors"] == 2
    assert s["events"] == 4
    assert s["by_event"] == {"page_view": 1, "table_select": 2, "search": 1}
    assert s["active_sessions"] == 2  # both visited within the last 30 min
    # only non-null table_names, ordered by count desc then name asc
    assert s["top_tables"] == [
        {"table": "languages", "n": 1},
        {"table": "libraries", "n": 1},
    ]


def test_log_event_rejects_unknown_event_and_long_meta(metrics_env):
    vid, _ = metrics_env.issue_visitor()
    with pytest.raises(ValueError):
        metrics_env.log_event(vid, "hack")
    with pytest.raises(ValueError):
        metrics_env.log_event(vid, "page_view", meta="x" * 201)


# --- API contract (via TestClient) -----------------------------------------

def test_get_root_sets_signed_cookie(client):
    r = client.get("/")
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "")
    assert "METRICS_VISITOR=" in sc
    assert "httponly" in sc.lower()
    assert "samesite=lax" in sc.lower()
    assert "max-age=31536000" in sc.lower()
    assert "path=/" in sc.lower()


def test_root_reissues_when_cookie_invalid(client):
    r = client.get("/", cookies={"METRICS_VISITOR": "garbage.invalidsig"})
    assert "set-cookie" in r.headers


def test_post_metrics_unsigned_is_401(client):
    r = client.post("/api/metrics", json={"event": "page_view"})
    assert r.status_code == 401


def test_post_metrics_bad_event_is_400(client, signed_cookie):
    r = client.post(
        "/api/metrics",
        json={"event": "nope"},
        cookies={"METRICS_VISITOR": signed_cookie},
    )
    assert r.status_code == 400


def test_post_metrics_ok_and_reflects_in_summary(client, signed_cookie):
    r = client.post(
        "/api/metrics",
        json={"event": "page_view", "table": "libraries"},
        cookies={"METRICS_VISITOR": signed_cookie},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "id": 1}

    s = client.get("/api/metrics/summary").json()
    assert s["events"] == 1
    assert s["by_event"] == {"page_view": 1}
    assert s["top_tables"] == [{"table": "libraries", "n": 1}]


def test_summary_endpoint_is_open(client):
    # The summary endpoint is read-only aggregate metrics; no visitor cookie needed.
    r = client.get("/api/metrics/summary")
    assert r.status_code == 200
    body = r.json()
    for key in ("visits", "unique_visitors", "events", "by_event", "active_sessions", "top_tables"):
        assert key in body
