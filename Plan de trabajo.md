## Plan de trabajo

### Fase 0 — Definición del producto

**Objetivo:** cerrar alcance y arquitectura antes de programar.

Entregables:

- Nombre provisional del proyecto.
- Alcance de v0.1, MVP y v1.0.
- Arquitectura general.
- Convenciones de código.
- Estructura del repositorio.
- Decisión final de stack.
- Documento de capacidades soportadas por motor.

Stack base:

```
Python 3.14+
PySide6
QScintilla

psycopg 3
PyMySQL
sqlite3
pyodbc

SQLAlchemy Core
Pydantic
sqlglot
RapidFuzz
keyring

pytest
pytest-qt
uv (gestor de paquetes y venv)
ruff (linter y formateador)
Nuitka

### Fase 1 — Universal Schema Model

```

**Objetivo:** construir el corazón del producto.

Debe representar de forma neutral:

```
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
Function
Procedure
Trigger
Relationship
```

Por ejemplo:

```
DatabaseSchema
 └── schemas[]      
 └── tables[]           
     ├── columns[]           
     ├── indexes[]           
     ├── foreign_keys[]           
     └── constraints[]
```

Aquí no debe existir lógica específica de:

```
PostgreSQL
Prisma
SQLAlchemy
Laravel
EF Core
```

Es el modelo común de todo el sistema.

**Criterio de terminado:** cargar un esquema ficticio y serializarlo/deserializarlo sin depender de ningún motor.

---

### Fase 2 — PostgreSQL Inspector

**Objetivo:** primera implementación real Database First.

Soportar:

```
Schemas
Tables
Columns
PK
FK
Indexes
Unique
Checks
Defaults
Sequences
Views
Materialized 
Views
Functions
Triggers
```

Flujo:

```
PostgreSQL
    ↓
PostgreSQLInspector
    ↓
Universal Schema Model
```

Pruebas con bases pequeñas, medianas y una BD con muchas tablas.

**Milestone importante:** conectar a PostgreSQL y ver correctamente todo el esquema convertido al modelo universal.

---

### Fase 3 — Shell de aplicación PySide6

**Objetivo:** tener ya una aplicación desktop funcional.

Primera UI:

```
┌─────────────────────────────────────────────┐
│ Menu                                        │
├───────────────┬─────────────────────────────┤
│ Connections                                 |  
│               │       Workspace             |
│ PostgreSQL    │                             │
│ └─ database   │                             │
│    └─ public  │                             │
│       └─ ...  │                             │
├───────────────┴─────────────────────────────┤
│ Status                                      │
└─────────────────────────────────────────────┘
```

Implementar:

- administrador de conexiones;
- guardar perfiles;
- credenciales con `keyring`;
- conexión/desconexión;
- árbol de objetos;
- lazy loading;
- refresh de metadata;
- tabs principales.

Aquí todavía no necesitamos el editor SQL completo.

---

### Fase 4 — Ejecutor SQL

**Objetivo:** convertir la app en un cliente SQL realmente utilizable.

Agregar:

- ejecutar query;
- ejecutar selección;
- múltiples statements;
- cancelación;
- transacciones;
- commit/rollback;
- tiempo de ejecución;
- número de filas;
- errores;
- resultados tabulares;
- paginación;
- exportar CSV/JSON.

Muy importante:

```
UI Thread
   │
   └── NO ejecuta queries
```

Todo pasa por:

```
QThreadPool
QRunnable
Workers
```

---

### Fase 5 — Editor SQL avanzado

Aquí empezamos con uno de los grandes diferenciadores.

Primera versión:

```
QScintilla
├── Syntax highlighting
├── Line numbers
├── Folding
├── Brace matching
├── Current line
├── Multi-selection
├── Search/replace
└── Shortcuts
```

Después nuestro motor:

```
SQL Language Engine
├── Parser
├── Dialect
├── Completion Engine
├── Semantic Analyzer
├── Diagnostics
├── Formatter
└── Snippets
```

Autocomplete:

```
SELECT c.
```

```
id
name
email
created_at
```

Entender:

- aliases;
- tablas;
- columnas;
- schemas;
- funciones;
- palabras reservadas;
- tipos.

---

### Fase 6 — Metadata Cache + IntelliSense

**Objetivo:** que el editor se sienta rápido.

Al conectar:

```
Database
    ↓
Metadata Cache
    ↓
RAM

No consultar la BD por cada tecla.

```

Agregar:

- fuzzy matching;
- ranking de sugerencias;
- columnas por alias;
- autocompletado por contexto;
- nombres cualificados;
- funciones según dialecto.

Y una función clave:

```
FROM reservations r
JOIN
↓
customer
ssuppliers
payments
```

basado en Foreign Keys.

---

### Fase 7 — MySQL, SQLite y SQL Server

Una vez demostrado PostgreSQL:

```
DatabaseInspector
├── PostgreSQLInspector
├── MySQLInspector
├── SQLiteInspector
└── SQLServerInspector
```

Cada uno produce exactamente:

```
Universal Schema Model
```

También agregar dialectos:

```
SQLDialect
├── PostgreSQLDialect
├── MySQLDialect
├── SQLiteDialect
└── TSQLDialect
```

Este punto marca nuestro **MVP real de Database IDE**.

---

### Fase 8 — Generador de modelos

Primera versión de Code Generation.

Outputs iniciales:

```
Python
├── SQLAlchemy
└── SQLModel

TypeScript
├── Prisma
└── TypeORM

PHP
└── Eloquent

C#
└── Entity Framework Core

```

Una tabla:

```
customers
```

debe poder producir todos esos modelos desde el mismo `Universal Schema Model`.

Aquí validamos definitivamente que la arquitectura funciona.

---

### Fase 9 — Generación sin ORM

Agregar:

```
Python
├── psycopg
├── asyncpg
└── pyodbc

TypeScript
├── pg
├── mysql2
└── mssql

PHP
└── PDO

C#
├── Dapper
└── ADO.NET

```

Generando:

- repositories;
- consultas parametrizadas;
- mappings;
- CRUD básico.

Así no casamos el producto con los ORM.

---

### Fase 10 — Backend Generator

Ahora pasamos de:

```
Generate Model
```

a:

```
Generate Backend
```

Primera matriz:

```
Python
└── FastAPI
    ├── SQLAlchemy
    └── SQLModel

TypeScript
└── NestJS
    ├── Prisma
    └── TypeORM

PHP
└── Laravel
    └── Eloquent

C#
└── ASP.NET Core
    └── EF Core

```

Generar:

```
Models
DTOs
Schemas
Repositories
Services
Controllers
Routes
Validation
CRUD
Pagination
Filters
OpenAPI
Tests
.env.example
Dockerfile
```

---

### Fase 11 — ER Diagram

El segundo gran diferenciador visual.

Implementar:

- tablas como nodos;
- PK/FK;
- relaciones;
- zoom;
- pan;
- búsqueda;
- auto-layout;
- mover nodos;
- esconder tablas;
- focus mode;
- relaciones a uno/dos niveles.

Luego modo diseñador:

```
Explore
Design
```

En Design:

- agregar columnas;
- crear FK;
- cambiar tipos;
- agregar índices;
- renombrar;
- crear tablas.

Nunca aplicar directamente.

Primero:

```
Visual change
    ↓
Schema Diff
    ↓
SQL Preview
    ↓
Apply
```

---

### Fase 12 — Database First / Code First

Aquí ya soportamos oficialmente ambos sentidos.

```
DATABASE FIRST

Database
   ↓
Schema
   ↓
Models / Backend

```

y:

```
CODE FIRST

Models
   ↓
Parser
   ↓
Schema Model
   ↓
Migration
   ↓
Database

```

Primeros parsers:

```
SQLAlchemy
SQLModel
Prisma
Eloquent
EF Core
```

---

### Fase 13 — Schema Diff Engine

Esta pieza es crítica.

Comparaciones:

```
DB ↔ DB
DB ↔ ORM
ORM ↔ ORM
Code ↔ Database
```

Mostrar:

```
+ agregado
- eliminado
~ modificado

```

Ejemplo:

```
customers.phone                 +
customers.email VARCHAR(150)    → VARCHAR(255)
customers.legacy_code           -
```

y generar migración.

---

### Fase 14 — Sync / Hybrid Mode

Aquí llegamos a una función muy diferenciadora:

```
Database ←→ Code
```

Mostrar:

```
Database                    ORM
────────────────────────────────────
users.id             ✓      users.id
users.email          ✓      users.email
users.phone          →      missing
                     ←      users.avatar
```

Y permitir decidir dirección por cambio.

---

### Fase 15 — EXPLAIN / Performance

Especialmente fuerte para PostgreSQL y SQL Server.

Agregar:

- EXPLAIN;
- EXPLAIN ANALYZE;
- árbol visual;
- scans;
- joins;
- costos;
- buffers;
- tiempos;
- detección de posibles problemas.

También:

- índices;
- índices no usados;
- duplicados;
- FK sin índice;
- queries lentas.

---

### Fase 16 — Proyecto y workspace

El usuario debería poder abrir un proyecto:

```
my-backend.workspace
```

que recuerde:

```
Connections
Open tabs
Queries
ER diagrams
Code generator settings
Favorites
Snippets
Architecture profile
```

Eso hace que el producto se convierta en herramienta diaria.

---

## Qué NO haría al principio

No empezaría todavía con:

```
AI
Git
Cloud sync
Oracle
MongoDB
Redis
Kafka
Deployment
Kubernetes
```

Pueden llegar después.

Primero debemos ser excepcionales en:

```
SQL
Relational Databases
Schema
Models
Backend Generation
```

---

## Roadmap resumido

```
FOUNDATION
01 Universal Schema Model
02 PostgreSQL Inspector
03 PySide6 Shell
04 Query Executor

SQL IDE
05 Advanced Editor
06 IntelliSense / Metadata Cache
07 MySQL / SQLite / SQL Server

CODE GENERATION
08 ORM Models
09 Native DB Access
10 Backend Generator

VISUAL DATABASE
11 ER Diagram
12 Code First / Database First
13 Schema Diff
14 Hybrid Sync

ADVANCED
15 Query Performance
16 Projects / Workspaces

```

## El primer objetivo que yo pondría al equipo

No sería “hacer una ventana bonita”.

Sería conseguir esta demo:

```
Conectar PostgreSQL
        ↓
Leer customers
        ↓
Mostrar:
columns
PK
FK
indexes
        ↓
Visualizarla en la aplicación
        ↓
Generate
├── SQLAlchemy
├── SQLModel
├── Prisma
├── Eloquent
└── EF Core
```

Cuando esa demo funcione bien, tendremos comprobado el **núcleo arquitectónico del producto**. A partir de ahí podremos crecer sin convertir el código en un monstruo.


