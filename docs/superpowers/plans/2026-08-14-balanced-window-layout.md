# Balanced Window Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the complete current desktop window into documented functional groups, finish the required three-mode theme control, and verify the result at normal and minimum sizes without changing database behavior.

**Architecture:** Keep UI composition inside the existing PySide6 presentation components and preserve every service, signal, worker, and domain contract. `ThemeManager` owns appearance resolution and persistence; `ThemeToggleButton`, `ConnectionSelector`, `DatabaseExplorerWidget`, `ResultsWidget`, and `MainWindow` own only their local presentation responsibilities.

**Tech Stack:** Python 3.14, PySide6/Qt 6, QtAwesome, QSettings, pytest, pytest-qt, Ruff

## Global Constraints

- The application remains a native PySide6 desktop application for Windows, Linux, and macOS.
- The UI contains no database-engine-specific business logic and performs no database operation on the Qt UI thread.
- The initial window is 1340 × 840 px and the minimum supported window is 1100 × 700 px.
- The explorer starts at 340 px and cannot shrink below 280 px.
- Editor/results initial allocation is 65/35 with minimum heights of 240/180 px.
- Toolbar controls are 32 px high; spacing uses 4/8/12 px increments.
- `Ejecutar` is the only visually primary action.
- System, Light, and Dark modes are available; the selected mode persists with `QSettings`.
- Touched components use centralized tokens/QSS and QtAwesome icons, not hard-coded presentation colors or emoji actions.
- Unimplemented product actions are disabled rather than presented as working controls.

---

### Task 1: Persisted three-mode theme manager

**Files:**
- Modify: `src/backend_ide/ui/theme/manager.py`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: `ThemeMode`, `DARK_PALETTE`, `LIGHT_PALETTE`, `QApplication.styleHints()`.
- Produces: `ThemeManager(settings: QSettings | None = None)`, `resolved_mode`, `set_mode(mode: ThemeMode, *, persist: bool = True)`, and `toggle_theme()`.

- [x] **Step 1: Write failing tests for persistence and system resolution**

Add imports for `QSettings` and the palettes, then add:

```python
def test_theme_manager_persists_all_documented_modes(qapp, tmp_path):
    settings_path = tmp_path / "theme.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    manager = ThemeManager(settings=settings)

    for mode in (ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK):
        manager.set_mode(mode)
        assert manager.current_mode == mode
        assert settings.value("appearance/theme") == mode.value

    restored = ThemeManager(settings=QSettings(str(settings_path), QSettings.Format.IniFormat))
    assert restored.current_mode == ThemeMode.DARK


def test_system_theme_resolves_to_a_concrete_palette(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "system.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(settings=settings)

    manager.set_mode(ThemeMode.SYSTEM)

    assert manager.current_mode == ThemeMode.SYSTEM
    assert manager.resolved_mode in (ThemeMode.LIGHT, ThemeMode.DARK)
    expected = LIGHT_PALETTE if manager.resolved_mode == ThemeMode.LIGHT else DARK_PALETTE
    assert manager.current_palette == expected
```

- [x] **Step 2: Run the tests and verify failure**

Run: `uv run pytest tests/test_ui_shell.py -k 'theme_manager_persists or system_theme_resolves' -v`

Expected: FAIL because `ThemeManager` does not accept settings, does not preserve `SYSTEM`, and has no `resolved_mode`.

- [x] **Step 3: Implement settings, selected mode, and resolved mode**

Implement this shape in `ThemeManager`:

```python
SETTINGS_KEY = "appearance/theme"

def __init__(self, settings: QSettings | None = None) -> None:
    super().__init__()
    self._settings = settings or QSettings("BackendIDE", "BackendIDE")
    saved = self._settings.value(self.SETTINGS_KEY, ThemeMode.SYSTEM.value, type=str)
    try:
        self._mode = ThemeMode(saved)
    except ValueError:
        self._mode = ThemeMode.SYSTEM
    self._resolved_mode = self._resolve_mode(self._mode)
    self._palette = self._palette_for(self._resolved_mode)

@property
def resolved_mode(self) -> ThemeMode:
    return self._resolved_mode

def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
    if mode != ThemeMode.SYSTEM:
        return mode
    scheme = QApplication.styleHints().colorScheme()
    return ThemeMode.LIGHT if scheme == Qt.ColorScheme.Light else ThemeMode.DARK

def _palette_for(self, mode: ThemeMode) -> ThemePalette:
    return LIGHT_PALETTE if mode == ThemeMode.LIGHT else DARK_PALETTE

def set_mode(self, mode: ThemeMode, *, persist: bool = True) -> None:
    self._mode = mode
    self._resolved_mode = self._resolve_mode(mode)
    self._palette = self._palette_for(self._resolved_mode)
    if persist:
        self._settings.setValue(self.SETTINGS_KEY, mode.value)
        self._settings.sync()
    self.apply_theme()
    self.theme_changed.emit(mode.value)

def toggle_theme(self) -> ThemeMode:
    new_mode = ThemeMode.LIGHT if self._resolved_mode == ThemeMode.DARK else ThemeMode.DARK
    self.set_mode(new_mode)
    return new_mode
```

Connect `QApplication.styleHints().colorSchemeChanged` once so a selected `SYSTEM` mode reapplies the resolved palette when the OS appearance changes.

- [x] **Step 4: Run focused and existing theme tests**

Run: `uv run pytest tests/test_ui_shell.py -k theme -v`

Expected: PASS, including the existing text-button quick-toggle test, which remains compatible until Task 2 replaces that component.

- [x] **Step 5: Commit the theme manager**

```bash
git add src/backend_ide/ui/theme/manager.py tests/test_ui_shell.py
git commit -m "feat: persist system light and dark themes"
```

---

### Task 2: Compact documented theme control

**Files:**
- Modify: `src/backend_ide/ui/components/theme_toggle.py`
- Modify: `src/backend_ide/ui/theme/manager.py`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: `ThemeManager.current_mode`, `ThemeManager.current_palette`, `ThemeManager.set_mode()`, `ThemeManager.toggle_theme()`.
- Produces: `ThemeToggleButton(QToolButton)` with a main quick-toggle action and a menu containing one checkable action per `ThemeMode`.

- [x] **Step 1: Write failing interaction tests**

Replace the text-based toggle test with:

```python
def test_theme_control_exposes_system_light_and_dark(app_instance, qtbot):
    _, window = app_instance
    qtbot.addWidget(window)
    manager = ThemeManager.get_instance()
    manager.set_mode(ThemeMode.SYSTEM)

    assert window.theme_toggle.height() == 32
    assert [action.data() for action in window.theme_toggle.menu().actions()] == [
        ThemeMode.SYSTEM,
        ThemeMode.LIGHT,
        ThemeMode.DARK,
    ]

    dark_action = next(
        action for action in window.theme_toggle.menu().actions() if action.data() == ThemeMode.DARK
    )
    dark_action.trigger()
    assert manager.current_mode == ThemeMode.DARK
    assert dark_action.isChecked()

    qtbot.mouseClick(window.theme_toggle, Qt.MouseButton.LeftButton)
    assert manager.current_mode == ThemeMode.LIGHT
```

- [x] **Step 2: Run the interaction test and verify failure**

Run: `uv run pytest tests/test_ui_shell.py::test_theme_control_exposes_system_light_and_dark -v`

Expected: FAIL because the current control is a text-only `QPushButton` with no menu.

- [x] **Step 3: Implement the split theme tool button**

Change the component to `QToolButton`, set `MenuButtonPopup`, a fixed 32 × 32 size, and a `QMenu` with `Sistema`, `Claro`, and `Oscuro`. Store `ThemeMode` in each action's `data`, make the actions checkable, and call `ThemeManager.set_mode(action.data())` when triggered. The main button calls `toggle_theme()`.

Use these QtAwesome icons:

```python
MODE_ICONS = {
    ThemeMode.SYSTEM: "fa6s.desktop",
    ThemeMode.LIGHT: "fa6s.sun",
    ThemeMode.DARK: "fa6s.moon",
}
```

On `theme_changed`, refresh the button icon using `current_palette.text_primary`, update the tooltip to name the selected mode, and check exactly one menu action.

- [x] **Step 4: Centralize QToolButton styling**

Extend the global button selectors in `ThemeManager.generate_stylesheet()` from `QPushButton` to `QPushButton, QToolButton`. Add `QToolButton#theme_toggle_btn` and `QToolButton#icon_button` rules using palette tokens; do not add inline style sheets to the component.

- [x] **Step 5: Run the theme tests**

Run: `uv run pytest tests/test_ui_shell.py -k theme -v`

Expected: PASS.

- [x] **Step 6: Commit the theme control**

```bash
git add src/backend_ide/ui/components/theme_toggle.py src/backend_ide/ui/theme/manager.py tests/test_ui_shell.py
git commit -m "feat: add compact three-mode theme control"
```

---

### Task 3: Three-zone top bar and adaptive connection group

**Files:**
- Modify: `src/backend_ide/ui/views/main_window.py`
- Modify: `src/backend_ide/ui/components/connection_selector.py`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: existing connection/query signals and slots without signature changes.
- Produces: `MainWindow.top_bar`, `MainWindow.query_toolbar`, `MainWindow.btn_new_query`, `MainWindow.btn_er_diagram`, `MainWindow.main_splitter`, and `MainWindow.workspace_splitter` for stable UI tests.

- [x] **Step 1: Write failing structure and resize tests**

Add:

```python
def test_top_bar_groups_controls_by_documented_function(app_instance, qtbot):
    app, window = app_instance
    qtbot.addWidget(window)
    window.show()
    app.processEvents()

    assert window.minimumSize().width() == 1100
    assert window.minimumSize().height() == 700
    assert window.top_bar.layout().columnCount() == 3
    assert window.top_bar.layout().itemAtPosition(0, 0).widget() is window.conn_selector
    assert window.top_bar.layout().itemAtPosition(0, 1).widget() is window.query_toolbar
    assert window.top_bar.layout().itemAtPosition(0, 2).widget() is window.theme_toggle
    assert window.btn_execute.height() == 32
    assert window.btn_new_query.height() == 32
    assert window.btn_er_diagram.height() == 32
    assert not window.btn_er_diagram.isEnabled()


def test_connection_controls_follow_context_then_actions(app_instance, qtbot):
    _, window = app_instance
    qtbot.addWidget(window)
    layout = window.conn_selector.layout()
    widgets = [layout.itemAt(index).widget() for index in range(layout.count())]
    assert widgets == [
        window.conn_selector.lbl_profile,
        window.conn_selector.combo,
        window.conn_selector.env_badge,
        window.conn_selector.btn_new,
        window.conn_selector.btn_edit,
    ]
    assert window.conn_selector.combo.minimumWidth() == 180
```

- [x] **Step 2: Run the new tests and verify failure**

Run: `uv run pytest tests/test_ui_shell.py -k 'top_bar_groups or connection_controls_follow' -v`

Expected: FAIL because the top bar uses `QHBoxLayout`, the local controls are not exposed, and connection actions precede context.

- [x] **Step 3: Implement the adaptive connection group**

In `ConnectionSelector`, expose `self.lbl_profile`, order the widgets as profile label → expanding combo → environment badge → new → edit, reduce the combo minimum width from 220 to 180, and apply `QSizePolicy.Expanding, Fixed`. Set all interactive controls to 32 px high.

Replace emoji text with `Nueva conexión` and `Editar`, and use QtAwesome `fa6s.plug-circle-plus` and `fa6s.pen-to-square` icons. Keep the existing signals, profile data, environment badge, and tooltips.

- [x] **Step 4: Implement the three-column top bar**

In `MainWindow._setup_ui()`:

```python
self.setMinimumSize(1100, 700)
self.top_bar = QWidget()
self.top_bar.setObjectName("top_bar")
top_layout = QGridLayout(self.top_bar)
top_layout.setContentsMargins(12, 8, 12, 8)
top_layout.setHorizontalSpacing(12)
top_layout.setColumnStretch(0, 1)
top_layout.setColumnStretch(1, 0)
top_layout.setColumnStretch(2, 1)
```

Expose the query group and secondary buttons as attributes. Use QtAwesome `fa6s.play`, `fa6s.file-circle-plus`, and `fa6s.diagram-project`. Disable `btn_er_diagram` until its documented flow exists. Add connection, query, and theme widgets at columns 0, 1, and 2 with left, center, and right alignment respectively.

Expose the two splitters, set the explorer minimum width to 280, set horizontal sizes to `[340, 1000]`, set stretch factors to `0/1`, and make children non-collapsible. Set vertical sizes to `[455, 245]`, stretch factors to `13/7`, and minimum heights to 240/180.

- [x] **Step 5: Run all shell tests**

Run: `uv run pytest tests/test_ui_shell.py -v`

Expected: PASS.

- [x] **Step 6: Commit the top bar layout**

```bash
git add src/backend_ide/ui/views/main_window.py src/backend_ide/ui/components/connection_selector.py tests/test_ui_shell.py
git commit -m "feat: group top bar actions by workflow"
```

---

### Task 4: Dense explorer header and aligned results actions

**Files:**
- Modify: `src/backend_ide/ui/explorer/explorer_widget.py`
- Modify: `src/backend_ide/ui/results/results_widget.py`
- Modify: `src/backend_ide/ui/components/breadcrumb.py`
- Modify: `src/backend_ide/ui/theme/manager.py`
- Test: `tests/test_database_explorer.py`
- Test: `tests/test_query_execution.py`

**Interfaces:**
- Consumes: existing explorer and results signals, result models, and export service.
- Produces: `DatabaseExplorerWidget.header`, `DatabaseExplorerWidget.lbl_title`, `DatabaseExplorerWidget.entities_row` removed, and `ResultsWidget.action_bar` with stable child order.

- [x] **Step 1: Write failing explorer layout test**

Add:

```python
def test_explorer_header_contains_summary_and_compact_actions(qtbot):
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)
    header_layout = explorer.header.layout()
    widgets = [header_layout.itemAt(index).widget() for index in range(header_layout.count())]

    assert explorer.lbl_title in widgets
    assert explorer.lbl_entities_count in widgets
    assert explorer.btn_refresh in widgets
    assert explorer.btn_add in widgets
    assert explorer.btn_refresh.size().toTuple() == (32, 32)
    assert explorer.btn_add.size().toTuple() == (32, 32)
    assert explorer.minimumWidth() == 280
```

- [x] **Step 2: Write failing results layout test**

Add:

```python
def test_results_actions_are_aligned_and_emoji_free(qtbot):
    results = ResultsWidget()
    qtbot.addWidget(results)
    layout = results.action_bar.layout()

    assert layout.itemAt(0).widget() is results.lbl_stats
    assert layout.itemAt(layout.count() - 2).widget() is results.txt_filter_grid
    assert layout.itemAt(layout.count() - 1).widget() is results.btn_export
    assert results.txt_filter_grid.height() == 32
    assert results.btn_export.height() == 32
    assert "📥" not in results.btn_export.text()
```

- [x] **Step 3: Run both tests and verify failure**

Run: `uv run pytest tests/test_database_explorer.py::test_explorer_header_contains_summary_and_compact_actions tests/test_query_execution.py::test_results_actions_are_aligned_and_emoji_free -v`

Expected: FAIL because header/action widgets are local, explorer actions are in the database row, and results still use emoji text.

- [x] **Step 4: Consolidate the explorer header**

Expose `self.header` and `self.lbl_title`. Move `lbl_entities_count`, `btn_refresh`, and `btn_add` into the header. Leave only `cmb_database` in `database_row`; retain `database_row` so the existing order test remains valid. Set the widget minimum width to 280, compact buttons to 32 × 32, object name both as `icon_button`, and remove inline color style sheets.

Use `ThemeManager.current_palette` when generating QtAwesome icons and refresh them on `theme_changed`. Replace state-label inline colors with a dynamic `status` property (`loading` or `error`) and QSS selectors in `ThemeManager`.

- [x] **Step 5: Align and clean the results toolbar**

Expose `self.action_bar`, set filter and export controls to 32 px, and retain status → stretch → filter → export order. Replace emoji placeholders/actions/tabs with QtAwesome icons:

```python
self.txt_filter_grid.setPlaceholderText("Filtrar resultados…")
self.btn_export.setText("Exportar")
act_csv.setIcon(qta.icon("fa6s.file-csv"))
act_json.setIcon(qta.icon("fa6s.file-code"))
self.results_tabs.addTab(self.table_view, qta.icon("fa6s.table"), "Datos")
self.results_tabs.addTab(self.txt_messages, qta.icon("fa6s.rectangle-list"), "Mensajes")
```

Remove emoji prefixes from status and message strings without changing their information.

- [x] **Step 6: Centralize touched component styles**

Add QSS rules for `#sidebar_title`, `#section_label`, `#count_badge`, `QLabel[status="loading"]`, and `QLabel[status="error"]` using theme tokens. Replace inline breadcrumb colors with object names and QSS rules; remove decorative emoji from breadcrumb labels while preserving connection/database/schema text.

- [x] **Step 7: Run explorer, result, and shell tests**

Run: `uv run pytest tests/test_database_explorer.py tests/test_query_execution.py tests/test_ui_shell.py -v`

Expected: PASS.

- [x] **Step 8: Commit panel layout changes**

```bash
git add src/backend_ide/ui/explorer/explorer_widget.py src/backend_ide/ui/results/results_widget.py src/backend_ide/ui/components/breadcrumb.py src/backend_ide/ui/theme/manager.py tests/test_database_explorer.py tests/test_query_execution.py
git commit -m "feat: align explorer and results controls"
```

---

### Task 5: Full requirement and visual verification

**Files:**
- Modify: `design-qa.md`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: the complete reorganized UI and the traceability matrix in `docs/superpowers/specs/2026-08-14-balanced-window-layout-design.md`.
- Produces: automated size/regression evidence plus dark/light screenshots at both required window sizes.

- [ ] **Step 1: Add final minimum-size geometry test**

Add:

```python
@pytest.mark.parametrize("size", [(1340, 840), (1100, 700)])
def test_documented_window_sizes_have_no_clipped_toolbar_controls(app_instance, qtbot, size):
    app, window = app_instance
    qtbot.addWidget(window)
    window.resize(*size)
    window.show()
    app.processEvents()

    top_rect = window.top_bar.rect()
    for control in (
        window.conn_selector,
        window.query_toolbar,
        window.theme_toggle,
    ):
        rect = control.geometry()
        assert top_rect.contains(rect.topLeft())
        assert top_rect.contains(rect.bottomRight())
        assert control.isVisible()
```

- [ ] **Step 2: Run all automated checks**

Run: `uv run pytest`

Expected: all tests PASS.

Run: `uv run ruff check .`

Expected: no diagnostics.

Run: `uv run ruff format --check .`

Expected: all files already formatted.

- [ ] **Step 3: Capture the required visual states**

Start the application offscreen with `auto_load_profile=False`, set each of `ThemeMode.DARK` and `ThemeMode.LIGHT`, render at 1340 × 840 and 1100 × 700, and save:

```text
/tmp/manejador-db-layout-dark-1340x840.png
/tmp/manejador-db-layout-dark-1100x700.png
/tmp/manejador-db-layout-light-1340x840.png
/tmp/manejador-db-layout-light-1100x700.png
```

Use this Qt capture program from the shell:

```bash
QT_QPA_PLATFORM=offscreen uv run python - <<'PY'
from backend_ide.ui.app import create_app
from backend_ide.ui.theme import ThemeManager, ThemeMode

app, window = create_app([], auto_load_profile=False)
manager = ThemeManager.get_instance()
for mode in (ThemeMode.DARK, ThemeMode.LIGHT):
    manager.set_mode(mode)
    for width, height in ((1340, 840), (1100, 700)):
        window.resize(width, height)
        window.show()
        app.processEvents()
        path = f"/tmp/manejador-db-layout-{mode.value}-{width}x{height}.png"
        assert window.grab().save(path)
window.close()
PY
```

Open all four images and inspect: three-zone top alignment, no clipping, 340 px explorer at initial size, compact explorer header, editor/results 65/35 balance, readable status bar, and correct light/dark contrast.

- [ ] **Step 4: Update visual evidence**

Append a `Distribución completa de ventana` section to `design-qa.md` containing the four screenshot paths, viewport sizes, and checklist outcome. State `Sin limitaciones visuales conocidas` only if all four captures pass inspection; otherwise record and fix each concrete defect before continuing. Do not overwrite the prior explorer evidence.

- [ ] **Step 5: Commit verification evidence**

```bash
git add tests/test_ui_shell.py design-qa.md
git commit -m "test: verify balanced window layout"
```

- [ ] **Step 6: Audit the implementation against every acceptance criterion**

For each row in the design traceability table, cite one automated test, source location, or opened screenshot. Treat missing evidence as incomplete work and fix it before publication.

- [ ] **Step 7: Prepare publication**

Confirm the feature branch contains only the design, plan, implementation, tests, and QA evidence. Then use the GitHub publication workflow requested by the user to push the branch and open a pull request; do not merge it.
