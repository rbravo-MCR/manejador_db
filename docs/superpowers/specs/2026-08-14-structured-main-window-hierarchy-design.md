# Structured Main Window Hierarchy Design

**Date:** 2026-08-14

**Status:** Approved for implementation planning

## Goal

Make the main window read as a coherent database workspace and remove the ambiguity that makes the current environment badge look like an actionable button. Preserve the existing database connection, schema inspection, query execution, and theme behavior.

## Scope

This change refines the visual hierarchy and presentation behavior of the entire main window. It changes the connection environment indicator and verifies that the surrounding top bar, context bar, explorer, editor, results area, and status bar retain clear responsibilities.

It does not add new database features, enable the ER diagram action, change connection lifecycle rules, or alter query execution services.

## Selected Direction

The selected layout is a balanced, single-row top bar with three functional groups:

1. Connection context on the left.
2. Query actions in the center.
3. Theme control on the right.

The selected environment treatment is a small semantic color dot followed by the complete localized environment name, such as `● Desarrollo`. It is plain informational text, not a button or outlined chip.

## Window Hierarchy

The window is organized from global context to detailed work:

1. **Top bar** — connection context, query actions, and appearance control.
2. **Context bar** — active profile, database, and schema breadcrumb.
3. **Main workspace** — database explorer beside the SQL editor and results.
4. **Status bar** — current connection state and Python version.

### Top bar

The connection group uses this order:

`Perfil` → profile selector → environment indicator → `Nueva conexión` → `Editar`

The query group uses this order:

`Ejecutar` → `Nueva consulta` → disabled `Diagrama ER`

The theme selector remains right-aligned. Buttons retain both an icon and a text label. The environment indicator has no hover, pressed, focus, menu, or click behavior.

### Context bar

The breadcrumb continues to show profile, active database, and schema. It remains visually separate from global commands so the user can distinguish current location from available actions.

### Main workspace

The database explorer remains on the left with a useful minimum width. The right side keeps the SQL editor above results and messages. The initial vertical allocation remains approximately 65 percent for editing and 35 percent for results.

### Status bar

The status bar remains the authoritative location for connection progress, success, and failure messages. The environment indicator classifies the selected profile; it does not independently claim that the connection succeeded.

## Environment Indicator

The indicator is implemented as a non-interactive label composed visually of:

- an 8-pixel semantic color dot;
- the complete Spanish environment name;
- normal interface text color for the name;
- no filled background, border, brackets, abbreviation, or button styling.

Environment labels and dot colors are:

| Domain value | Visible label | Semantic color |
| --- | --- | --- |
| `development` | `Desarrollo` | Accent blue |
| `testing` | `Pruebas` | Success green |
| `staging` | `Preproducción` | Warning amber |
| `production` | `Producción` | Danger red |

When no profile is selected, the indicator shows `Sin entorno` with the muted neutral color. A production indicator warns through its red dot only and remains non-interactive.

## Component Responsibilities

`ConnectionSelector` owns profile selection, connection-management action signals, and rendering the selected profile's environment. The environment mapping is explicit and local to this presentation component.

`MainWindow` owns the four-level window hierarchy and the layout proportions. It continues to coordinate profile changes with connection loading, breadcrumb updates, explorer state, and the status bar.

`ThemeManager` remains the source of semantic palette colors. The connection component consumes those tokens and must not introduce hard-coded theme colors.

Database services, inspection workers, and query services retain their current contracts and behavior.

## State Flow

1. The profile selector emits the selected profile identifier.
2. `ConnectionSelector` immediately updates the environment label from the selected profile metadata.
3. `MainWindow` begins the existing asynchronous connection and inspection flow.
4. Until that flow completes, the existing workspace remains visible and the status bar communicates progress.
5. On success, the breadcrumb, explorer, and status bar reflect the active database context.
6. On failure, the status bar reports the failure. The environment label continues to describe the selected profile, not connection success.

## Responsive Behavior

The supported minimum window size remains 1100 × 700 and the initial size remains 1340 × 840.

At narrower supported widths, the profile selector yields horizontal space before the main workspace is compressed. The primary query actions and theme control remain visible. The explorer keeps its useful minimum width, while the main horizontal splitter gives remaining space to the editor and results workspace.

## Accessibility and Clarity

The full environment name avoids unexplained abbreviations such as `[DEVE]`. The colored dot is supplemental; meaning does not depend on color alone. The label does not accept keyboard focus and has an explanatory tooltip identifying it as the selected profile's environment.

Interactive controls keep icons, text, tooltips, focus behavior, and disabled-state styling. Informational text does not use the same filled background treatment as primary or secondary buttons.

## Validation

Automated tests will verify:

- every environment value maps to the complete Spanish label;
- semantic colors come from the active theme palette;
- the environment indicator is a non-interactive label without button behavior;
- the connection controls retain the approved order;
- profile changes update the environment indicator;
- the top bar groups remain in their approved left, center, and right positions;
- minimum window dimensions and editor/results proportions remain valid;
- existing connection, explorer, query, and theme tests continue to pass.

Visual QA will cover light and dark themes at 1340 × 840 and 1100 × 700. Final verification will run the full test suite, Ruff linting, Ruff formatting verification, package build, and Git whitespace checks before the existing pull request is updated.
