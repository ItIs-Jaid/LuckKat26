"""CDN-free guard + / route works (even with inline fallback)."""
from __future__ import annotations


def test_index_route(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_no_cdn_refs(client):
    r = client.get("/")
    body = r.text
    assert "http://" not in body
    assert "https://" not in body
