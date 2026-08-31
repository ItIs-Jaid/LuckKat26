# 04 · FRONTEND / GUI REVIEW — bugs, cyberpunk spec, local/NAS file-ref design

Lens: frontend/GUI. Scope: `dashboard/static/index.html` + `dashboard/server.py` (contract). Read-only. Operator: Jaid.

---

## CURRENT FRONTEND BUGS

### [HIGH] XSS — unescaped server-derived labels in cards (innerHTML) — index.html:281, :293, :297
`sevHtml`/`catHtml` build HTML by concatenating `k` (the `vuln_severity` / `tool_category` keys from `/api/summary`) straight into `innerHTML`. `k` is data text, not a trusted literal. The KB ingests external advisories, so these keys are influenced by outside data.
- `:277-279` `<span class="lab">'+k+'</span>` — unescaped into element text.
- `:293` `title="'+k+'"` — unquote-escaped: a `"` in `k` breaks out of the attribute → `onmouseover=`/script injection. This is the dangerous one.
- `:297` `catHtml` same pattern.
Fix: set label via `textContent` (like the row cells already do) OR run `k` through `esc()` and an attribute-escaper. Positive control exists: `esc()` at `:330` is used correctly for `col.type` (`:323`) and drawer (`:518,:522-523`); the cards simply don't use it.
Note: row **cells** are SAFE — `cell.textContent = f.text` (`:433`). Row values are NOT an XSS vector. Only the summary cards are.

### [MEDIUM] Infinite-fetch loop if API returns non-null cursor with empty/tiny pages — index.html:397-411, :460-462
`ensureLoaded(index)`: base cases are `index <= rows.length` and `nextCursor == null`. If the server keeps `next_cursor` non-null but each page yields 0 (or a few) new rows, `rows.length` never advances past `index`, so the recursion at `:407` (`return ensureLoaded(start+vis)`) never terminates → unbounded network storm. The `state.fetching` guard (`:398`) only prevents re-entrancy during an in-flight request, not the post-fetch recursion.
Fix: after a page, if `items.length === 0` set `state.nextCursor = null` and stop; or track `lastLen` and bail when `rows.length` made no progress; or cap recursion depth (e.g. `MAX_PREFETCH_PAGES = 200`).

### [LOW] Spacer cap makes >~1.07M rows unreachable — index.html:162, :357-359
`MAX_SPACER = 30000000` px; `spacer.h = min(MAX_SPACER, logical*ROW_H)`; windowing maps `scrollTop/ROW_H` → row index. 30M/28 ≈ 1,071,428 addressable rows. For `expectedTotal` above ~1M the scrollbar maxes out and the tail is never rendered. Scaling limit, not a crash. Mitigate later with windowed/indexed scroll (scroll-by-ratio) if a table exceeds this.

### [LOW] Spacer trusts `expectedTotal` from server — index.html:357
`logical = max(expectedTotal, rows.length)`. An inaccurate/over-large `total` yields a too-tall spacer (capped at 30M) → blank scroll space and a misleading scrollbar thumb. Benign, cosmetic. Acceptable; note for contract hardening (server should return accurate `total`).

### [LOW] Ineffective de-dup guard (dead code) — index.html:383
`state.rows[len-1] === it` is reference equality on freshly-parsed JSON objects → always false; only the `id === it.id` check can skip, and that only drops a true duplicate id (won't happen). The guard is effectively a no-op. Harmless; flag so a future reader doesn't trust it.

### [LOW] No keyboard nav / focus mgmt for rows + drawer — index.html (events :543-565)
Rows clickable only; drawer close is mouse-only. Accessibility/UX gap, not a bug. Optional.

### [INFO] Graceful summary degrade is OK — index.html:251, :586-593
If `/api/summary` is slow/fails, cards show "summary unavailable" and `renderCards()` re-runs on resolve; rows still load independently. No action needed. (Documented so reviewers know it's intended, not a defect.)

### [INFO] Good guards already present
- rAF-throttled scroll render via `scheduleRender`/`renderScheduled` (`:447-454`, listener `:544`) — no scroll thrash. ✓
- `state.fetching` early-return prevents concurrent double-fetch (`:398`). ✓
- Drawer URL uses `encodeURIComponent` (`:515`). ✓
- Row values via `textContent` (`:433`). ✓

---

## DESIGN: cyberpunk + seamless local/NAS file-ref

### A. Cyberpunk aesthetic spec (CDN-free, inline CSS, system fonts only)

**Tokens**
| token | value | use |
|---|---|---|
| `--bg` | `#0a0a12` | app background (was `#0e1116`) |
| `--panel` | `#0d0f1a` | headers/cards/drawer |
| `--panel2` | `#11141f` | controls |
| `--line` | `#1b2a3a` | hairlines (cyan-tinted) |
| `--ink` | `#c8f5ff` | primary text (icy) |
| `--muted` | `#5c7689` | secondary |
| `--accent` | `#00f0ff` | NEON CYAN (primary) |
| `--accent2` | `#ff2cf0` | NEON MAGENTA (secondary) |
| `--crit` | `#ff2b5e` | red-pink |
| `--high` | `#ff8a00` | amber |
| `--med` | `#00f0ff` | cyan |
| `--low` | `#39ff14` | toxic green |
| `--row-h` | `28px` | keep |
| `--glow` | `0 0 6px` accent | text/box glow |

**Font**: monospace/terminal — `font: 12px/1.4 ui-monospace,"SF Mono","Cascadia Code","Consolas","Liberation Mono",monospace;` (no Google Fonts; system stack only).

**Effects (all inline CSS, no assets)**
- Scanlines: fixed overlay `body::after { background: repeating-linear-gradient(0deg, rgba(0,240,255,.04) 0 1px, transparent 1px 3px); pointer-events:none; }`
- Grid backdrop: `body { background: radial-gradient(...) , linear-gradient(...) }` faint cyan grid.
- Glow: `text-shadow: 0 0 6px var(--accent)` on headings/accents; `box-shadow: 0 0 8px rgba(0,240,255,.35)` on active card/selected row.
- Selected row: `box-shadow: 0 0 0 1px var(--accent), 0 0 10px rgba(0,240,255,.25) inset`.
- Drawer border: `1px solid var(--accent2)` with magenta glow.
- CRT flicker (optional, subtle): `@keyframes flicker` toggling opacity 0.97↔1 on `body::after`, 8s.

**CSS sketch**
```css
:root{ --bg:#0a0a12; --panel:#0d0f1a; --panel2:#11141f; --line:#1b2a3a;
  --ink:#c8f5ff; --muted:#5c7689; --accent:#00f0ff; --accent2:#ff2cf0;
  --crit:#ff2b5e; --high:#ff8a00; --med:#00f0ff; --low:#39ff14; --row-h:28px; }
body{ background:var(--bg); color:var(--ink);
  font:12px/1.4 ui-monospace,"SF Mono","Cascadia Code","Consolas",monospace; }
body::after{ content:""; position:fixed; inset:0; pointer-events:none; z-index:30;
  background:repeating-linear-gradient(0deg, rgba(0,240,255,.045) 0 1px, transparent 1px 3px); }
.card.active,.row.selected{ box-shadow:0 0 0 1px var(--accent), 0 0 10px rgba(0,240,255,.25); }
header.top h1{ color:var(--accent); text-shadow:0 0 8px var(--accent); letter-spacing:1px; }
.drawer{ border-left:1px solid var(--accent2); box-shadow:-8px 0 24px rgba(255,44,240,.18); }
```

### B. Local/NAS file-referencing — backend (NEW, not built)

**Endpoints (add to server.py; read-only)**
- `GET /api/fs/list?root=<id>&path=<rel>` → `{entries:[{name,is_dir,size,mtime,rel}]}`
- `GET /api/fs/read?root=<id>&path=<rel>&max=<bytes=65536>` → `{path,text,truncated}`
- `GET /api/fs/roots` → `[{id,label,path}]` (drives the GUI root switcher)

**Allowlist + path-traversal safety (CRITICAL)**
- Env `ALLOWED_ROOTS="local:C:/Users/Jaide/projects;nas:/data"` (semicolon list of `id:abs`). On k3s: `local:/app;nas:/data` (NAS already mounted at `/data`). Per-deployment via env — nothing hard-coded.
- Normalize every requested `path` with `pathlib.Path.resolve()` (expands `..`, symlinks, `.`, case on Windows).
- **Reject** if the resolved path is not `>=` an allowed root: `root in (resolved, *resolved.parents)` → 403/400. This blocks `../`, symlink escapes, and absolute overrides.
- Symlinks: `resolve()` follows them; re-check the *resolved* target is still under root. Optionally `os.path.realpath` + compare.
- Read-only: never write; cap `read` at `max` bytes; ignore binary (detect via NUL / extension allowlist) → return metadata only.
- No glob, no recursion beyond one level in `list`.

**Windows path trap (flag)**
- Dev (Windows): roots look like `C:/Users/Jaide/...`; in-container they're `/data`. The backend MUST normalize both sides with the OS-native `pathlib` and compare with `os.path.normcase` on Windows (case-insensitive) so `c:/Users` ≠ escape. Pass `root` id from the GUI, never raw absolute client paths, so traversal checks happen server-side only.

### C. Local/NAS file-referencing — GUI (NEW)

**Layout (cyberpunk-styled)**
- New left "File Explorer" panel (collapsible), monospace, neon grid. Top: root switcher (local / nas) from `/api/fs/roots`. Below: tree (lazy `fs/list` per folder) + preview pane.
- Tree rows: `▸ name` (dir) / `· name` (file), size+mtime in muted cyan. Click dir → expand; click file → load preview in the pane (right side or reuse drawer).
- Preview pane: `<pre>` of file text (capped), with glow; binary → "binary — N bytes, no preview".
- **Reference action**: a "↳ insert @ref" button (and double-click) copies `@root:/rel/path` into a reference buffer. Insert target: the search box (prefills `q=`), the drawer "resolved sources" list, or a new "references" strip above the table. Clicking an inserted `@ref` opens that file in the preview (deep-link). This is the "see local + NAS files seamlessly for referencing" loop Jaid asked for.
- Coexists with KB browsing: file-ref is a separate panel; referencing a file attaches it to the current row view / copies its path — it does NOT replace the SQLite table browsing.

**k3s coexistence**
- In-pod: `local` = mounted workspace (e.g. `/app`), `nas` = `/data` (already mounted). Same endpoints, different `ALLOWED_ROOTS`. No code change between dev/prod — only env.
- On Jaid's Windows dev box: `local` = her projects dir, `nas` = whatever she mounts (or omitted). Define `ALLOWED_ROOTS` in the process env / k8s secret.

### D. Gaps: current index.html → target
1. **Aesthetic**: current is flat GitHub-dark; needs cyberpunk tokens + scanline/glow/grid (Section A). Pure CSS swap, no structural change.
2. **File Explorer**: entirely absent. Needs panel + `/api/fs/*` calls + reference buffer (Section B/C).
3. **XSS**: fix card innerHTML before any data surfaces grow (Section HIGH).
4. **Windowing**: add prefetch-termination guard + plan ratio-scroll for >1M rows (Sections MEDIUM/LOW).
5. **Keyboard/a11y**: add row focus + drawer Esc-close for parity with the terminal aesthetic.

---
*Reviewed read-only. No source files modified. Findings cite file:line in `dashboard/static/index.html` and `dashboard/server.py`.*
