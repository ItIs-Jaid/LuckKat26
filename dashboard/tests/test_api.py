"""TestClient endpoint tests (contract)."""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_tables(client):
    r = client.get("/api/tables")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12
    assert all(t["rows"] > 0 for t in data)


def test_summary_medium(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    sev = r.json()["vuln_severity"]
    assert "MEDIUM" in sev  # from the MODERATE row
    assert "VECTOR" in sev  # from the CVSS row


def test_rows_limit_and_cursor(client):
    r = client.get("/api/rows?table=vulnerabilities&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None


def test_rows_search(client):
    r = client.get("/api/rows?table=security_tools&q=Go")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert any("GoPhish" == i["name"] for i in items)


def test_rows_unknown_table(client):
    r = client.get("/api/rows?table=NOPE")
    assert r.status_code == 404


def test_row_detail_advisory(client):
    r = client.get("/api/row/vulnerabilities/1")
    assert r.status_code == 200
    body = r.json()
    assert "advisory_keys" in body
