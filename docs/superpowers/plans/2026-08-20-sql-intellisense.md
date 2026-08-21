# SQL IntelliSense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver the first functional release from `docs/FEATURE SPEC — Editor SQL con Autocompletado Inteligente.md`: fast contextual SQL completion backed by cached real metadata, PostgreSQL and SQLite support, and a themed professional popup.

**Architecture:** Keep completion policy in the domain layer: a cursor-aware analyzer produces `SQLContext`, dialect providers supply engine-specific language items, a metadata cache owns immutable connection snapshots, and `SqlCompletionEngine` ranks candidates. Qt remains an adapter that debounces keystrokes, renders a model/view popup, and inserts the selected item; existing inspectors and `QRunnable` workers remain responsible for blocking database I/O.

**Tech Stack:** Python 3.14, PySide6, Pydantic, sqlglot, RapidFuzz, QtAwesome, pytest/pytest-qt

**Spec:** `docs/FEATURE SPEC — Editor SQL con Autocompletado Inteligente.md`

## Execution Note

The first delivery was completed through commit `36b2d47` and consolidated on
`codex/ui-redesign`. Automated acceptance covers the analyzer, dialects, metadata cache,
PostgreSQL and SQLite providers, non-blocking refresh, popup interaction, and the performance
budget. Real PostgreSQL metadata evidence and the final deterministic dark/light integration
captures are recorded in `design-qa.md`.

## Global Constraints

- Preserve the existing Universal Schema Model, query execution, explorer, themes, and public APIs unless an additive change is required.
- Never query database metadata on an editor keystroke; completion reads only an in-memory snapshot.
- Metadata I/O runs through the existing `QThreadPool`/`QRunnable` architecture.
- Cached completion for normal statements must remain below 100 ms.
- First delivery supports PostgreSQL and SQLite; dialect interfaces support PostgreSQL, MySQL/MariaDB, SQLite, and SQL Server.
- Use model/view popup rendering and central light/dark theme tokens.

---

### Task 1: Cursor-aware SQL context analyzer

**Files:**
- Create: `src/backend_ide/domain/sql/context.py`
- Test: `tests/test_sql_context.py`

**Interfaces:**
- Produces: `SQLContextAnalyzer.analyze(sql: str, cursor_position: int) -> SQLContext`
- Produces: `SQLContext(statement, clause, current_token, qualifier, schema_qualifier, aliases, tables, expects_relation)`

- [x] **Step 1: Write failing analyzer tests**

```python
def test_analyzer_resolves_join_alias_at_cursor():
    sql = "SELECT * FROM users u JOIN orders o ON o."
    context = SQLContextAnalyzer().analyze(sql, len(sql))
    assert context.qualifier == "o"
    assert context.aliases == {"u": "users", "o": "orders"}
    assert context.clause == "ON"


def test_analyzer_isolates_current_statement():
    sql = "SELECT x. FROM old x; SELECT u. FROM users u"
    context = SQLContextAnalyzer().analyze(sql, len(sql))
    assert context.statement == " SELECT u. FROM users u"
    assert context.aliases == {"u": "users"}
```

- [x] **Step 2: Run `uv run pytest tests/test_sql_context.py -q` and verify the missing module failure.**
- [x] **Step 3: Implement a small tokenizer/state analyzer that ignores quoted strings/comments, selects the statement containing the cursor, detects clauses, relation sources, aliases, qualifier and current token.**
- [x] **Step 4: Run `uv run pytest tests/test_sql_context.py -q` and verify all analyzer cases pass.**

### Task 2: Dialects, snippets, candidate model, and contextual ranking

**Files:**
- Create: `src/backend_ide/domain/sql/dialects.py`
- Create: `src/backend_ide/domain/sql/snippets.py`
- Modify: `src/backend_ide/domain/sql/completer.py`
- Modify: `src/backend_ide/domain/sql/__init__.py`
- Test: `tests/test_sql_completion.py`

**Interfaces:**
- Produces: `SQLDialectProvider.keywords()`, `.functions()`, `.data_types()` and `get_dialect_provider(engine_name)`.
- Produces: `SnippetProvider.complete(prefix) -> list[CompletionItem]`.
- Produces: `SqlCompletionEngine.complete(sql, cursor_position, metadata=None, dialect=None) -> list[CompletionItem]`.
- Retains: `get_completions(prefix="", context_text="")` as a compatibility wrapper.

- [x] **Step 1: Add failing tests for the required keywords, schema/table/view completion, aliases, JOIN, SELECT columns, INSERT, UPDATE, WHERE, schema-dot, functions, snippets, PostgreSQL/SQLite function differences, fuzzy `rsv -> reservations`, and contextual ordering over generic keywords.**
- [x] **Step 2: Run the focused completion tests and verify failures expose missing context/ranking behavior.**
- [x] **Step 3: Add the four dialect providers and basic `sel`, `ins`, `upd`, and `ct` snippets without adding a dependency.**
- [x] **Step 4: Expand `CompletionKind` and `CompletionItem` with insert text, documentation and score; orchestrate context candidates and rank with RapidFuzz.**
- [x] **Step 5: Run `uv run pytest tests/test_sql_context.py tests/test_sql_completion.py -q` and verify all domain completion tests pass.**

### Task 3: Explicit connection metadata cache and engine adapters

**Files:**
- Create: `src/backend_ide/application/metadata_cache.py`
- Create: `src/backend_ide/infrastructure/database/sqlite/__init__.py`
- Create: `src/backend_ide/infrastructure/database/sqlite/metadata.py`
- Modify: `src/backend_ide/infrastructure/database/contracts.py`
- Modify: `src/backend_ide/infrastructure/database/postgresql/inspector.py`
- Test: `tests/test_metadata_cache.py`
- Test: `tests/test_sqlite_metadata.py`

**Interfaces:**
- Produces: `ConnectionMetadataCache.put(key, schema)`, `.get(key)`, `.update_columns(key, schema, table, columns)`, `.invalidate(key)`.
- Produces: `SQLiteMetadataProvider.inspect_database() -> DatabaseSchema` using `sqlite_master` and `PRAGMA table_info`.
- Adds metadata capability methods to the infrastructure contract while allowing existing PostgreSQL inspector reuse.

- [x] **Step 1: Add failing tests proving cache isolation by connection/database, atomic column updates, invalidation, and SQLite table/view/column inspection against an in-memory database.**
- [x] **Step 2: Run both new test modules and verify failures.**
- [x] **Step 3: Implement the cache and SQLite provider; expose PostgreSQL metadata through the existing inspector rather than duplicating catalog SQL.**
- [x] **Step 4: Run the cache/SQLite/PostgreSQL inspector suites and verify they pass.**

### Task 4: Non-blocking metadata integration and refresh

**Files:**
- Modify: `src/backend_ide/infrastructure/database/schema_inspection_worker.py`
- Modify: `src/backend_ide/infrastructure/database/table_columns_worker.py`
- Modify: `src/backend_ide/ui/views/main_window.py`
- Test: `tests/test_schema_inspection_worker.py`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: `ConnectionMetadataCache` and `DatabaseSchema` snapshots.
- Produces: active cached metadata propagated to every existing/new editor.
- Produces: manual `Refrescar metadata` action and successful-DDL invalidation/refresh hook.

- [x] **Step 1: Add failing tests for cache promotion on connection switch, stale worker rejection, new-tab propagation, manual refresh, lazy real-column updates, and successful CREATE/ALTER/DROP refresh detection.**
- [x] **Step 2: Run the focused worker/window tests and verify failures.**
- [x] **Step 3: Promote worker results atomically into the cache, keep all database reads in workers, wire the refresh action, and refresh after successful DDL with conservative statement detection.**
- [x] **Step 4: Run the worker/window tests and verify they pass without regressing explorer behavior.**

### Task 5: Debounced professional completion popup

**Files:**
- Modify: `src/backend_ide/ui/editor/sql_editor_widget.py`
- Modify: `src/backend_ide/ui/editor/sql_completer.py`
- Modify: `src/backend_ide/ui/theme/manager.py`
- Test: `tests/test_sql_completion.py`

**Interfaces:**
- Consumes: `SqlCompletionEngine.complete` at the editor cursor.
- Produces: 150 ms automatic debounce, immediate dot activation, forced Ctrl/Cmd+Space activation, Enter/Tab acceptance, Escape dismissal, Arrow navigation, per-kind icons and detail/tooltips.

- [x] **Step 1: Add failing pytest-qt cases for debounce, immediate dot completion, full-document cursor context, Ctrl+Space on empty input, Enter/Tab replacement, Escape, clean icon labels, and centralized light/dark styling.**
- [x] **Step 2: Run the focused UI tests and verify failures.**
- [x] **Step 3: Implement the timer-driven trigger and model/view popup adapter; pass the complete SQL plus exact cursor position and never access a database from Qt completion code.**
- [x] **Step 4: Run the focused UI tests and verify all keyboard and popup behavior passes.**

### Task 6: Acceptance, performance, visual QA, and documentation

**Files:**
- Modify: `design-qa.md`

**Interfaces:**
- Verifies the complete first-delivery path against the feature specification.

- [x] **Step 1: Add acceptance/performance tests for `SELECT r.`, `WHERE c.`, `JOIN ... ON c.`, PostgreSQL and SQLite dialects, and a cached normal completion under 100 ms.**
- [x] **Step 2: Run `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, and `git diff --check`.**
- [x] **Step 3: Launch offscreen with a real PostgreSQL profile, confirm real cached table columns appear for alias completion without a keystroke query, and capture dark/light popup images.**
- [x] **Step 4: Record traceability, captures, manual checks, known first-delivery limits, and second-delivery debt in `design-qa.md`.**
- [x] **Step 5: Repeat the full test/lint/format/diff verification after documentation and leave the desktop application running for user testing.**
