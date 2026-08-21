# Structured Main Window Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the ambiguous abbreviated environment badge with a non-interactive semantic dot and complete Spanish label while preserving the approved main-window hierarchy and responsive layout.

**Architecture:** Add a focused `EnvironmentIndicator` presentation widget beside the existing profile selector. `ConnectionSelector` supplies the selected domain environment, `ThemeManager` supplies semantic colors, and `MainWindow` keeps its existing three-zone toolbar and splitter responsibilities; database services and workers remain unchanged.

**Tech Stack:** Python 3.14, PySide6, pytest, pytest-qt, Ruff, uv

## Execution Note

The integrated implementation keeps the approved behavior while extracting
`EnvironmentIndicator` to `ui/components/environment_indicator.py` as a reusable component.
Semantic colors remain centralized in `ThemeManager` QSS through the indicator's dynamic
`environment` property instead of being applied as inline component styles. The final test names
and visual evidence are recorded in `tests/test_connection_profiles.py`, `tests/test_ui_shell.py`,
and `design-qa.md`.

## Global Constraints

- Keep the initial window size at 1340 × 840 and the supported minimum at 1100 × 700.
- Keep the top bar ordered as connection context, query actions, and theme control.
- Keep connection controls ordered as `Perfil`, selector, environment, `Nueva conexión`, and `Editar`.
- Render environment meaning with a complete Spanish label plus color; never depend on color alone.
- The environment indicator must have no filled background, border, brackets, abbreviation, focus, hover, pressed, menu, or click behavior.
- Use `ThemeManager.current_palette` semantic tokens; do not add hard-coded theme colors.
- Preserve all connection, inspection, query, breadcrumb, explorer, results, and theme contracts.
- Leave `Diagrama ER` visible and disabled.
- Use TDD for every behavior change and keep each task independently reviewable.

---

## File Structure

- Modify `src/backend_ide/ui/components/connection_selector.py`: define the environment presentation widget and connect it to profile selection and theme changes.
- Modify `tests/test_connection_profiles.py`: test localized labels, semantic colors, non-interactivity, empty state, and profile switching.
- Modify `tests/test_ui_shell.py`: update the shell contract from the old badge to the new indicator and protect responsive layout behavior.
- Modify `design-qa.md`: append screenshot evidence and the final visual checklist without replacing prior evidence.

No domain, application-service, storage, database-adapter, worker, or query-execution file changes are required.

---

### Task 1: Non-interactive environment indicator

**Files:**
- Modify: `src/backend_ide/ui/components/connection_selector.py`
- Test: `tests/test_connection_profiles.py`

**Interfaces:**
- Consumes: `Environment`, `ThemeManager.get_instance()`, and `ThemePalette` fields `accent`, `success`, `warning`, `danger`, and `text_muted`.
- Produces: `EnvironmentIndicator.set_environment(environment: Environment | None) -> None`, `EnvironmentIndicator.refresh_palette() -> None`, `EnvironmentIndicator.dot`, and `EnvironmentIndicator.text_label`.

- [x] **Step 1: Write failing tests for complete localized labels and semantic colors**

Add the following import and parameterized test to `tests/test_connection_profiles.py`:

```python
from backend_ide.ui.components.connection_selector import EnvironmentIndicator
from backend_ide.ui.theme import ThemeManager


@pytest.mark.parametrize(
    ("environment", "visible_label", "palette_field"),
    [
        (Environment.DEVELOPMENT, "Desarrollo", "accent"),
        (Environment.TESTING, "Pruebas", "success"),
        (Environment.STAGING, "Preproducción", "warning"),
        (Environment.PRODUCTION, "Producción", "danger"),
    ],
)
def test_environment_indicator_uses_full_label_and_semantic_color(
    qtbot, environment, visible_label, palette_field
):
    indicator = EnvironmentIndicator()
    qtbot.addWidget(indicator)

    indicator.set_environment(environment)

    expected_color = getattr(ThemeManager.get_instance().current_palette, palette_field)
    assert indicator.text_label.text() == visible_label
    assert f"background-color: {expected_color}" in indicator.dot.styleSheet()
```

- [x] **Step 2: Run the label test to verify it fails**

Run:

```bash
uv run pytest tests/test_connection_profiles.py::test_environment_indicator_uses_full_label_and_semantic_color -v
```

Expected: FAIL because `EnvironmentIndicator` does not exist.

- [x] **Step 3: Write failing tests for empty state and non-interactivity**

Append to `tests/test_connection_profiles.py`:

```python
def test_environment_indicator_is_informational_and_has_neutral_empty_state(qtbot):
    indicator = EnvironmentIndicator()
    qtbot.addWidget(indicator)

    indicator.set_environment(None)

    palette = ThemeManager.get_instance().current_palette
    assert indicator.text_label.text() == "Sin entorno"
    assert f"background-color: {palette.text_muted}" in indicator.dot.styleSheet()
    assert indicator.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert indicator.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert "entorno" in indicator.toolTip().lower()
```

- [x] **Step 4: Run the empty-state test to verify it fails**

Run:

```bash
uv run pytest tests/test_connection_profiles.py::test_environment_indicator_is_informational_and_has_neutral_empty_state -v
```

Expected: FAIL because `EnvironmentIndicator` does not exist.

- [x] **Step 5: Implement the minimal environment indicator**

In `src/backend_ide/ui/components/connection_selector.py`, add `QSizePolicy` to the existing widget imports if it is not already present and define this class immediately before `ConnectionSelector`:

```python
class EnvironmentIndicator(QWidget):
    """Read-only environment context rendered as a semantic dot and full label."""

    LABELS = {
        Environment.DEVELOPMENT: "Desarrollo",
        Environment.TESTING: "Pruebas",
        Environment.STAGING: "Preproducción",
        Environment.PRODUCTION: "Producción",
    }
    PALETTE_FIELDS = {
        Environment.DEVELOPMENT: "accent",
        Environment.TESTING: "success",
        Environment.STAGING: "warning",
        Environment.PRODUCTION: "danger",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._environment: Environment | None = None
        self._theme_manager = ThemeManager.get_instance()
        self.setObjectName("environment_indicator")
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.dot = QLabel()
        self.dot.setObjectName("environment_dot")
        self.dot.setFixedSize(8, 8)
        self.text_label = QLabel()
        self.text_label.setObjectName("environment_label")

        layout.addWidget(self.dot)
        layout.addWidget(self.text_label)
        self.set_environment(None)

    def set_environment(self, environment: Environment | None) -> None:
        """Display the selected profile environment without implying connection state."""
        self._environment = environment
        visible_label = self.LABELS.get(environment, "Sin entorno")
        self.text_label.setText(visible_label)
        self.setToolTip(f"Entorno del perfil seleccionado: {visible_label}")
        self.setAccessibleName(f"Entorno del perfil: {visible_label}")
        self.refresh_palette()

    def refresh_palette(self) -> None:
        """Refresh the semantic dot after a theme change."""
        palette = self._theme_manager.current_palette
        palette_field = self.PALETTE_FIELDS.get(self._environment)
        color = getattr(palette, palette_field) if palette_field else palette.text_muted
        self.dot.setStyleSheet(f"background-color: {color}; border: none; border-radius: 4px;")
```

Do not add mouse signals, event handlers, actions, menus, borders, filled container styles, or color literals.

- [x] **Step 6: Run the focused indicator tests**

Run:

```bash
uv run pytest tests/test_connection_profiles.py -k environment_indicator -v
```

Expected: 5 parameter cases PASS: four environments plus the neutral empty state.

- [x] **Step 7: Run lint and commit the focused component**

Run:

```bash
uv run ruff check src/backend_ide/ui/components/connection_selector.py tests/test_connection_profiles.py
git diff --check
```

Expected: both commands PASS.

Commit:

```bash
git add src/backend_ide/ui/components/connection_selector.py tests/test_connection_profiles.py
git commit -m "feat: add semantic environment indicator"
```

---

### Task 2: Connection selector integration and responsive shell contract

**Files:**
- Modify: `src/backend_ide/ui/components/connection_selector.py`
- Modify: `tests/test_connection_profiles.py`
- Modify: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: `EnvironmentIndicator.set_environment(environment: Environment | None) -> None` and `EnvironmentIndicator.refresh_palette() -> None` from Task 1.
- Produces: `ConnectionSelector.env_indicator: EnvironmentIndicator`; selected profiles update it through the existing `_on_connection_changed(index: int) -> None` path.

- [x] **Step 1: Write a failing profile-switching integration test**

Append to `tests/test_connection_profiles.py`:

```python
def test_connection_selector_updates_environment_when_profile_changes(temp_repo, qtbot):
    repo, _ = temp_repo
    service = ConnectionService(repo)
    development = ConnectionProfile(
        name="Development DB", engine="postgresql", environment=Environment.DEVELOPMENT
    )
    production = ConnectionProfile(
        name="Production DB", engine="postgresql", environment=Environment.PRODUCTION
    )
    service.save_profile(development)
    service.save_profile(production)
    selector = ConnectionSelector(service)
    qtbot.addWidget(selector)

    assert selector.select_profile(production.id)

    assert selector.env_indicator.text_label.text() == "Producción"
    assert selector.env_indicator.focusPolicy() == Qt.FocusPolicy.NoFocus
```

- [x] **Step 2: Update shell tests to express the approved control order**

In `tests/test_ui_shell.py`, replace both references to `window.conn_selector.env_badge` with `window.conn_selector.env_indicator`. In `test_connection_controls_follow_context_then_actions`, keep the exact expected sequence:

```python
assert widgets == [
    window.conn_selector.lbl_profile,
    window.conn_selector.combo,
    window.conn_selector.env_indicator,
    window.conn_selector.btn_new,
    window.conn_selector.btn_edit,
]
```

Add these assertions to `test_documented_window_sizes_have_no_clipped_toolbar_controls` after the geometry overlap checks:

```python
assert window.conn_selector.env_indicator.text_label.text() in {
    "Desarrollo",
    "Pruebas",
    "Preproducción",
    "Producción",
}
assert window.conn_selector.env_indicator.width() > 8
```

- [x] **Step 3: Run the integration and shell tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_connection_profiles.py::test_connection_selector_updates_environment_when_profile_changes \
  tests/test_ui_shell.py::test_connection_controls_follow_context_then_actions \
  tests/test_ui_shell.py::test_documented_window_sizes_have_no_clipped_toolbar_controls -v
```

Expected: FAIL because `ConnectionSelector` still exposes and updates `env_badge`.

- [x] **Step 4: Replace the old badge with the new indicator**

In `ConnectionSelector.__init__`, replace the old `env_badge` creation with:

```python
self.env_indicator = EnvironmentIndicator()
```

Replace the layout insertion with:

```python
layout.addWidget(self.env_indicator, alignment=Qt.AlignmentFlag.AlignVCenter)
```

Remove `_update_badge_style`. At the end of `_update_action_icons`, refresh the indicator instead:

```python
self.env_indicator.refresh_palette()
```

Replace `_on_connection_changed` with:

```python
def _on_connection_changed(self, index: int) -> None:
    """Update environment context and emit the selected profile."""
    profile = self.get_selected_profile()
    if profile is None:
        self.env_indicator.set_environment(None)
        return

    self.env_indicator.set_environment(profile.environment)
    self.connection_changed.emit(profile.id)
```

Do not use `profile.color`: the approved indicator uses semantic environment colors from the active theme.

- [x] **Step 5: Run focused connection and shell tests**

Run:

```bash
uv run pytest tests/test_connection_profiles.py tests/test_ui_shell.py -v
```

Expected: all tests PASS, including profile switching, control order, theme behavior, and both documented window sizes.

- [x] **Step 6: Format, lint, and commit the integration**

Run:

```bash
uv run ruff format src/backend_ide/ui/components/connection_selector.py tests/test_connection_profiles.py tests/test_ui_shell.py
uv run ruff check src/backend_ide/ui/components/connection_selector.py tests/test_connection_profiles.py tests/test_ui_shell.py
git diff --check
```

Expected: all commands PASS.

Commit:

```bash
git add src/backend_ide/ui/components/connection_selector.py tests/test_connection_profiles.py tests/test_ui_shell.py
git commit -m "refactor: clarify connection environment context"
```

---

### Task 3: Visual QA, regression verification, and PR update preparation

**Files:**
- Modify: `design-qa.md`
- Modify: `docs/superpowers/plans/2026-08-14-structured-main-window-hierarchy.md`

**Interfaces:**
- Consumes: the integrated main window from Task 2.
- Produces: four visual QA captures, documented outcomes, a fully checked plan, and a clean verified branch ready to push to the existing PR.

- [x] **Step 1: Capture the four approved viewport and theme combinations**

Use the existing PySide6 screenshot harness pattern from `docs/superpowers/plans/2026-08-14-balanced-window-layout.md`. Produce these exact files:

```text
/tmp/manejador-db-structured-dark-1340x840.png
/tmp/manejador-db-structured-dark-1100x700.png
/tmp/manejador-db-structured-light-1340x840.png
/tmp/manejador-db-structured-light-1100x700.png
```

For each capture, set the requested `ThemeMode`, resize the window, show it, call `app.processEvents()`, and save `window.grab()` to the matching path.

- [x] **Step 2: Inspect every screenshot against the approved design**

Use the local image viewer on all four files. Confirm every item explicitly:

```text
- The top bar remains a single compact row with left, center, and right groups.
- The environment reads as a dot plus a complete Spanish name.
- The environment has no filled container, border, brackets, or button silhouette.
- Profile, environment, connection actions, query actions, and theme do not overlap.
- The breadcrumb remains a distinct context row.
- Explorer, editor, and results remain readable at both viewport sizes.
- Light and dark themes preserve contrast and semantic dot colors.
```

If any item fails, add a focused failing regression test, make the smallest correction in the owning component, rerun the focused tests, and repeat all four captures before proceeding.

- [x] **Step 3: Append the visual evidence to `design-qa.md`**

Add a section named `## Jerarquía estructurada e indicador de entorno` containing:

```markdown
### Evidencia

- Oscuro, tamaño inicial: `/tmp/manejador-db-structured-dark-1340x840.png`.
- Oscuro, tamaño mínimo: `/tmp/manejador-db-structured-dark-1100x700.png`.
- Claro, tamaño inicial: `/tmp/manejador-db-structured-light-1340x840.png`.
- Claro, tamaño mínimo: `/tmp/manejador-db-structured-light-1100x700.png`.

### Resultado

- La barra superior conserva los tres grupos funcionales aprobados.
- El entorno usa punto semántico y nombre completo, sin apariencia interactiva.
- Los cuatro tamaños y temas conservan contexto, acciones y área de trabajo sin solapamientos.
- La barra de estado sigue siendo la fuente del estado real de conexión.
```

Record any discovered limitation instead of claiming it does not exist.

- [x] **Step 4: Run the complete verification suite**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
git diff --check
```

Expected: the full test suite passes, Ruff reports no violations or formatting changes, both distribution artifacts build successfully, and Git reports no whitespace errors.

- [x] **Step 5: Mark this plan complete and commit QA evidence**

Change every completed checkbox in this plan from `[ ]` to `[x]`, then run:

```bash
git add design-qa.md docs/superpowers/plans/2026-08-14-structured-main-window-hierarchy.md
git commit -m "docs: verify structured window hierarchy"
git status --short
```

Expected: the commit succeeds. Only `.superpowers/` may remain as local visual-companion state; it must not be staged or committed.

- [x] **Step 6: Verify publication scope before updating the existing PR**

Run:

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git status -sb
```

Expected: the branch contains the documented window work, semantic environment indicator, tests, and QA evidence; it tracks `origin/feat/documented-window-layout`; no product source or documentation change is unstaged.
