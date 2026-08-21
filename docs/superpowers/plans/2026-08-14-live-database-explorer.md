# Live Database Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate Database Explorer from the live PostgreSQL profile and match the supplied compact Beekeeper-style database/schema/table navigator.

**Architecture:** `MainWindow` creates a candidate adapter through `ConnectionService` and dispatches a `SchemaInspectionWorker`. The worker uses `PostgreSQLInspector` to discover connectable databases and build the Universal Schema Model; only a successful candidate replaces the active connection and explorer model.

**Tech Stack:** Python 3.14.4, PySide6 6.11, psycopg 3, Pydantic, pytest, pytest-qt, Ruff.

## Global Constraints

- Preserve all existing uncommitted UI, password, SSL, timeout, and test changes.
- Never place passwords in logs, signals, models, status text, or tree labels.
- All network and catalog operations run outside the Qt UI thread.
- Inspect one selected PostgreSQL database at a time.
- A failed refresh or switch preserves the last successful tree and connection.
- Query execution wiring and multi-connection pooling remain out of scope.
- Visual reference: `/home/rafael/Imágenes/Capturas de pantalla/Captura desde 2026-08-14 12-38-08.png`.
- Use QtAwesome icons in the explorer; do not add emoji, custom SVG, or raster placeholders.

---

### Task 1: Discover connectable PostgreSQL databases

**Files:**
- Modify: `src/backend_ide/infrastructure/database/postgresql/inspector.py`
- Modify: `tests/test_postgresql_inspector.py`

**Interfaces:**
- Consumes: `DatabaseConnection.execute_query(query, params=None)`.
- Produces: `PostgreSQLInspector.list_databases() -> list[str]`.

- [ ] **Step 1: Write the failing discovery test**

Extend the mocked query dispatcher and add:

```python
def test_postgresql_inspector_lists_connectable_databases():
    connection = MagicMock()
    connection.execute_query.return_value = [
        {"datname": "analytics"},
        {"datname": "db_outlet"},
    ]

    databases = PostgreSQLInspector(connection).list_databases()

    assert databases == ["analytics", "db_outlet"]
    sql = connection.execute_query.call_args.args[0]
    assert "NOT datistemplate" in sql
    assert "datallowconn" in sql
    assert "has_database_privilege" in sql
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_postgresql_inspector.py::test_postgresql_inspector_lists_connectable_databases`

Expected: FAIL because `PostgreSQLInspector` has no `list_databases` method.

- [ ] **Step 3: Implement database discovery**

Add this public method:

```python
def list_databases(self) -> list[str]:
    rows = self.connection.execute_query(
        """
        SELECT datname
        FROM pg_database
        WHERE NOT datistemplate
          AND datallowconn
          AND has_database_privilege(datname, 'CONNECT')
        ORDER BY datname;
        """
    )
    return [row["datname"] for row in rows]
```

- [ ] **Step 4: Run the focused inspector tests and confirm GREEN**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_postgresql_inspector.py`

Expected: all PostgreSQL inspector tests pass.

- [ ] **Step 5: Commit the discovery unit**

```bash
git add src/backend_ide/infrastructure/database/postgresql/inspector.py tests/test_postgresql_inspector.py
git commit -m "feat: discover accessible postgres databases"
```

---

### Task 2: Inspect schema metadata in a background worker

**Files:**
- Create: `src/backend_ide/infrastructure/database/schema_inspection_worker.py`
- Create: `tests/test_schema_inspection_worker.py`

**Interfaces:**
- Consumes: `DatabaseConnection`, `PostgreSQLInspector.list_databases()`, and `PostgreSQLInspector.inspect_database()`.
- Produces: immutable `DatabaseInspectionResult(database_names: tuple[str, ...], schema: DatabaseSchema)` and `SchemaInspectionWorker(connection, database_names=None)` with `succeeded(object)`, `failed(str)`, and `finished()` signals.

- [ ] **Step 1: Write failing worker success and failure tests**

```python
def test_schema_worker_emits_database_names_and_schema(qtbot):
    connection = MagicMock()
    schema = DatabaseSchema(engine_name="postgresql", database_name="db_outlet")
    worker = SchemaInspectionWorker(connection)
    results = []
    worker.signals.succeeded.connect(results.append)

    with (
        patch.object(PostgreSQLInspector, "list_databases", return_value=["db_outlet"]),
        patch.object(PostgreSQLInspector, "inspect_database", return_value=schema),
    ):
        worker.run()

    assert results[0].database_names == ("db_outlet",)
    assert results[0].schema is schema


def test_schema_worker_disconnects_candidate_and_emits_sanitized_failure(qtbot):
    connection = MagicMock()
    worker = SchemaInspectionWorker(connection)
    errors = []
    worker.signals.failed.connect(errors.append)

    with patch.object(PostgreSQLInspector, "list_databases", side_effect=RuntimeError("denied")):
        worker.run()

    connection.disconnect.assert_called_once()
    assert errors == ["denied"]
```

- [ ] **Step 2: Run the worker tests and confirm RED**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_schema_inspection_worker.py`

Expected: collection FAIL because the worker module does not exist.

- [ ] **Step 3: Implement the worker and result type**

```python
@dataclass(frozen=True, slots=True)
class DatabaseInspectionResult:
    database_names: tuple[str, ...]
    schema: DatabaseSchema


class SchemaInspectionSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class SchemaInspectionWorker(QRunnable):
    def __init__(
        self, connection: DatabaseConnection, database_names: tuple[str, ...] | None = None
    ):
        super().__init__()
        self.connection = connection
        self.database_names = database_names
        self.signals = SchemaInspectionSignals()

    def run(self) -> None:
        try:
            inspector = PostgreSQLInspector(self.connection)
            names = self.database_names or tuple(inspector.list_databases())
            schema = inspector.inspect_database()
            self.signals.succeeded.emit(DatabaseInspectionResult(tuple(names), schema))
        except Exception as err:
            self.connection.disconnect()
            self.signals.failed.emit(str(err))
        finally:
            self.signals.finished.emit()
```

- [ ] **Step 4: Run the worker tests and confirm GREEN**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_schema_inspection_worker.py`

Expected: both worker tests pass.

- [ ] **Step 5: Commit the asynchronous inspection unit**

```bash
git add src/backend_ide/infrastructure/database/schema_inspection_worker.py tests/test_schema_inspection_worker.py
git commit -m "feat: inspect database schema off the ui thread"
```

---

### Task 3: Add database selector and visible explorer states

**Files:**
- Modify: `src/backend_ide/ui/explorer/explorer_widget.py`
- Modify: `tests/test_database_explorer.py`

**Interfaces:**
- Produces: `database_changed = Signal(str)`, `cmb_database`, `btn_refresh`, `btn_add`, `lbl_entities_count`, `set_databases(names, selected)`, `set_loading(preserve_tree=False)`, `show_error(message, preserve_tree=False)`, and `set_controls_enabled(enabled)`.
- Consumes: `DatabaseSchema` through the existing `load_schema_model()`.

- [ ] **Step 1: Write failing explorer behavior tests**

```python
def test_database_dropdown_sits_above_filter_and_emits_selection(qtbot):
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)
    selected = []
    explorer.database_changed.connect(selected.append)

    explorer.set_databases(["analytics", "db_outlet"], "db_outlet")
    explorer.cmb_database.setCurrentText("analytics")

    assert explorer.layout().indexOf(explorer.cmb_database) < explorer.layout().indexOf(
        explorer.txt_filter
    )
    assert selected == ["analytics"]


def test_loaded_schema_is_expanded_with_direct_table_rows(qtbot):
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)
    explorer.load_schema_model("B2B_OUTLET", create_sample_schema())

    schema = explorer.tree.topLevelItem(0)
    assert schema.isExpanded()
    assert schema.childCount() == 2
    assert "users" in schema.child(0).text(0)
    assert explorer.lbl_entities_count.text() == "2"
```

Add a separate state test asserting that first-load loading/error rows are visible and a refresh
error with `preserve_tree=True` leaves the existing top-level connection unchanged.

- [ ] **Step 2: Run explorer tests and confirm RED**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_database_explorer.py`

Expected: FAIL because the dropdown API and automatic expansion do not exist.

- [ ] **Step 3: Implement selector, states, and automatic expansion**

Store refresh/add buttons as `self.btn_refresh` and `self.btn_add`. Insert a compact `QComboBox` row
between the header and filter, then an `ENTIDADES` heading with a table-count badge above the tree.
Block combo signals while `set_databases()` changes its model. In `load_schema_model()`, create one
top-level item per schema and put table rows directly beneath it; expand the first schema. Assign
QtAwesome database, rotate, plus, filter, folder, and table icons. State rows use
`QTreeWidgetItem([message])`; preserving states do not clear the current model.

- [ ] **Step 4: Run explorer tests and confirm GREEN**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_database_explorer.py`

Expected: all explorer tests pass.

- [ ] **Step 5: Commit the explorer UI unit**

```bash
git add src/backend_ide/ui/explorer/explorer_widget.py tests/test_database_explorer.py
git commit -m "feat: add database selector to explorer"
```

---

### Task 4: Orchestrate profile, database, inspection, and UI state

**Files:**
- Modify: `src/backend_ide/application/connection_service.py`
- Modify: `src/backend_ide/ui/components/connection_selector.py`
- Modify: `src/backend_ide/ui/views/main_window.py`
- Modify: `tests/test_connection_profiles.py`
- Modify: `tests/test_ui_shell.py`

**Interfaces:**
- Extends: `ConnectionService.build_connection(profile, password=None, database_name=None)`.
- Adds: `ConnectionSelector.select_profile(profile_id: str) -> bool`.
- Main-window handlers: `_load_profile(profile)`, `_start_inspection(profile, database_name, discover_databases)`, `_on_inspection_succeeded(result)`, `_on_inspection_failed(message)`, `_on_database_changed(database_name)`, and `_refresh_active_database()`.

- [ ] **Step 1: Write failing service and selector tests**

```python
def test_connection_service_can_build_adapter_for_another_database(temp_repo):
    repo, _ = temp_repo
    profile = ConnectionProfile(name="RDS", engine="postgresql", database="db_outlet")
    adapter = ConnectionService(repo).build_connection(profile, "secret", database_name="analytics")
    assert adapter.config.database == "analytics"
    assert profile.database == "db_outlet"


def test_connection_selector_can_select_saved_profile(temp_repo, qtbot):
    repo, _ = temp_repo
    service = ConnectionService(repo)
    profile = ConnectionProfile(name="B2B_OUTLET", engine="postgresql")
    service.save_profile(profile)
    selector = ConnectionSelector(service)
    qtbot.addWidget(selector)
    assert selector.select_profile(profile.id)
    assert selector.get_selected_profile().id == profile.id
```

- [ ] **Step 2: Write failing main-window integration tests**

Add tests with a fake `SchemaInspectionWorker` factory that records the candidate connection and
allows success/failure signals to be emitted deterministically. Assert:

```python
window._on_inspection_succeeded(
    DatabaseInspectionResult(("analytics", "db_outlet"), create_sample_schema())
)
assert window.explorer_widget.cmb_database.currentText() == "db_outlet"
assert window.explorer_widget.tree.topLevelItemCount() == 1
assert "db_outlet" in window.breadcrumb_bar.lbl_db.text()
assert "Conectado" in window.status_lbl_conn.text()
```

Also assert a database selection builds a candidate for the selected name, a failure restores the
last successful selection/tree, refresh starts one worker, and `closeEvent` disconnects the active
adapter.

- [ ] **Step 3: Run focused integration tests and confirm RED**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_connection_profiles.py tests/test_ui_shell.py`

Expected: FAIL because the override, selection, and inspection orchestration APIs do not exist.

- [ ] **Step 4: Implement service override and selector API**

Use `database_name or profile.database` when constructing `ConnectionConfig`; do not mutate the
profile. Implement `select_profile()` with `findData(profile_id)` and `setCurrentIndex()`.

- [ ] **Step 5: Implement main-window orchestration**

Initialize active/candidate profile, connection, database list, prior database, and worker fields.
Wire `connection_changed`, `database_changed`, and `refresh_requested` after all widgets exist.
After dialog acceptance, refresh/select `dialog.profile` and start discovery. Disable selectors and
refresh while the worker runs. On success, atomically swap connections/model/state, disconnect the
previous adapter, and update breadcrumb/status. On failure, disconnect the candidate, restore the
previous dropdown and tree, expose the error, and re-enable controls. Disconnect the active adapter
in `closeEvent`.

- [ ] **Step 6: Run focused integration tests and confirm GREEN**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q tests/test_connection_profiles.py tests/test_ui_shell.py tests/test_database_explorer.py`

Expected: all focused tests pass.

- [ ] **Step 7: Commit the orchestration unit**

```bash
git add src/backend_ide/application/connection_service.py src/backend_ide/ui/components/connection_selector.py src/backend_ide/ui/views/main_window.py tests/test_connection_profiles.py tests/test_ui_shell.py
git commit -m "feat: load live schemas into database explorer"
```

---

### Task 5: Verify and launch the live flow

**Files:**
- Modify only files required by formatting findings.

**Interfaces:**
- Consumes the completed feature through the desktop entry point.
- Produces a running PySide6 application for user verification.

- [ ] **Step 1: Run formatting and lint verification**

```bash
UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run ruff format --check src tests
UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run ruff check src tests
```

Expected: both commands exit 0 with no findings.

- [ ] **Step 2: Run the full automated suite**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run pytest -q`

Expected: all tests pass with zero failures.

- [ ] **Step 3: Launch and verify the application process**

Run: `UV_CACHE_DIR=/tmp/manejador-db-uv-cache uv run python -m backend_ide.ui.app`

Expected: the process remains running; after selecting the saved profile, the dropdown lists
accessible databases and the explorer visibly contains schemas and tables. Expanding a table loads
its fields through `TableColumnsWorker` and shows native type, `PK`, and `NOT NULL` markers.

- [ ] **Step 4: Commit any verification-only formatting changes**

```bash
git add src tests
git diff --cached --quiet || git commit -m "style: format live explorer integration"
```
