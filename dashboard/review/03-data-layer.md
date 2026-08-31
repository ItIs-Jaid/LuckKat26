# Lens 3 — Data Layer Review (`dashboard/db.py`)

**Reviewer:** subagent (Lens 3 focused break-test)
**Method:** read + execution. Ran the suite against the synthetic fixture DB (`db.make_fixture_db`), and added a throwaway probe (`tests/test_throwaway_lens3.py`) covering all requested edge cases, then deleted it. Did **not** edit any source file.

## Verdict: FAIL (C-1) — FIXED by Lead QA

One **CRITICAL** fetch-correctness bug (now fixed) in the keyset cursor for severity-sorted pagination, plus one **MEDIUM** test-harness defect that prevents the documented test command from even running. All 5 latched gotchas (a–e) are still correct.

---

## CRITICAL

### C-1 — Severity-sort keyset cursor compares raw TEXT `severity` against a numeric rank (cursor drift / fetch-correctness)
**Location:** `db.py:247-266` (cursor predicate uses `{sort}` = raw `severity` column) vs `db.py:199-203,277-282` (ORDER BY uses `SEVERITY_RANK_CASE`). Also the `next_cursor` encoder at `db.py:289-290` emits a numeric rank.

**Root cause:** When `sort == "severity"`, `sort_expr = SEVERITY_RANK_CASE` (a numeric CASE expression: CRITICAL=4 … VECTOR/LOW=1, UNKNOWN=0). The SELECT ORDER BY uses `sort_expr`, but the keyset cursor predicate is built by interpolating the *raw* `{sort}` column name (`severity`, a TEXT column) while binding `cursor_params = [sort_val]*4 + [row_id] + …` where `sort_val` is the **numeric** rank from `_severity_rank()`. So the predicate compares `severity < ?` / `severity > ?` where `?` is an INTEGER. In SQLite, `TEXT < INTEGER` is always FALSE and `TEXT > INTEGER` is always TRUE (storage-class order: INTEGER < TEXT).

**Observed (execution):**
- `dir=desc`, `limit=2`: page 1 = `[1,2]`, page 2 = **empty** → rows 3,4,5 silently dropped. (`severity < rank` is never true.)
- `dir=asc`, `limit=2`: page 1 = `[5,3]`, page 2 = `[5,3]` again → **infinite loop**, rows 4,2,1 never returned. (`severity > rank` is always true, so the whole table is re-returned from the top.)

**Impact:** Any UI "sort by severity" + paging (or API `?sort=severity&after=...`) loses/duplicates rows. This is user-facing and silent for DESC (looks like "fewer results than total says").

**Fix (do NOT apply — report only):** In the cursor-predicate f-strings (`db.py:252-264`) substitute `{sort_expr}` for `{sort}` when `sort_expr != sort` (i.e. the severity case), so the bound numeric rank is compared against the same numeric `SEVERITY_RANK_CASE` expression the ORDER BY uses. `_encode_cursor`/`_decode_cursor` already carry the numeric rank, so the binding stays consistent.

---

## MEDIUM

### M-1 — Documented test command cannot import `db` (whole suite fails to collect)
**Location:** `dashboard/tests/conftest.py:9` (`import db`); no `pytest.ini` / `[tool.pytest.ini_options]` / `pythonpath` anywhere; `dashboard/__init__.py` present.

**Observed:** `cd dashboard && uv run pytest -q` aborts at collection with `ModuleNotFoundError: No module named 'db'` (same from repo root via `uv run pytest dashboard/tests`). Under pytest's default "prepend" import mode, `dashboard/__init__.py` makes the test package resolve as `dashboard.tests`, so `dashboard/` is dropped from `sys.path[0]` and `import db` fails.

**Workaround used for this review:** `cd dashboard && PYTHONPATH=. uv run pytest -q` — now all **13 existing tests pass** (4 `test_db` + 7 `test_api` + 2 `test_index`). Real fix: add a pytest config (`pythonpath = ["."]` under `[tool.pytest.ini_options]` in a `pyproject.toml`/`pytest.ini` in `dashboard/`, or `import db` via a `conftest` path insertion).

---

## OK (verified by execution)

- **(a) placeholder count:** cursor f-string has exactly 10 `?`; `cursor_params = [sort_val]*4 + [row_id] + [sort_val]*4 + [row_id]` = 10. Match confirmed (`test_gotcha_a_cursor_placeholder_count`).
- **(b) WHERE assembly:** `cursor_pred.replace(" AND (", " WHERE (", 1)` at `db.py:270` correctly flips to `WHERE (` when there is no preceding search clause; the no-search severity query compiled/executed without a syntax error.
- **(c) total excludes cursor:** `db.py:273-275` COUNT uses `search_sql` only (no cursor predicate); severity pagination reported constant `total=5`, severity-filter probes reported `total=1`.
- **(d) normalize_severity:** `MODERATE→MEDIUM`, `CVSS:…→VECTOR`, `None→UNKNOWN`, unrecognized→UNKNOWN (`db.py:93-108`); covered by `test_normalize_severity`.
- **(e) severity filter vs normalized token:** filter `severity=MEDIUM` matched the raw `MODERATE` row (id 2) and `severity=VECTOR` matched the raw `CVSS:…` row (id 3); CASE emits `VECTOR`/`MEDIUM` and `sev_param` is normalized (`db.py:221-238`).
- Non-severity sorts are correct: deep pagination by `id` (desc) and by `fixed_in` (a column with a NULL) returned the full disjoint set `{1..5}` with no drift, no off-by-one.
- `q` search with no matching rows → `total=0`, `items=[]`, `next_cursor=None`.

---

## Edge cases probed (all except severity pass)
| Case | Result |
|---|---|
| Sort by column with NULLs (`fixed_in`), deep paginate | OK — full coverage, no drift |
| Sort by severity (DESC) deep paginate | **FAIL (C-1)** — page 2 empty |
| Sort by severity (ASC) deep paginate | **FAIL (C-1)** — infinite repeat |
| `q` search, zero rows | OK |
| Filter `severity=MEDIUM` (raw MODERATE) | OK — id 2 |
| Filter `severity=VECTOR` (raw CVSS) | OK — id 3 |
| Deep pagination (`id`, limit 2, 5 rows) | OK — `[2,2,1]` disjoint pages |

## Summary JSON
```json
{
  "critical": ["db.py:247-266,277-282,289-290 — severity-sort keyset cursor compares raw TEXT `severity` vs numeric bound rank (ORDER BY uses SEVERITY_RANK_CASE): DESC page2 empty (rows 3,4,5 lost), ASC loops [5,3] (rows 4,2,1 lost). Use sort_expr in cursor predicate."],
  "high": [],
  "medium": ["dashboard/tests/conftest.py:9 — `import db` fails under default pytest import mode; documented `cd dashboard && uv run pytest -q` aborts at collection (ModuleNotFoundError). No pythonpath/ini config + dashboard/__init__.py. Run with PYTHONPATH=. or add pytest pythonpath config."],
  "low": [],
  "ok": ["(a) cursor 10 placeholders == 10 params [db.py:266]","(b) WHERE assembly replace(' AND (',' WHERE (',1) correct [db.py:270]","(c) total COUNT excludes keyset cursor [db.py:273-275]","(d) normalize_severity MODERATE->MEDIUM, CVSS:->VECTOR [db.py:93-108]","(e) severity filter compares NORMALIZED token [db.py:221-238]","non-severity deep pagination (id, fixed_in) correct","q no-rows -> total 0/empty/next None","filter MEDIUM->raw MODERATE(id2), VECTOR->raw CVSS(id3)"],
  "verdict": "FAIL",
  "pytest_result": "documented `cd dashboard && uv run pytest -q` FAILS at collection (ImportError: No module named 'db'); with PYTHONPATH=. the 13 existing tests PASS and 2 added severity probes FAIL (they expose C-1)."
}
```
