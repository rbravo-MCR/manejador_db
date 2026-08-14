# Live Database Explorer Design

## Goal

After a PostgreSQL profile is tested and saved, automatically inspect its active database and
populate the desktop Database Explorer with the real connection, database, schemas, and tables.
The approved scope is the selected database only; enumerating and reconnecting to every database
on the PostgreSQL server is excluded.

## User Experience

The successful flow is:

1. The user opens **Nueva Conexión**, enters the profile, tests it, and saves it.
2. The main window selects the saved profile and immediately shows **Cargando estructura…**.
3. Database inspection runs outside the Qt UI thread.
4. The explorer renders `Connection → Database → Schema → Tables → Table` from live metadata.
5. The connection, database, first schema, and tables group are expanded so the result is visible
   without another click.
6. The breadcrumb and status bar use the real selected profile, database, and schema instead of
   the current hard-coded local PostgreSQL labels.

The existing refresh action repeats the inspection for the active profile. During the first load,
the tree shows a loading row. During later refreshes, the old tree remains visible. The profile
selector and refresh control are disabled until inspection finishes, preventing duplicate work or
a mismatch between the selected profile and displayed metadata.

## Architecture

`MainWindow` owns the active profile, active `DatabaseConnection`, and current inspection worker.
On an accepted connection dialog, it refreshes and selects the saved profile, builds the connection
through `ConnectionService`, and starts asynchronous inspection.

A focused `SchemaInspectionWorker` receives the database connection and uses
`PostgreSQLInspector.inspect_database()`. It emits either a `DatabaseSchema` or a sanitized error
message. The worker never reads UI widgets and never mutates the explorer directly.

On success, `MainWindow` passes the model to `DatabaseExplorerWidget.load_schema_model()`, updates
the breadcrumb and status, and retains the active connection for later real-query integration. On
profile change, it disconnects the previous adapter before loading the new profile. Closing the
window also disconnects it.

## Component Changes

### Connection selector

Add a method to select a profile by ID after its list is refreshed. Profile changes request a live
schema load rather than merely repainting the environment badge.

### Schema inspection worker

Add a Qt `QRunnable` with success and failure signals. It connects lazily through the existing
PostgreSQL adapter, invokes the existing inspector, and leaves the successfully opened connection
available to the main window. Failures disconnect the adapter and return an actionable message.

### Database Explorer

Add explicit loading, empty, and error presentations inside the tree. Loading replaces the tree
only when no successful model has been loaded yet; refresh preserves the current tree until a new
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
    → PostgreSQLInspector
    → DatabaseSchema
    → DatabaseExplorerWidget
    → breadcrumb + status bar
```

Only one inspection may be active. The profile selector and refresh control are disabled until the
worker completes. Passwords are retrieved through the existing keyring-backed service and are
never placed in the schema model, tree labels, status messages, or logs.

## Error Handling

- Network, SSL, authentication, permission, and catalog errors are caught in the worker.
- The UI remains responsive and the application stays open.
- The explorer displays a concise failure state and the status bar exposes the useful reason.
- A failed refresh preserves the previous successful tree so temporary outages do not erase useful
  context.
- An inspection that returns no user schemas shows an explicit empty state instead of a blank panel.
- Disconnect errors during profile replacement or shutdown are logged and do not terminate Qt.

## Testing

Automated tests will verify:

- the worker returns a real `DatabaseSchema` from a connection-backed inspector;
- saving a profile triggers asynchronous inspection and selects that profile;
- successful inspection populates and expands the database/schema/table hierarchy;
- profile selection and refresh trigger inspection without duplicate concurrent work;
- loading, empty, and failure states are visible and do not close the main window;
- breadcrumb and status text reflect the live profile and inspected database;
- changing profiles and closing the application disconnect active adapters;
- the full existing test suite and Ruff checks remain clean on Python 3.14.4.

## Out of Scope

- Enumerating every PostgreSQL database on the server.
- Opening independent connections for multiple databases.
- Replacing the current placeholder SQL execution path with the active connection.
- ER diagram loading or schema editing.
