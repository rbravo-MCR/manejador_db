# PRODUCT_SPEC.md

# Backend Development IDE
## Product Specification for Codex

**Status:** Initial product specification  
**Target platforms:** Windows, Linux, macOS  
**Application type:** Independent desktop application  
**Primary audience:** DBA, Backend Developers, Full Stack Developers, Software Architects, Legacy Modernization Teams

---

# 1. Product Vision

Build a professional desktop **Backend Development IDE** centered on relational databases and backend productivity.

This product is **not only a database manager**.

The product must combine:

- Database management
- Advanced SQL editing
- Database schema exploration
- ER diagramming
- Code generation
- ORM and non-ORM generation
- Database First workflows
- Code First workflows
- Schema synchronization
- Schema diff
- Backend scaffolding
- Legacy application modernization
- Legacy DBF data migration

The product should help a developer move naturally through this workflow:

```text
Database
   ↓
Understand
   ↓
Design
   ↓
Query
   ↓
Generate
   ↓
Modernize
   ↓
Synchronize
```

The main product principle is:

> The database schema is a first-class development asset.

The tool must help backend developers understand existing databases, write SQL faster, generate backend code, modernize legacy systems, and safely synchronize code and database structures.

---

# 2. Product Positioning

The application should be positioned as:

> **Backend Development IDE**

Not simply:

> Database Manager

The intended product combines capabilities normally distributed across several tools:

```text
DB Manager
+
SQL IDE
+
ER Designer
+
Backend Generator
+
Schema Diff Tool
+
Legacy Modernization Assistant
```

The UX must remain clean and intuitive despite this feature depth.

---

# 3. Non-Negotiable Product Principles

Codex MUST follow these principles.

## 3.1 Desktop-first

The product is a native-style desktop application for:

- Windows
- Linux
- macOS

The application itself MUST NOT require Docker.

Docker support may exist only as an optional artifact generated for backend projects.

---

## 3.2 Cross-platform from day one

Avoid OS-specific assumptions.

Use abstractions such as:

- `pathlib`
- `QStandardPaths`
- `QSettings`
- `QProcess`
- `keyring`

Do not hardcode Windows or Linux paths.

Do not make shell-specific behavior part of the core architecture.

---

## 3.3 Modular architecture

The UI MUST NOT contain database-engine-specific business logic.

The SQL editor MUST NOT own metadata, database introspection, generation, or schema logic.

The code generator MUST NOT depend directly on a specific database engine.

All major functionality must be replaceable through stable interfaces.

---

## 3.4 Universal Schema Model is the core

The most important domain object in the system is the:

> **Universal Schema Model**

All supported databases must be converted into this neutral representation.

All code generators consume this neutral representation.

ER diagrams consume this representation.

Schema diff consumes this representation.

Legacy DBF import produces this representation.

Code First parsers must produce this representation.

Do not bypass the Universal Schema Model.

---

## 3.5 Performance-sensitive components may use Rust

The primary application is built in Python.

Rust is reserved for performance-sensitive engines.

Use:

- Rust
- PyO3
- maturin

Potential Rust modules include:

- SQL parsing
- Semantic SQL analysis
- Schema diff
- Dependency graph
- Metadata indexing
- Fuzzy search
- ER diagram layout
- Large DBF processing

Do NOT rewrite a Python component in Rust without evidence that performance requires it.

---

## 3.6 User data belongs to the user

Queries, generated code, procedures, migrations, reports, diagrams, and project files must be stored as normal files whenever practical.

Avoid proprietary binary formats.

Prefer:

- SQL
- JSON
- YAML
- Markdown
- Python
- TypeScript
- PHP
- C#
- Prisma
- other plain-text formats

Generated artifacts must remain usable outside this IDE.

---

## 3.7 Never overwrite user code blindly

Before changing an existing project:

- Preview changes
- Detect conflicts
- Show diffs
- Allow skip/replace/manual review

The tool must never silently overwrite important source files.

---

# 4. Primary Technology Stack

## Desktop application

```text
Python 3.14+
PySide6
Qt 6
QScintilla
```

## Database access

```text
PostgreSQL
    psycopg 3

MySQL / MariaDB
    PyMySQL

SQLite
    sqlite3

SQL Server
    pyodbc

Shared abstractions where useful
    SQLAlchemy Core
```

Do NOT use SQLAlchemy ORM internally as the universal database abstraction.

---

## Application and domain support

```text
Pydantic
dataclasses where appropriate
Jinja2
sqlglot
RapidFuzz
keyring
structlog
```

## Native performance core

```text
Rust
PyO3
maturin
```

## Tooling and Environment

```text
uv (package & venv management)
ruff (linting & formatting)
```

## Testing

```text
pytest
pytest-qt
cargo test
```

## Packaging

Prefer:

```text
Nuitka
GitHub Actions
```

Platform-specific builds must be generated on their corresponding operating systems.

---

# 5. Supported Database Engines

Tier 1 relational database engines:

```text
PostgreSQL
MySQL / MariaDB
SQLite
Microsoft SQL Server
```

All engines must expose a common inspection contract.

Example conceptual interface:

```python
class DatabaseInspector(Protocol):
    def inspect_database(self) -> DatabaseSchema:
        ...
```

Implementations:

```text
PostgreSQLInspector
MySQLInspector
SQLiteInspector
SQLServerInspector
```

---

# 6. Legacy Data Sources

The product must support legacy DBF data as a generic source format.

Do NOT treat FoxPro or Clipper as fully emulated database engines.

Use:

```text
Legacy Data Source
└── DBF
    ├── dBase-compatible
    ├── FoxPro-compatible
    └── Clipper-compatible
```

Initial DBF support:

- DBF table structure
- Fields
- Records
- Deleted record markers
- Data type detection
- Character encoding handling
- DBT memo files
- FPT memo files
- Streaming/batch processing for large datasets

Later support:

- NTX
- CDX
- NSX

The objective is:

> Analyze, normalize, migrate and modernize legacy DBF data.

The objective is NOT:

> Fully emulate FoxPro or Clipper runtime behavior.

DBF must eventually map into:

```text
DBF
 ↓
Legacy Inspector
 ↓
Universal Schema Model
 ↓
PostgreSQL / MySQL / SQLite / SQL Server
```

---

# 7. Universal Schema Model

The Universal Schema Model must be independent from:

- PostgreSQL
- MySQL
- SQLite
- SQL Server
- DBF
- SQLAlchemy
- SQLModel
- Django
- Sequelize
- Prisma
- TypeORM
- Drizzle
- Eloquent
- Doctrine
- Entity Framework Core
- Dapper

Minimum required entities:

```text
Database
Schema
Table
Column
PrimaryKey
ForeignKey
Index
UniqueConstraint
CheckConstraint
Default
Sequence
View
MaterializedView
Function
Procedure
Trigger
Relationship
```

Additional metadata should support:

- native database type
- normalized type
- nullable
- auto increment / identity
- generated columns
- default expressions
- precision
- scale
- length
- comments
- collation
- references
- composite keys
- indexes
- unique constraints
- checks

The model must be serializable.

Prefer a stable representation suitable for:

- JSON
- tests
- cache
- diffs
- persistence
- plugin boundaries

---

# 8. Database Connection Profiles

Users must be able to save database connections.

Each connection profile should support:

```text
Name
Database engine
Host
Port
Database
Username
Secure password reference
Optional color
Environment
Optional group
```

Environment values:

```text
Development
Testing
Staging
Production
```

Passwords must NOT be stored as plain text.

Use the operating system credential store through `keyring`.

Connection profiles should visually expose:

- name
- engine
- environment
- optional color

Color should follow the connection across:

- Database Explorer
- Query tabs
- Status bar
- ER Diagram
- Connection selector

Production must receive extra visual and execution safeguards.

---

# 9. Production Safety

Potentially dangerous operations against Production connections require protection.

Examples:

```text
DELETE without WHERE
UPDATE without WHERE
DROP TABLE
TRUNCATE
DROP DATABASE
DROP SCHEMA
```

The IDE should warn clearly before execution.

Do not depend only on color.

Use the explicit connection environment classification.

---

# 10. Workspace and File Model

The user may open a folder as a workspace.

Example:

```text
my-backend/
├── queries/
├── procedures/
├── functions/
├── views/
├── migrations/
├── models/
├── generated/
├── diagrams/
└── .backendide/
```

Possible contents:

```text
queries/
    active-customers.sql

procedures/
    sp_create_reservation.sql

functions/
    calculate_total.sql

migrations/
    2026_08_13_add_customer_phone.sql

diagrams/
    reservations.erd.json

.backendide/
    workspace.json
```

The `.backendide` directory may contain:

- open tabs
- layout state
- diagram positions
- generator preferences
- workspace connection references
- non-secret settings

Secrets must remain outside the workspace.

---

# 11. File Editing

Required standard behavior:

```text
Ctrl+S
    Save

Ctrl+Shift+S
    Save As

Save All
```

Unsaved tabs must be clearly indicated.

Example:

```text
reservations.sql *
```

The application should eventually support crash/session recovery for unsaved work.

---

# 12. SQL IDE

The SQL editor is a major product pillar.

Use:

```text
QScintilla
```

QScintilla is responsible only for the editing surface.

It should not contain business logic.

The SQL IDE architecture should conceptually be:

```text
SQL Editor UI
      ↓
SQL Language Engine
      ├── Parser
      ├── Dialect
      ├── Completion Engine
      ├── Semantic Analyzer
      ├── Diagnostics
      ├── Formatter
      ├── Snippets
      └── Metadata Provider
```

---

# 13. SQL Editor Capabilities

Target capabilities:

- Syntax highlighting
- Line numbers
- Folding
- Brace matching
- Search
- Replace
- Multiple tabs
- Execute current statement
- Execute selected text
- SQL formatter
- Snippets
- IntelliSense
- Table completion
- Column completion
- Alias-aware completion
- Function completion
- Type completion
- Fuzzy matching
- SQL diagnostics
- Hover information
- Go-to-definition where practical
- Query history
- Favorites
- Execution time
- Row count
- Explain support

---

# 14. SQL IntelliSense

Autocomplete must understand SQL context.

Example:

```sql
SELECT c.
FROM customers c
```

Expected suggestions:

```text
id
name
email
status
created_at
```

Autocomplete should use cached metadata.

Do NOT query the database on every keystroke.

Metadata must be loaded, cached, indexed, and refreshed independently.

---

# 15. Relationship-Aware SQL Completion

Foreign key information must power SQL suggestions.

Example:

```sql
FROM reservations r
JOIN
```

The editor may suggest:

```text
customers
suppliers
payments
```

Based on known relationships.

Selecting a relationship may generate:

```sql
JOIN customers c
    ON c.id = r.customer_id
```

This is a strategic product feature.

---

# 16. Query Execution

Database queries must NOT block the Qt UI thread.

Use:

- `QThreadPool`
- `QRunnable`
- workers
- signals/slots

Required capabilities:

- Execute SQL
- Execute selected SQL
- Execute current statement
- Cancel when supported
- Commit
- Rollback
- Auto-commit options
- Execution messages
- Error details
- Result tables
- Result paging
- Export CSV
- Export JSON

---

# 17. Database Explorer

The Database Explorer must support lazy loading.

Potential hierarchy:

```text
Connection
└── Database
    └── Schema
        ├── Tables
        ├── Views
        ├── Materialized Views
        ├── Functions
        ├── Procedures
        ├── Sequences
        └── Triggers
```

Context actions should include:

```text
Open Data
Open Structure
New Query
Generate SQL
Generate Code
Open ER Diagram
Copy Name
Refresh
```

---

# 18. ER Diagram

The application must include a visual ER diagram.

The ER diagram consumes the Universal Schema Model.

Required concepts:

```text
Explore Mode
Design Mode
```

## Explore Mode

Read-only schema exploration.

Features:

- tables as nodes
- columns
- PK
- FK
- relationships
- zoom
- pan
- search
- auto layout
- focus mode
- hide/show tables
- configurable detail level

Detail levels:

```text
Compact
Normal
Detailed
```

---

## 18.1 Relationship Focus Mode

For large databases, avoid displaying every table.

The user should be able to select a table and display:

```text
Direct relationships
2 levels
All relationships
```

---

## 18.2 Relationship Path Finder

The user should eventually be able to select two tables and request:

```text
Find relationship
```

Example:

```text
customers
 ↓
reservations
 ↓
payments
```

The tool may use this information to generate a JOIN query.

---

## 18.3 Design Mode

Design Mode may support:

- create table
- rename table
- add column
- remove column
- change type
- create FK
- create index
- set unique
- set nullability
- edit defaults

Never apply changes directly.

Flow:

```text
Visual Change
 ↓
Schema Diff
 ↓
SQL Preview
 ↓
User confirmation
 ↓
Apply
```

---

# 19. Schema Diff Engine

The system must eventually support:

```text
DB ↔ DB
DB ↔ Code
Code ↔ Code
ORM ↔ DB
```

Diff classifications:

```text
Added
Removed
Modified
Potentially destructive
```

Examples:

```text
+ customers.phone
~ reservations.status VARCHAR(20) → VARCHAR(50)
- payments.legacy_code
```

The diff engine should feed the migration engine.

---

# 20. Database First

Database First workflow:

```text
Database
 ↓
Inspector
 ↓
Universal Schema Model
 ↓
Models / ORM / SQL / Backend
```

Users should be able to select:

- one table
- several tables
- a schema
- an ERD selection

and generate code.

---

# 21. Code First

Code First workflow:

```text
Models / ORM Code
 ↓
Parser
 ↓
Universal Schema Model
 ↓
Schema Diff
 ↓
Migration
 ↓
Database
```

Initial target model parsers may include:

- SQLAlchemy
- SQLModel
- Prisma
- Sequelize
- Eloquent
- EF Core

Do not implement all parsers in the first milestone.

---

# 22. Hybrid / Sync Mode

Long-term target:

```text
Database ←→ Universal Schema Model ←→ Code
```

Example UI:

```text
Database                    Code
────────────────────────────────────
users.id             ✓      users.id
users.email          ✓      users.email
users.phone          →      missing
                     ←      users.avatar
```

The user must decide direction where ambiguity exists.

Never synchronize destructive changes automatically.

---

# 23. Code Generator Engine

The Code Generator must be plugin-friendly.

Do NOT implement giant conditional blocks like:

```python
if framework == "fastapi" and orm == "sqlalchemy":
    ...
elif framework == "nestjs" and orm == "sequelize":
    ...
```

Prefer composable generators.

Conceptual architecture:

```text
Universal Schema Model
        ↓
Generator Engine
        ↓
Language
        ↓
Framework
        ↓
ORM / Data Access
        ↓
Architecture Template
        ↓
Generated Files
```

Possible conceptual interfaces:

```text
LanguageGenerator
FrameworkGenerator
OrmGenerator
ArchitectureTemplate
```

---

# 24. Supported Backend Ecosystems

Tier 1 planned ecosystems:

## Python

Frameworks:

```text
FastAPI
Flask
Django
```

ORM / Data Access:

```text
SQLAlchemy
SQLModel
Django ORM
Native SQL
```

---

## TypeScript / Node.js

Traditional server frameworks:

```text
NestJS
Fastify
Express
```

ORM / Data Access:

```text
Sequelize
Prisma
TypeORM
Drizzle
Native SQL
```

Sequelize is a first-class ORM option.

---

## PHP

Frameworks:

```text
Laravel
Symfony
```

ORM / Data Access:

```text
Eloquent
Doctrine
PDO
```

---

## C#

Framework:

```text
ASP.NET Core
```

Data Access:

```text
Entity Framework Core
Dapper
ADO.NET
```

---

# 25. Serverless

Serverless options must only appear when the user explicitly selects a serverless or edge deployment model.

Do NOT mix Hono into the normal traditional backend workflow.

Example:

```text
Deployment Model

Traditional Server
Serverless
Edge
```

When Serverless or Edge is selected, Hono may become available.

The system should filter incompatible ORM/runtime combinations.

---

# 26. Backend Generation

The generator should eventually support generation of:

- Models
- Entities
- DTOs
- Schemas
- Repositories
- Services
- Controllers
- Routes
- CRUD
- Validation
- Pagination
- Filtering
- OpenAPI
- Tests
- Configuration
- `.env.example`
- optional Dockerfile
- optional container configuration

Docker output is optional generated project content only.

Docker is NOT an application runtime requirement.

---

# 27. Generation Modes

The user should be able to choose:

```text
New project
Add module to existing project
Models only
ORM schema only
CRUD only
Preview only
```

Before modifying an existing project:

```text
Skip
Show Diff
Replace
```

Prefer `Show Diff`.

---

# 28. ORM and Non-ORM Support

The product must support both approaches.

The user must never be forced into an ORM.

Examples:

```text
TypeScript
├── Sequelize
├── Prisma
├── TypeORM
├── Drizzle
└── Native SQL

Python
├── SQLAlchemy
├── SQLModel
├── Django ORM
└── Native SQL

PHP
├── Eloquent
├── Doctrine
└── PDO

C#
├── EF Core
├── Dapper
└── ADO.NET
```

---

# 29. Legacy Modernization

Legacy modernization is a major product area.

Target sources include:

```text
PHP legacy
VB.NET
C# legacy
Node.js legacy
Python legacy
Visual FoxPro source code where practical
DBF datasets
```

The goal is NOT syntax-only conversion.

The tool should identify:

- data access
- SQL
- business rules
- models
- relationships
- stored procedures
- technical debt
- deprecated APIs
- migration candidates

---

# 30. Legacy Modernization Targets

Users may choose target stacks such as:

```text
C# / .NET
Python
TypeScript / Node.js
```

Examples:

```text
VB.NET + ADO.NET
    ↓
C# + ASP.NET Core + EF Core
```

```text
PHP + mysqli/PDO
    ↓
Laravel + Eloquent
```

```text
Node raw SQL
    ↓
TypeScript + Sequelize
```

```text
FoxPro / DBF
    ↓
PostgreSQL / SQL Server
    ↓
C# / Python / TypeScript backend
```

---

# 31. Incremental Legacy Migration

Do not assume an entire legacy system should be migrated in one operation.

Support strategies:

```text
Incremental
Module by module
Models only
Repository layer
Full ORM migration
```

Migration candidates should be classified:

```text
Safe
Review
Manual
```

Example:

```text
Safe
    Simple parameterized CRUD

Review
    Business logic mixed with SQL

Manual
    Dynamic SQL
    Very complex stored procedures
    Unclear business rules
```

---

# 32. ORM Migration Recommendations

The tool must NOT assume ORM is always better.

For some queries, recommend preserving native SQL.

Examples:

- complex reporting
- CTE-heavy SQL
- window functions
- vendor-specific optimized SQL
- high-performance batch queries

The product should make technical recommendations rather than blindly transform code.

---

# 33. Legacy Upgrade Reports

The product should eventually generate professional modernization reports.

Supported export targets may include:

```text
PDF
DOCX
Markdown
HTML
```

Possible report sections:

```text
Executive Summary
Current Architecture
Technology Inventory
Database Access Analysis
Technical Debt
Security Findings
Migration Strategy
Target Architecture
Module-by-Module Plan
Code Transformations
Database Changes
Stored Procedure Strategy
Risk Matrix
Testing Strategy
Rollback Strategy
Remaining Manual Work
Recommendations
```

Do not implement reporting before the core architecture is stable.

---

# 34. UI / UX Principles

The product must have a high-quality modern UI.

Do not treat UI quality as a final polish step.

Build a design system early.

Primary principles:

- high information density without clutter
- intuitive navigation
- contextual actions
- fast keyboard workflow
- clear visual hierarchy
- minimal modal interruption
- responsive desktop layouts
- strong feedback states
- accessible dark/light appearance
- professional developer-tool aesthetics

Reference quality level:

```text
JetBrains DataGrip
VS Code
Linear
Raycast
TablePlus
Beekeeper Studio
```

Do NOT clone these products.

Use them only as quality references.

---

# 35. Application Layout

Conceptual layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ Top Bar / Connection / Commands / Theme                   │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│ Explorer      │                  Workspace                  │
│               │                                             │
│ DB / Schema   │ SQL / ERD / Generator / Diff / Data       │
│               │                                             │
├───────────────┼─────────────────────────────────────────────┤
│               │ Results / Problems / Explain / History     │
├───────────────┴─────────────────────────────────────────────┤
│ Status Bar                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

# 36. Theme System

Required appearance modes:

```text
System
Light
Dark
```

A compact quick toggle must exist in the top bar:

```text
☀️ / 🌙
```

The user should not need to open Settings to switch Light/Dark.

Persist theme preference.

Use a centralized theme system.

Do not scatter colors across widgets.

---

# 37. Design System

Create reusable design tokens.

Examples:

```text
Spacing
Typography
Radius
Borders
Elevation
Accent
Success
Warning
Danger
Info
```

Reusable components may include:

```text
Button
IconButton
SplitButton
Tabs
SearchBox
CommandPalette
TreeItem
DataGrid
Toast
Dialog
ContextMenu
Dropdown
Tooltip
Badge
EmptyState
Breadcrumb
StatusBar
```

Prefer SVG icons.

---

# 38. Command Palette

The product should eventually support a command palette.

Example:

```text
Ctrl+Shift+P
```

Commands may include:

```text
Connect database
New SQL query
Generate Sequelize model
Generate SQLAlchemy model
Open ER Diagram
Compare schemas
Format SQL
```

---

# 39. Context Menus

Context menus are a key advanced-user interaction.

Example table context menu:

```text
Open Data
Open Structure
ER Diagram

Generate SQL
├── SELECT
├── INSERT
├── UPDATE
└── DELETE

Generate Code
├── SQLAlchemy
├── Sequelize
├── Prisma
├── Eloquent
└── EF Core

Compare Schema
Copy Name
```

---

# 40. Performance Strategy

Do not prematurely optimize everything.

First implement correct, testable Python versions.

Measure real performance.

Move modules to Rust only when justified.

Likely Rust candidates:

```text
SQL parsing
SQL semantic analysis
Schema diff
Dependency graph
Metadata index
Fuzzy matching
ERD layout
DBF processing
```

---

# 41. Security

Requirements:

- Never store passwords in plain text
- Use OS credential storage
- Parameterize generated queries
- Warn against dangerous production operations
- Do not silently execute destructive migrations
- Do not expose secrets in logs
- Do not include credentials in exported workspace files
- Do not include credentials in generated source code

---

# 42. Testing Strategy

Every core feature must be testable without the UI.

Required layers:

```text
Domain tests
Inspector tests
Generator tests
Diff tests
SQL engine tests
UI tests
Integration tests
```

Use fixtures representing realistic schemas.

Test edge cases:

- composite PK
- composite FK
- nullable columns
- default expressions
- unusual identifiers
- reserved keywords
- cross-schema references
- large schemas
- cyclic relationships

---

# 43. Repository Structure

Initial proposed repository structure:

```text
backend-development-ide/
├── src/
│   └── backend_ide/
│       ├── domain/
│       │   ├── schema/
│       │   ├── sql/
│       │   └── generation/
│       │
│       ├── application/
│       │
│       ├── infrastructure/
│       │   ├── database/
│       │   ├── storage/
│       │   └── security/
│       │
│       ├── generators/
│       │   ├── python/
│       │   ├── typescript/
│       │   ├── php/
│       │   └── csharp/
│       │
│       ├── legacy/
│       │   └── dbf/
│       │
│       └── ui/
│           ├── components/
│           ├── editor/
│           ├── explorer/
│           ├── diagrams/
│           ├── dialogs/
│           └── theme/
│
├── rust/
│   └── backend_ide_core/
│
├── tests/
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── DECISIONS.md
│
├── pyproject.toml
├── README.md
└── .gitignore
```

This structure is a starting point.

Codex may suggest improvements but must explain architectural reasons before changing the top-level organization substantially.

---

# 44. Development Phases

## Phase 0 — Foundation

Deliver:

- repository
- coding conventions
- dependency management
- architecture documentation
- test configuration
- CI skeleton

No full application implementation.

---

## Phase 1 — Universal Schema Model

Implement only the neutral schema domain model.

Acceptance criteria:

- no database-specific dependencies
- serializable
- unit tested
- supports relationships and constraints
- supports realistic complex schemas

Do NOT implement the GUI yet.

---

## Phase 2 — PostgreSQL Inspector

Implement PostgreSQL inspection into Universal Schema Model.

Acceptance criteria:

- schemas
- tables
- columns
- PK
- FK
- indexes
- unique
- checks
- defaults
- sequences
- views
- functions
- triggers

---

## Phase 3 — PySide6 Application Shell

Implement:

- main window
- basic navigation
- workspace
- connection panel
- theme system
- Light/Dark quick toggle
- basic reusable design components

Do not implement advanced SQL intelligence yet.

---

## Phase 4 — Query Execution

Implement:

- SQL execution
- worker-based execution
- results
- messages
- transaction controls
- exports

No UI blocking.

---

## Phase 5 — Advanced SQL Editor

Implement QScintilla editor infrastructure.

Then incrementally add:

- syntax
- statement detection
- formatting
- autocomplete
- metadata completion
- diagnostics

---

## Phase 6 — Metadata Cache and IntelliSense

Implement fast metadata indexing.

Acceptance criteria:

- no DB query per keystroke
- alias-aware columns
- context-sensitive suggestions
- fuzzy search
- relationship-aware JOIN suggestions

---

## Phase 7 — Remaining Tier 1 Databases

Implement:

- MySQL / MariaDB
- SQLite
- SQL Server

All must produce the same Universal Schema Model.

---

## Phase 8 — ORM Model Generation

Initial generators:

```text
SQLAlchemy
SQLModel
Sequelize
Prisma
Eloquent
EF Core
```

The same schema must generate all outputs.

---

## Phase 9 — Non-ORM Generation

Initial support:

```text
Python native DB access
TypeScript native DB access
PHP PDO
C# Dapper / ADO.NET
```

---

## Phase 10 — Backend Generator

Initial target stacks:

```text
FastAPI + SQLAlchemy / SQLModel
NestJS + Sequelize
Laravel + Eloquent
ASP.NET Core + EF Core
```

Do not add every possible framework before these are stable.

---

## Phase 11 — ER Diagram

Implement:

- Explore Mode
- relationship visualization
- auto-layout
- search
- focus mode
- detail levels

Then Design Mode.

---

## Phase 12 — Code First

Add model parsers incrementally.

Do not implement all ORMs simultaneously.

---

## Phase 13 — Schema Diff

Implement neutral schema comparison.

Then migration generation.

---

## Phase 14 — Hybrid Sync

Implement controlled DB/code reconciliation.

Never auto-apply destructive changes.

---

## Phase 15 — Legacy DBF

Implement generic DBF legacy data source support.

Initial scope:

- DBF
- DBT
- FPT
- encoding
- deleted records
- schema inference
- streaming
- migration target mapping

Later:

- NTX
- CDX
- NSX

---

## Phase 16 — Legacy Source Modernization

Initial target:

- PHP legacy
- VB.NET
- C# legacy

Then expand based on real user demand.

---

## Phase 17 — Performance and Explain

Implement:

- Explain
- Explain Analyze where supported
- visual plans
- performance hints
- index analysis

---

## Phase 18 — Commercial Polish

Implement:

- packaging
- crash recovery
- update strategy
- installers
- code signing planning
- telemetry strategy only if explicitly approved
- documentation
- onboarding
- licensing architecture

---

# 45. MVP Definition

The first useful MVP is NOT the full roadmap.

MVP target:

```text
Desktop application
+
PostgreSQL
+
MySQL
+
SQLite
+
SQL Server
+
Database Explorer
+
SQL Editor
+
Query Results
+
Saved Connections
+
Light/Dark
+
Universal Schema Model
+
Basic ER Diagram
+
Basic model generation
```

Initial generation targets:

```text
SQLAlchemy
Sequelize
Prisma
Eloquent
EF Core
```

Legacy modernization can remain post-MVP if necessary.

---

# 46. First Technical Milestone

The first milestone to prove architecture correctness is:

```text
Connect PostgreSQL
        ↓
Inspect one schema
        ↓
Load Universal Schema Model
        ↓
Select customers
        ↓
Generate:
    SQLAlchemy
    SQLModel
    Sequelize
    Prisma
    Eloquent
    EF Core
```

If this works correctly from the same Universal Schema Model, the core architecture is validated.

---

# 47. Codex Working Rules

Codex MUST follow these rules.

## Rule 1

Do not implement the entire roadmap in one pass.

---

## Rule 2

Work phase by phase.

---

## Rule 3

Before implementing a phase:

- summarize intended changes
- identify affected modules
- identify new dependencies
- identify risks

---

## Rule 4

Do not introduce new major frameworks without explaining why.

---

## Rule 5

Do not change architectural boundaries casually.

---

## Rule 6

Keep business/domain logic independent from PySide6.

---

## Rule 7

Keep database-specific logic inside adapters/inspectors/dialects.

---

## Rule 8

Keep generators independent from database drivers.

Generators consume the Universal Schema Model.

---

## Rule 9

Add tests with every core implementation.

---

## Rule 10

Do not silently remove or rewrite working functionality.

---

## Rule 11

Prefer simple and explicit implementations over speculative abstraction.

---

## Rule 12

Do not introduce Rust unless:

- the interface is already clearly defined
- the Python implementation is measurable
- there is a demonstrated performance reason

Exception:

DBF streaming and other explicitly designated native components may use Rust earlier if justified.

---

## Rule 13

Do not store credentials in source files, configuration files, logs, generated code, or workspace metadata.

---

## Rule 14

Do not execute destructive database operations automatically.

---

## Rule 15

Do not generate code into an existing project without previewing conflicts.

---

# 48. Initial Codex Task

When this specification is first provided to Codex, DO NOT start implementing the full application.

First perform the following:

1. Read this entire specification.
2. Summarize the proposed architecture.
3. Identify technical risks.
4. Identify unclear or conflicting requirements.
5. Propose the initial repository structure.
6. Propose the contents of `pyproject.toml`.
7. Define the interfaces for:
   - Universal Schema Model
   - Database Inspector
   - Database Adapter
   - Code Generator
   - SQL Dialect
8. Propose an initial testing strategy.
9. Identify which components should initially remain Python.
10. Identify potential future Rust boundaries.
11. Produce a concrete implementation plan for Phase 0 and Phase 1.
12. STOP.

Do not implement the complete application until the architecture proposal has been reviewed.

---

# 49. Definition of Success

The product succeeds when a DBA or backend developer can:

1. Open the desktop application.
2. Connect to a database.
3. Visually understand its schema.
4. Write SQL with high-quality IntelliSense.
5. Execute and inspect queries safely.
6. Generate backend data-access code.
7. Choose ORM or non-ORM.
8. Generate models in multiple languages.
9. Compare database and code schemas.
10. Modernize legacy systems incrementally.
11. Save all relevant work as normal files.
12. Use the application comfortably on Windows, Linux, or macOS.

The application should feel:

```text
Fast
Professional
Modern
Predictable
Safe
Developer-first
```

---

# 50. Final Product Direction

The product is:

> A cross-platform Backend Development IDE centered on databases, schema intelligence, SQL productivity, backend code generation, and legacy modernization.

The core architectural chain is:

```text
Database / Legacy Source / Code
              ↓
       Universal Schema Model
              ↓
 ┌────────────┼───────────────┐
 ↓            ↓               ↓
SQL IDE     ER Designer    Schema Diff
                              ↓
                       Generator Engine
                              ↓
            ORM / Native / Backend / Migration
```

Protect this architecture.

Do not optimize for the fastest possible demo if doing so breaks these boundaries.
