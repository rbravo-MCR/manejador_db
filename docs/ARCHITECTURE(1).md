# ARCHITECTURE.md

# Backend Development IDE — Architecture

**Status:** Initial architecture baseline  
**Target platforms:** Windows, Linux, macOS  
**Primary stack:** Python + PySide6 + Qt 6 + QScintilla  
**Native performance stack:** Rust + PyO3 + maturin

---

## 1. Architectural Goals

The application must be:

- Cross-platform
- Modular
- Extensible
- Testable without UI
- Safe for production database usage
- Capable of supporting Database First and Code First
- Capable of ORM and non-ORM generation
- Suitable for legacy modernization
- Able to evolve toward Rust for performance-critical components without rewriting the application

The system must avoid tightly coupling:

- UI to database engines
- SQL editor to metadata acquisition
- code generators to database drivers
- schema diff to a specific ORM
- legacy import to FoxPro or Clipper runtime behavior

---

## 2. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    PySide6 Desktop UI                       │
│                                                             │
│ Explorer │ SQL IDE │ ERD │ Generator │ Diff │ Modernization│
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│                                                             │
│ Use Cases / Services / Commands / Orchestration             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                           │
│                                                             │
│ Universal Schema Model                                     │
│ SQL contracts                                              │
│ Generator contracts                                        │
│ Diff contracts                                             │
│ Workspace concepts                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────────┐
          ▼                 ▼                     ▼
┌────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│ Infrastructure │ │ Generator Engine │ │ Native Rust Core   │
│                │ │                  │ │                    │
│ DB adapters    │ │ Python           │ │ SQL analysis       │
│ Inspectors     │ │ TypeScript       │ │ Schema diff        │
│ Files          │ │ PHP              │ │ Metadata index     │
│ Keyring        │ │ C#               │ │ DBF streaming      │
└────────────────┘ └──────────────────┘ └────────────────────┘
```

---

## 3. Layer Responsibilities

### 3.1 Presentation Layer

Technology:

```text
PySide6
Qt 6
QScintilla
```

Responsibilities:

- Main window
- Database Explorer
- SQL tabs
- Query results
- ER diagrams
- Code generation wizard
- Schema diff views
- Connection manager
- Legacy modernization views
- Theme system
- Notifications
- Command palette
- Context menus

The presentation layer MUST NOT:

- Execute raw database introspection logic directly
- Contain generator rules
- Contain ORM-specific mappings
- Store passwords
- Implement schema comparison algorithms

---

### 3.2 Application Layer

Responsibilities:

- Coordinate use cases
- Manage workflows
- Invoke inspectors
- Invoke generators
- Invoke schema diff
- Manage query execution jobs
- Manage workspace state
- Coordinate file persistence
- Apply production-safety policies

Example services:

```text
InspectDatabaseService
ExecuteQueryService
GenerateCodeService
GenerateBackendService
CompareSchemasService
ImportLegacyDbfService
ModernizeLegacyProjectService
WorkspaceService
ConnectionProfileService
```

---

### 3.3 Domain Layer

The Domain Layer contains product concepts independent from frameworks.

Primary concepts:

```text
DatabaseSchema
Schema
Table
Column
PrimaryKey
ForeignKey
Index
Constraint
View
Function
Procedure
Trigger
Relationship
SchemaDiff
GenerationRequest
GenerationResult
ConnectionProfile
Workspace
```

No PySide6 imports are allowed in domain modules.

No database driver imports are allowed in domain modules.

---

## 4. Universal Schema Model

The Universal Schema Model is the architectural center of the system.

```text
PostgreSQL ───────┐
MySQL ────────────┤
SQLite ───────────┤
SQL Server ───────┤
DBF ──────────────┤
ORM Code ─────────┤
                  ▼
       Universal Schema Model
                  │
       ┌──────────┼─────────────┐
       ▼          ▼             ▼
      ERD      Diff Engine   Generators
```

The Universal Schema Model must be:

- Serializable
- Stable
- Versionable
- Testable
- Engine-neutral
- ORM-neutral

Recommended representation:

```python
DatabaseSchema
└── schemas: list[Schema]
    └── tables: list[Table]
        ├── columns
        ├── primary_key
        ├── foreign_keys
        ├── indexes
        └── constraints
```

---

## 5. Database Architecture

### 5.1 Supported engines

Tier 1:

```text
PostgreSQL
MySQL / MariaDB
SQLite
Microsoft SQL Server
```

### 5.2 Contracts

Conceptual interfaces:

```python
class DatabaseConnection(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def test(self) -> bool: ...


class DatabaseInspector(Protocol):
    def inspect_database(self) -> DatabaseSchema: ...


class QueryExecutor(Protocol):
    def execute(self, request: QueryRequest) -> QueryResult: ...


class SQLDialect(Protocol):
    def keywords(self) -> set[str]: ...
    def functions(self) -> set[str]: ...
    def normalize_identifier(self, value: str) -> str: ...
```

Implementations:

```text
PostgreSQLConnection
PostgreSQLInspector
PostgreSQLDialect

MySQLConnection
MySQLInspector
MySQLDialect

SQLiteConnection
SQLiteInspector
SQLiteDialect

SQLServerConnection
SQLServerInspector
TSQLDialect
```

---

## 6. Query Execution Architecture

Queries must never execute on the Qt UI thread.

```text
SQL Editor
   ↓
ExecuteQueryService
   ↓
QueryJob
   ↓
QThreadPool / QRunnable
   ↓
Database Adapter
   ↓
QueryResult
   ↓
Qt Signal
   ↓
Results View
```

Required execution concepts:

```text
QueryRequest
QueryResult
ExecutionStats
DatabaseError
TransactionState
```

---

## 7. SQL IDE Architecture

QScintilla is the editing surface only.

```text
QScintilla
    │
    ▼
SQL Editor Controller
    │
    ├── Statement Detector
    ├── Formatter
    ├── Completion Engine
    ├── Semantic Analyzer
    ├── Diagnostics Engine
    ├── Snippet Engine
    └── Metadata Provider
```

Metadata must be cached.

Do not query the database on every keystroke.

---

## 8. Metadata Architecture

```text
Database Inspector
       ↓
Universal Schema Model
       ↓
Metadata Cache
       ↓
Metadata Index
       ↓
SQL Completion Engine
```

Initial implementation may remain Python.

Rust becomes an option when:

- schemas contain thousands of tables
- completion indexing becomes slow
- dependency traversal becomes expensive

---

## 9. ER Diagram Architecture

The ER diagram renders the Universal Schema Model.

```text
Universal Schema Model
          ↓
Graph Model
          ↓
Layout Engine
          ↓
Qt Graphics Scene
```

Modes:

```text
Explore
Design
```

Design Mode produces proposed schema changes.

It must NOT directly mutate a database.

```text
ERD Change
   ↓
Proposed Schema
   ↓
Schema Diff
   ↓
Migration Preview
   ↓
User Confirmation
   ↓
Apply
```

---

## 10. Schema Diff Architecture

```text
Source Schema
      │
      ├── Database
      ├── ORM
      └── File
      │
      ▼
Universal Schema Model
      │
      ▼
Schema Diff Engine
      │
      ▼
SchemaDiff
      │
      ├── Added
      ├── Removed
      ├── Modified
      └── Destructive
```

The diff engine must be neutral.

Migration generators consume `SchemaDiff`.

---

## 11. Code Generation Architecture

Avoid framework-specific condition trees.

```text
GenerationRequest
      ↓
Generator Engine
      ↓
Language Generator
      ↓
Framework Generator
      ↓
ORM / Data Access Generator
      ↓
Architecture Template
      ↓
GeneratedProject
```

Example:

```text
TypeScript
+
NestJS
+
Sequelize
+
Repository + Service
```

Initial language families:

```text
Python
TypeScript
PHP
C#
```

---

## 12. Generator Plugin Model

Conceptual interface:

```python
class CodeGenerator(Protocol):
    id: str
    language: str

    def supports(self, request: GenerationRequest) -> bool:
        ...

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        ...
```

Potential components:

```text
SQLAlchemyGenerator
SQLModelGenerator
SequelizeGenerator
PrismaGenerator
EloquentGenerator
EFCoreGenerator
```

---

## 13. Legacy DBF Architecture

DBF is treated as a generic legacy data source.

```text
DBF / DBT / FPT
       ↓
Legacy DBF Reader
       ↓
Legacy Type Mapper
       ↓
Universal Schema Model
       ↓
Migration Planner
       ↓
Target Database
```

Initial scope:

- DBF
- DBT
- FPT
- encoding
- deleted records
- streaming
- schema inference

Later:

- NTX
- CDX
- NSX

Rust is allowed early here when large-file streaming benefits justify it.

---

## 14. Legacy Modernization Architecture

```text
Legacy Project
     ↓
Source Scanner
     ↓
Language Analyzer
     ↓
Data Access Analyzer
     ↓
SQL Extractor
     ↓
Modernization Model
     ↓
Target Stack
     ↓
Block-by-Block Proposal
     ↓
Diff / Review
```

Targets:

```text
C# / .NET
Python
TypeScript / Node.js
```

Modernization must be incremental.

---

## 15. Workspace Architecture

Workspace files are ordinary files.

```text
project/
├── queries/
├── procedures/
├── functions/
├── migrations/
├── generated/
├── diagrams/
└── .backendide/
```

`.backendide/` may contain:

- tab state
- panel layout
- diagram positions
- generator preferences
- non-secret connection references

Never store passwords here.

---

## 16. Connection Profiles

Connection profiles contain:

```text
name
engine
host
port
database
username
environment
optional color
optional group
secure credential reference
```

Credentials are stored through `keyring`.

---

## 17. Theme Architecture

Theme options:

```text
System
Light
Dark
```

Quick toggle:

```text
☀️ / 🌙
```

Use centralized theme tokens.

No arbitrary widget-specific color definitions.

---

## 18. Rust Boundary

Initial Python-first policy:

```text
Python
├── Application
├── UI
├── Generators
├── DB adapters
├── Domain
└── Initial algorithms
```

Potential Rust modules:

```text
backend_ide_core
├── sql
├── schema_diff
├── graph
├── metadata_index
├── fuzzy
├── erd_layout
└── dbf
```

Python communicates with Rust using PyO3.

---

## 19. Proposed Repository Structure

```text
backend-development-ide/
├── src/
│   └── backend_ide/
│       ├── domain/
│       │   ├── schema/
│       │   ├── sql/
│       │   ├── generation/
│       │   └── workspace/
│       │
│       ├── application/
│       │
│       ├── infrastructure/
│       │   ├── database/
│       │   ├── storage/
│       │   ├── security/
│       │   └── logging/
│       │
│       ├── generators/
│       │   ├── python/
│       │   ├── typescript/
│       │   ├── php/
│       │   └── csharp/
│       │
│       ├── legacy/
│       │   ├── dbf/
│       │   └── modernization/
│       │
│       └── ui/
│           ├── components/
│           ├── explorer/
│           ├── editor/
│           ├── results/
│           ├── diagrams/
│           ├── dialogs/
│           └── theme/
│
├── rust/
│   └── backend_ide_core/
├── tests/
├── docs/
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 20. Dependency Direction

Allowed:

```text
UI
 ↓
Application
 ↓
Domain
```

Infrastructure implements Domain/Application contracts.

Forbidden:

```text
Domain → PySide6
Domain → psycopg
Domain → PyMySQL
Domain → pyodbc
Generators → live database connection
```

---

## 21. Architecture Review Rule

Any architectural change that alters:

- Universal Schema Model
- dependency direction
- generator contracts
- database inspector contracts
- Rust boundary
- workspace format

must be documented in:

```text
docs/DECISIONS.md
```

before being treated as permanent.
