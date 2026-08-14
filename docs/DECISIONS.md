# DECISIONS.md

# Backend Development IDE — Architecture & Product Decisions

This document records important product and technical decisions.

Each decision should remain concise and explain:

- Decision
- Reason
- Consequences
- Status

---

# ADR-001 — Product Category

**Decision:** The product is a **Backend Development IDE**, not only a Database Manager.

**Reason:** The product combines database management, SQL tooling, ER diagrams, backend generation, schema diff, Code First/Database First, and legacy modernization.

**Consequences:**

- UX must support multiple workflows
- Database schema intelligence becomes central
- Product positioning is developer-first

**Status:** Accepted

---

# ADR-002 — Desktop Application

**Decision:** Build an independent desktop application for Windows, Linux, and macOS.

**Reason:** DBA/backend workflows benefit from native desktop interaction, filesystem access, large data grids, keyboard workflows, and local project integration.

**Consequences:**

- Cross-platform design from day one
- No browser-only architecture
- No Docker requirement for running the IDE

**Status:** Accepted

---

# ADR-003 — Python + PySide6

**Decision:** Use Python + PySide6 + Qt 6 for the application.

**Reason:**

- Rapid development
- Strong desktop capabilities
- Mature Qt ecosystem
- Good fit for database tooling
- Good fit for code generation and analysis

**Consequences:**

- Python remains the orchestration/application language
- Qt Widgets are the primary desktop UI foundation

**Status:** Accepted

---

# ADR-004 — Rust for Performance-Critical Components

**Decision:** Use Rust instead of C++ for native performance components.

**Reason:**

- Modern systems language
- Strong performance
- Memory safety
- Good Python integration via PyO3
- Suitable for parsers, graph algorithms, indexing, and binary legacy formats

**Consequences:**

- Rust is not required everywhere
- Python-first implementations remain preferred until performance justifies migration

**Status:** Accepted

---

# ADR-005 — PyO3 + maturin

**Decision:** Use PyO3 + maturin for Python/Rust integration.

**Reason:** Clean Python module integration and practical cross-platform packaging.

**Consequences:**

- Rust APIs must expose stable, minimal boundaries
- Avoid leaking Rust implementation details into the UI

**Status:** Accepted

---

# ADR-006 — QScintilla for SQL Editing

**Decision:** Use QScintilla as the SQL editing surface.

**Reason:**

- Advanced editor features
- Line numbers
- Folding
- markers
- indicators
- autocomplete UI
- good Qt integration

**Consequences:**

QScintilla must remain a view/editor surface only.

Semantic SQL logic must remain external.

**Status:** Accepted

---

# ADR-007 — Universal Schema Model

**Decision:** All schema-aware features must use a neutral Universal Schema Model.

**Reason:** Required to support multiple databases, ORMs, Code First, Database First, ERD, diff, DBF and generation without tight coupling.

**Consequences:**

All engines and parsers normalize into the same representation.

All generators consume the same representation.

**Status:** Accepted

---

# ADR-008 — Supported Tier 1 Databases

**Decision:** Initial relational database support:

```text
PostgreSQL
MySQL / MariaDB
SQLite
Microsoft SQL Server
```

**Reason:** High practical coverage across backend, enterprise, web, desktop, and local development.

**Consequences:**

- Four inspectors
- Four dialect layers
- Four adapter implementations

**Status:** Accepted

---

# ADR-009 — Generic DBF Support

**Decision:** Support DBF as a generic legacy data source instead of presenting FoxPro/Clipper as fully supported database engines.

**Reason:** The goal is migration and modernization, not runtime emulation.

**Initial scope:**

```text
DBF
DBT
FPT
Encoding
Deleted records
Schema inference
Streaming
```

**Later:**

```text
NTX
CDX
NSX
```

**Status:** Accepted

---

# ADR-010 — ORM and Non-ORM

**Decision:** The product must support both ORM and direct/native data access.

**Reason:** ORM is not always the correct solution.

**Consequences:**

Generators must support both paradigms.

**Status:** Accepted

---

# ADR-011 — Python Ecosystem

**Decision:** Planned Python support:

```text
FastAPI
Flask
Django
SQLAlchemy
SQLModel
Django ORM
Native SQL
```

**Status:** Accepted

---

# ADR-012 — TypeScript / Node.js Ecosystem

**Decision:** Planned traditional Node frameworks:

```text
NestJS
Fastify
Express
```

Planned data access:

```text
Sequelize
Prisma
TypeORM
Drizzle
Native SQL
```

**Status:** Accepted

---

# ADR-013 — Sequelize is First-Class

**Decision:** Sequelize is a first-class ORM option, not a legacy-only option.

**Reason:** Strong productivity, simple model relationships, broad SQL database support, and continued practical relevance.

**Consequences:**

- Sequelize generator receives full support
- Sequelize should be included in early generator milestones

**Status:** Accepted

---

# ADR-014 — PHP Ecosystem

**Decision:** Planned PHP support:

```text
Laravel + Eloquent
Symfony + Doctrine
PDO
```

**Reason:** PHP remains highly relevant for web and legacy modernization.

**Status:** Accepted

---

# ADR-015 — C# Ecosystem

**Decision:** Planned C# support:

```text
ASP.NET Core
Entity Framework Core
Dapper
ADO.NET
```

**Reason:** Strong enterprise usage and major relevance for SQL Server / VB.NET modernization.

**Status:** Accepted

---

# ADR-016 — Serverless is Contextual

**Decision:** Serverless/Edge options only appear when the user explicitly selects that deployment model.

**Reason:** Avoid clutter and inappropriate stack suggestions in normal backend workflows.

**Consequences:**

Hono is not shown in the default traditional server flow.

**Status:** Accepted

---

# ADR-017 — Hono for Serverless / Edge

**Decision:** Hono may be offered primarily for serverless and edge workflows.

**Reason:** Strong fit for Web Standards, Cloudflare Workers, Lambda-style deployment, and portable runtimes.

**Status:** Accepted

---

# ADR-018 — No Docker Requirement

**Decision:** Docker is not required to run the desktop application.

**Reason:** The IDE must install and run independently.

**Consequences:**

Dockerfiles or compose files may only be optional generated project artifacts.

**Status:** Accepted

---

# ADR-019 — Workspace Uses Real Files

**Decision:** User work must be stored as normal files whenever possible.

Examples:

```text
.sql
.py
.ts
.php
.cs
.json
.yaml
.md
```

**Reason:** Users must own and version their work outside the IDE.

**Status:** Accepted

---

# ADR-020 — Internal Workspace Folder

**Decision:** Use `.backendide/` for workspace-specific state.

**May contain:**

- panel state
- open tabs
- diagram positions
- non-secret preferences

**Must NOT contain:**

- passwords
- connection secrets

**Status:** Accepted

---

# ADR-021 — Connection Profiles

**Decision:** Saved database connections include:

```text
Name
Engine
Host
Port
Database
Username
Environment
Optional color
Optional group
Secure credential reference
```

**Status:** Accepted

---

# ADR-022 — Connection Color

**Decision:** Connection profiles may have an optional color.

**Reason:** Fast visual identification of production, staging, development, client systems, etc.

**Consequences:**

The color may appear in:

- explorer
- tabs
- status bar
- ERD context

**Status:** Accepted

---

# ADR-023 — Explicit Environment

**Decision:** Connection environment is separate from connection color.

Values:

```text
Development
Testing
Staging
Production
```

**Reason:** Safety must not depend on color alone.

**Status:** Accepted

---

# ADR-024 — Production Safety

**Decision:** Dangerous SQL against Production requires explicit warning.

Examples:

```text
DELETE without WHERE
UPDATE without WHERE
DROP
TRUNCATE
```

**Status:** Accepted

---

# ADR-025 — Dark / Light Quick Toggle

**Decision:** Add a compact `☀️ / 🌙` toggle to the top bar.

**Reason:** Fast and intuitive theme switching.

**Additional settings:**

```text
System
Light
Dark
```

**Status:** Accepted

---

# ADR-026 — Design System from Early Development

**Decision:** UI quality is a first-class feature.

**Reason:** The product targets daily-use professional workflows and must remain intuitive despite complexity.

**Consequences:**

Build reusable design tokens/components early.

**Status:** Accepted

---

# ADR-027 — ER Diagram

**Decision:** Include an interactive ER diagram.

Modes:

```text
Explore
Design
```

**Reason:** Schema visualization is central for DBA/backend/full-stack users.

**Status:** Accepted

---

# ADR-028 — ERD Does Not Directly Mutate DB

**Decision:** Visual design changes first produce a schema diff and SQL preview.

**Flow:**

```text
Visual Change
 ↓
Diff
 ↓
SQL Preview
 ↓
Confirmation
 ↓
Apply
```

**Status:** Accepted

---

# ADR-029 — Database First

**Decision:** Database First is a first-class workflow.

```text
Database
 ↓
Universal Schema Model
 ↓
Code
```

**Status:** Accepted

---

# ADR-030 — Code First

**Decision:** Code First is a first-class workflow.

```text
ORM / Models
 ↓
Parser
 ↓
Universal Schema Model
 ↓
Migration
```

**Status:** Accepted

---

# ADR-031 — Hybrid Sync

**Decision:** Long-term support bidirectional database/code synchronization.

**Reason:** Real projects often mix Database First and Code First practices.

**Constraint:** Destructive changes are never auto-applied.

**Status:** Accepted

---

# ADR-032 — Legacy Modernization

**Decision:** Include legacy modernization as a major product area.

Initial sources:

```text
PHP
VB.NET
C#
DBF
```

Later:

```text
Node.js
Python
Visual FoxPro source
```

**Status:** Accepted

---

# ADR-033 — Legacy Upgrade Targets

**Decision:** Initial modernization targets:

```text
C# / .NET
Python
TypeScript / Node.js
```

**Status:** Accepted

---

# ADR-034 — Incremental Modernization

**Decision:** Legacy migration must support incremental, block-by-block modernization.

Classification:

```text
Safe
Review
Manual
```

**Reason:** Large legacy systems should not be blindly rewritten.

**Status:** Accepted

---

# ADR-035 — ORM Migration Is Not Mandatory

**Decision:** The modernization engine may recommend keeping raw SQL.

**Reason:** Complex reporting, CTEs, window functions, vendor-specific optimizations, or high-performance SQL may remain better as SQL.

**Status:** Accepted

---

# ADR-036 — Legacy Upgrade Reports

**Decision:** Eventually generate modernization/upgrade reports.

Formats:

```text
Markdown
HTML
DOCX
PDF
```

**Status:** Accepted

---

# ADR-037 — No Blind Overwrites

**Decision:** Generated code must not silently overwrite existing project files.

Options:

```text
Skip
Show Diff
Replace
```

Preferred:

```text
Show Diff
```

**Status:** Accepted

---

# ADR-038 — Python First, Rust When Measured

**Decision:** Implement in Python first unless the component has a strong reason to be native.

Likely Rust targets:

```text
SQL analysis
Schema diff
Metadata indexing
Dependency graphs
ERD layout
DBF streaming
```

**Status:** Accepted

---

# ADR-039 — Cross-Platform Build Policy

**Decision:** Build each target platform on that platform.

```text
Windows runner → Windows artifacts
Linux runner   → Linux artifacts
macOS runner   → macOS artifacts
```

**Status:** Accepted

---

# ADR-040 — Initial Architecture Validation

**Decision:** Before expanding aggressively, validate:

```text
PostgreSQL
 ↓
Universal Schema Model
 ↓
Generate:
SQLAlchemy
SQLModel
Sequelize
Prisma
Eloquent
EF Core
```

**Reason:** This proves the central architecture before building too much around it.

**Status:** Accepted
