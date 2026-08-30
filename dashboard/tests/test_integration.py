"""GUI-facing integration tests for the INTERACTION METRICS panel + track().

OWNERSHIP (per Lead brief / design doc):
  - Supervisor B (GUI) owns the tests in THIS file.
  - Supervisor A (backend) APPENDS the /api/metrics POST + /api/metrics/summary
    endpoint tests BELOW these — do NOT rewrite B's tests; add functions.

These GUI tests only assert on the *served* index.html, so they stay green
whether or not the metrics backend (metrics.py / server.py router) exists yet.
They verify the panel markup and the client-side tracking wiring are present.
"""
from __future__ import annotations


def test_index_serves_metrics_panel(client):
    """GET / must serve the dashboard HTML containing the INTERACTION METRICS
    panel and a fetch to the summary endpoint."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "INTERACTION METRICS" in body
    assert "/api/metrics/summary" in body


def test_index_has_client_side_tracking_wiring(client):
    """The served HTML must include the cookie-gated track() function and a
    best-effort POST to /api/metrics, proving analytics is wired (and silent)."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "METRICS_VISITOR" in body  # cookie-gating of tracking
    assert "function track(" in body  # client-side tracker present
    assert "/api/metrics" in body     # POST target referenced


def test_index_panel_reuses_cyberpunk_classes(client):
    """The metrics panel must reuse the existing cyberpunk card / bar classes
    (no off-theme bespoke markup for the core stats + breakdowns)."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    for cls in ("class=\"metrics\"", "id=\"metricsStats\"", "id=\"metricsByEvent\"", "id=\"metricsTopTables\""):
        assert cls in body
