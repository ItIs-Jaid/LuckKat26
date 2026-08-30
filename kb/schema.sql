-- DevSecLoc KB schema — local-first knowledge base
-- Live store = this SQLite file. Exports in kb/export/ are review-only mirrors.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS languages (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    version     TEXT,
    role        TEXT,            -- what this language is used for in the stack
    notes       TEXT,
    source_ids  TEXT,            -- ';'-joined ids from sources.id
    accessed_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 3  -- 1..5 (1=claim, 5=verified primary doc)
);

CREATE TABLE IF NOT EXISTS libraries (
    id          INTEGER PRIMARY KEY,
    language_id INTEGER REFERENCES languages(id),
    name        TEXT NOT NULL,
    category    TEXT,            -- web-framework, orm, http, container, crypto...
    purpose     TEXT,
    ecosystem   TEXT,            -- pip/npm/vcpkg/crates/cargo/docker...
    version     TEXT,
    source_ids  TEXT,
    accessed_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS patterns (
    id          INTEGER PRIMARY KEY,
    domain      TEXT NOT NULL,   -- python|c_cpp|web|devops|security|systems
    title       TEXT NOT NULL,
    problem     TEXT,            -- when to use
    solution    TEXT,            -- how
    anti_pattern TEXT,           -- what NOT to do
    snippet     TEXT,            -- optional reference snippet
    source_ids  TEXT,
    accessed_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS tutorials (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    url         TEXT,
    domain      TEXT,
    level       TEXT,            -- beginner|intermediate|advanced
    summary     TEXT,
    source_ids  TEXT,
    accessed_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    kind        TEXT,            -- github|reddit|docs|advisory|blog|paper
    title       TEXT,
    url         TEXT UNIQUE,
    tier        INTEGER DEFAULT 3, -- 1 community ... 3 primary/official
    accessed_at TEXT DEFAULT (datetime('now')),
    last_ok     INTEGER DEFAULT 1, -- 1 reachable, 0 dead (re-validation)
    content_hash TEXT            -- for change detection
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    id          INTEGER PRIMARY KEY,
    cve         TEXT,
    ecosystem   TEXT,
    package     TEXT,
    severity    TEXT,            -- low|medium|high|critical
    summary     TEXT,
    fixed_in    TEXT,
    source_ids  TEXT,
    discovered_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 4
);

CREATE TABLE IF NOT EXISTS methodologies (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    domain      TEXT,
    summary     TEXT,
    steps       TEXT,            -- newline-separated
    source_ids  TEXT,
    accessed_at TEXT DEFAULT (datetime('now')),
    confidence  INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS code_reviews (
    id          INTEGER PRIMARY KEY,
    task        TEXT,
    lang        TEXT,
    file_path   TEXT,
    finding     TEXT,
    severity    TEXT,
    resolution  TEXT,
    verified_by TEXT,            -- jaid | model:<name> | null
    created_at  TEXT DEFAULT (datetime('now')),
    source_ids  TEXT
);

CREATE TABLE IF NOT EXISTS errors (
    id          INTEGER PRIMARY KEY,
    lang        TEXT,
    error_sig   TEXT,            -- normalized signature / message key
    cause       TEXT,
    fix         TEXT,
    recurrence  INTEGER DEFAULT 1,
    verified_by TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    source_ids  TEXT
);

CREATE TABLE IF NOT EXISTS research_runs (
    id          INTEGER PRIMARY KEY,
    ran_at      TEXT DEFAULT (datetime('now')),
    mode        TEXT,            -- deterministic | llm
    model       TEXT,            -- null for deterministic
    items_new   INTEGER DEFAULT 0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    id          INTEGER PRIMARY KEY,
    kind        TEXT,            -- vuln|synthesis|pattern
    payload     TEXT,
    status      TEXT DEFAULT 'pending', -- pending|approved|rejected
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_patterns_domain ON patterns(domain);
CREATE INDEX IF NOT EXISTS idx_lib_lang ON libraries(language_id);
CREATE INDEX IF NOT EXISTS idx_vuln_eco ON vulnerabilities(ecosystem);
CREATE INDEX IF NOT EXISTS idx_src_url ON sources(url);

-- Security tooling reference (Black Arch / Kali niche tools: red_team|recon|cloud|osint).
-- Seeded from security-tools-reference.md via kb/seed_security_tools.py.
-- Each tool's source_url is also inserted into `sources` so the daily updater's
-- URL re-validation keeps links fresh (self-improving knowledge base).
CREATE TABLE IF NOT EXISTS security_tools (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    category      TEXT NOT NULL,   -- red_team|recon|cloud|osint
    subcategory   TEXT,
    kali_pkg      TEXT,            -- package name, or 'pip'/'git'/'' if absent
    blackarch_pkg TEXT,
    availability  TEXT,            -- verified|unverified
    niche_use     TEXT,
    source_url    TEXT,
    source_id     INTEGER REFERENCES sources(id),
    added_at      TEXT DEFAULT (datetime('now')),
    confidence    INTEGER DEFAULT 3
);

CREATE INDEX IF NOT EXISTS idx_sectools_cat ON security_tools(category);
CREATE INDEX IF NOT EXISTS idx_sectools_name ON security_tools(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sectools_uniq ON security_tools(name, category);
