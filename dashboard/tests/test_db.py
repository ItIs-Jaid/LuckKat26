"""Unit tests for db.py — run against the synthetic fixture."""
from __future__ import annotations

import db


def test_normalize_severity():
    assert db.normalize_severity("MODERATE") == "MEDIUM"
    assert db.normalize_severity("CVSS:3.1/AV:N/AC:L") == "VECTOR"
    assert db.normalize_severity("high") == "HIGH"
    assert db.normalize_severity("UNKNOWN") == "UNKNOWN"
    assert db.normalize_severity(None) == "UNKNOWN"
    assert db.normalize_severity("weird") == "UNKNOWN"


def test_source_ids_join(tmp_path, monkeypatch):
    p = db.make_fixture_db(tmp_path / "kb.db")
    monkeypatch.setenv("KB_DB_PATH", str(p))
    detail = db.row_detail("libraries", 1)  # source_ids '1;2;3'
    assert len(detail["sources"]) == 3


def test_query_rows_limit_and_cursor(tmp_path, monkeypatch):
    p = db.make_fixture_db(tmp_path / "kb.db")
    monkeypatch.setenv("KB_DB_PATH", str(p))
    res = db.query_rows("vulnerabilities", limit=2)
    assert len(res["items"]) == 2
    assert res["next_cursor"] is not None
    assert res["total"] == 5
    # fetch next page
    res2 = db.query_rows("vulnerabilities", limit=2, after=res["next_cursor"])
    assert len(res2["items"]) == 2
    # no overlap with page 1
    ids1 = {i["id"] for i in res["items"]}
    ids2 = {i["id"] for i in res2["items"]}
    assert ids1.isdisjoint(ids2)


def test_unknown_table():
    try:
        db.list_columns("NOPE")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_query_rows_severity_sort_keyset_correct(tmp_path, monkeypatch):
    """Regression for the C-1 bug: sorting vulnerabilities by severity must page
    without dropping/duplicating rows. Raw column vs numeric rank compares wrong
    in SQLite (INTEGER < TEXT), so the cursor predicate must use sort_expr.

    Fixture severities (desc rank): id1 HIGH(3), id2 MODERATE->MED(2),
    id3 CVSS:->VECTOR(1), id4 LOW(1), id5 unknown->UNKNOWN(0).
    DESC full walk should visit every id 1..5 exactly once; ASC likewise.
    """
    p = db.make_fixture_db(tmp_path / "kb.db")
    monkeypatch.setenv("KB_DB_PATH", str(p))

    def walk(direction):
        after = None
        seen = []
        for _ in range(10):  # hard cap; a correct walk terminates well before this
            res = db.query_rows("vulnerabilities", sort="severity", dir=direction,
                                limit=2, after=after)
            seen.extend(r["id"] for r in res["items"])
            if res["next_cursor"] is None:
                break
            after = res["next_cursor"]
        return seen

    desc = walk("desc")
    asc = walk("asc")
    assert sorted(set(desc)) == [1, 2, 3, 4, 5], f"DESC lost rows: {desc}"
    assert sorted(set(asc)) == [1, 2, 3, 4, 5], f"ASC lost rows: {asc}"
    # no duplicates -> proves the cursor advanced, not looped
    assert len(desc) == len(set(desc)), f"DESC duplicated: {desc}"
    assert len(asc) == len(set(asc)), f"ASC duplicated: {asc}"

