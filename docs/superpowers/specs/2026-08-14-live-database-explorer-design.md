# Live Database Explorer Design

## Goal

After a PostgreSQL profile is tested and saved, discover the databases that its user may connect
to and automatically inspect the active database. Populate the desktop Database Explorer with the
real connection, selected database, schemas, and tables. A database dropdown above the explorer
filter lets the user switch databases without creating duplicate profiles.

## User Experience

The successful flow is:

1. The user opens **Nueva Conexión**, enters the profile, tests it, and saves it.
2. The main window selects the saved profile and immediately shows **Cargando estructura…**.
3. Database discovery and inspection run outside the Qt UI thread.
4. A **Base de datos** dropdown appears below the `DATABASE EXPLORER` title and above its filter.
5. The dropdown selects the database stored in the profile and lists every non-template database
   for which the PostgreSQL user has `CONNECT` privilege.
6. The explorer renders `Connection → Database → Schema → Tables → Table` from live metadata.
7. The connection, database, first schema, and tables group are expanded so the result is visible
   without another click.
8. The breadcrumb and status bar use the real selected profile, database, and schema instead of
   the current hard-coded local PostgreSQL labels.

Selecting another database creates a temporary adapter using the same profile host, port, user,
password, and SSL mode with only the database name replaced. A successful switch replaces the
active connection and tree. A failed switch restores the previous dropdown selection, connection,
and tree. Database switching never creates or modifies a saved profile.

The existing refresh action repeats the inspection for the active profile. During the first load,
the tree shows a loading row. During later refreshes, the old tree remains visible. The profile
selector and refresh control are disabled until inspection finishes, preventing duplicate work or
a mismatch between the selected profile and displayed metadata.

## Architecture

`MainWindow` owns the active profile, selected database name, active `DatabaseConnection`, and
current inspection worker. On an accepted connection dialog, it refreshes and selects the saved
profile, builds the connection through `ConnectionService`, and starts asynchronous discovery and
inspection.

A focused `SchemaInspectionWorker` receives a candidate database connection and uses
`PostgreSQLInspector.list_databases()` plus `inspect_database()`. It emits a result containing the
accessible database names and `DatabaseSchema`, or a sanitized error message. On later dropdown
switches it reuses the known database list and inspects only the newly selected database. The
worker never reads UI widgets and never mutates the explorer directly.

On success, `MainWindow` passes the model to `DatabaseExplorerWidget.load_schema_model()`, updates
the database dropdown, breadcrumb, and status, and retains the active connection for later
real-query integration. A candidate connection does not replace the current connection until its
inspection succeeds. On profile change, the previous adapter is disconnected after the new model
loads. Closing the window also disconnects it.

## Component Changes

### Connection selector

Add a method to select a profile by ID after its list is refreshed. Profile changes request a live
schema load rather than merely repainting the environment badge.

### Schema inspection worker

Add a Qt `QRunnable` with success and failure signals. It connects lazily through the existing
PostgreSQL adapter, invokes the existing inspector, and leaves the successfully opened connection
available to the main window. Failures disconnect the adapter and return an actionable message.

### PostgreSQL inspector

Add `list_databases()` using `pg_database`, excluding templates and databases that disallow
connections or for which the current user lacks `CONNECT` privilege. Results are ordered by name
and always include the current database when PostgreSQL reports it as connectable.

### Database Explorer

Add the **Base de datos** dropdown between the explorer title and filter, plus explicit loading,
empty, and error presentations inside the tree. Loading replaces the tree only when no successful
model has been loaded yet; refresh and database switching preserve the current tree until a new
model succeeds. Successful loading expands the hierarchy through the first schema and its Tables
group. Existing lazy population remains in place for schema contents and refresh replaces the
cached universal schema model atomically.

### Main window

Coordinate profile selection, worker lifecycle, explorer updates, breadcrumb, and status bar. The
refresh signal reloads the active profile. Query execution remains outside this feature and keeps
its current behavior.

## State and Data Flow

```text
ConnectionDialog accepted
    → ConnectionSelector refresh/select profile
    → MainWindow builds DatabaseConnection
    → SchemaInspectionWorker
    → PostgreSQLInspector.list_databases + inspect_database
    → accessible database names + DatabaseSchema
    → database dropdown + DatabaseExplorerWidget
    → breadcrumb + status bar

Database dropdown changed
    → MainWindow builds candidate connection for selected database
    → SchemaInspectionWorker.inspect_database
    → success: replace active connection and tree
    → failure: restore previous database selection and tree
```

Only one inspection may be active. The profile selector, database dropdown, and refresh control are
disabled until the worker completes. Passwords are retrieved through the existing keyring-backed
service and are never placed in the database list, schema model, tree labels, status messages, or
logs.

## Error Handling

- Network, SSL, authentication, permission, and catalog errors are caught in the worker.
- The UI remains responsive and the application stays open.
- The explorer displays a concise failure state and the status bar exposes the useful reason.
- A failed refresh preserves the previous successful tree so temporary outages do not erase useful
  context.
- An inspection that returns no user schemas shows an explicit empty state instead of a blank panel.
- A database-switch failure restores the last successful dropdown value and active connection.
- Disconnect errors during profile replacement or shutdown are logged and do not terminate Qt.

## Testing

Automated tests will verify:

- the worker returns a real `DatabaseSchema` from a connection-backed inspector;
- database discovery excludes templates and databases without `CONNECT` privilege;
- saving a profile triggers asynchronous inspection and selects that profile;
- the dropdown is placed above the explorer filter and selects the profile database;
- changing the dropdown inspects the selected database without saving another profile;
- a failed database switch preserves the prior selection, active connection, and tree;
- successful inspection populates and expands the database/schema/table hierarchy;
- profile selection and refresh trigger inspection without duplicate concurrent work;
- loading, empty, and failure states are visible and do not close the main window;
- breadcrumb and status text reflect the live profile and inspected database;
- changing profiles and closing the application disconnect active adapters;
- the full existing test suite and Ruff checks remain clean on Python 3.14.4.

## Out of Scope

- Keeping simultaneous active connections to multiple databases.
- Replacing the current placeholder SQL execution path with the active connection.
- ER diagram loading or schema editing.
