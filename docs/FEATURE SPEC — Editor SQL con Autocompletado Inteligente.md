# FEATURE SPEC — Editor SQL con Autocompletado Inteligente

## Proyecto

**Manejador de Bases de Datos Multiplataforma**

Tecnología principal:

- Python 3.12+

- PySide6

- PostgreSQL

- MySQL / MariaDB

- SQLite

- SQL Server

La aplicación debe funcionar en:

- Linux

- Windows

- macOS

---

# 1. Objetivo

Implementar un **editor SQL profesional con autocompletado contextual**, similar al comportamiento esperado en herramientas como:

- DataGrip

- DBeaver

- Beekeeper Studio

- VS Code SQL extensions

El autocompletado NO debe limitarse a una lista estática de palabras SQL.

Debe conocer:

- conexión activa

- motor de base de datos

- base de datos

- schemas

- tablas

- vistas

- columnas

- aliases

- funciones

- procedimientos

- keywords SQL

El objetivo es que escribir consultas dentro del manejador sea rápido y agradable.

---

# 2. Principio fundamental

El autocompletado debe ser **contextual**.

Ejemplo:

```sql
SELECT u.
FROM users u
```

Al escribir:

```sql
u.
```

debe mostrar exclusivamente o prioritariamente las columnas de `users`.

Ejemplo:

```text
id
name
email
created_at
updated_at
```

No debe mostrar simplemente todas las columnas de todas las tablas.

---

# 3. Comportamiento básico

El editor debe mostrar sugerencias mientras el usuario escribe.

Ejemplo:

```sql
SEL
```

Debe sugerir:

```text
SELECT
```

Ejemplo:

```sql
SELECT * FR
```

Debe sugerir:

```text
FROM
```

Ejemplo:

```sql
SELECT *
FROM use
```

Debe sugerir tablas como:

```text
users
user_roles
user_sessions
```

---

# 4. Autocompletado de schemas

Ejemplo PostgreSQL:

```sql
SELECT *
FROM pub
```

Debe sugerir:

```text
public
```

Al escribir:

```sql
SELECT *
FROM public.
```

debe mostrar tablas y vistas del schema `public`.

Ejemplo:

```text
users
customers
reservations
payments
```

---

# 5. Autocompletado de tablas

Después de:

```sql
FROM
JOIN
UPDATE
INSERT INTO
DELETE FROM
```

deben sugerirse tablas compatibles con el contexto.

Ejemplo:

```sql
SELECT *
FROM res
```

Sugerencias:

```text
reservations
reservation_items
reservation_payments
```

La coincidencia no debe ser únicamente por prefijo.

Debe permitirse fuzzy matching.

Ejemplo:

```text
rsv
```

podría encontrar:

```text
reservations
```

si el sistema de scoring lo considera suficientemente relevante.

---

# 6. Autocompletado de columnas

Ejemplo:

```sql
SELECT
FROM reservations
```

Mientras el cursor está después de `SELECT`, deben sugerirse columnas de `reservations`.

Ejemplo:

```text
id
confirmation_number
customer_id
supplier_id
pickup_date
dropoff_date
total
status
created_at
```

---

# 7. Autocompletado usando aliases

Esto es obligatorio.

Consulta:

```sql
SELECT r.
FROM reservations r
```

Al escribir:

```sql
r.
```

mostrar columnas de:

```text
reservations
```

Ejemplo:

```text
id
customer_id
supplier_id
pickup_date
dropoff_date
status
```

---

# 8. JOIN inteligente

Ejemplo:

```sql
SELECT *
FROM reservations r
JOIN customers c ON c.
```

El sistema debe identificar:

```text
c = customers
```

y sugerir columnas de `customers`.

Después:

```sql
JOIN customers c ON c.id = r.
```

debe sugerir columnas de `reservations`.

---

# 9. Relaciones y Foreign Keys

Si existen foreign keys conocidas por metadata, el sistema puede dar prioridad a columnas relacionadas.

Ejemplo:

Tabla:

```text
reservations.customer_id
```

Foreign Key:

```text
reservations.customer_id -> customers.id
```

Al escribir:

```sql
JOIN customers c ON
```

sería conveniente priorizar sugerencias como:

```sql
c.id = r.customer_id
```

Esta funcionalidad puede implementarse como una segunda etapa, pero la arquitectura debe permitirla.

---

# 10. Funciones SQL

El autocompletado debe conocer funciones del motor activo.

Ejemplo PostgreSQL:

```text
COUNT
SUM
AVG
MIN
MAX
COALESCE
NULLIF
DATE_TRUNC
NOW
CURRENT_DATE
STRING_AGG
JSON_AGG
JSONB_BUILD_OBJECT
```

Ejemplo MySQL:

```text
COUNT
SUM
AVG
IFNULL
CONCAT
NOW
DATE_FORMAT
GROUP_CONCAT
JSON_OBJECT
```

Ejemplo SQL Server:

```text
COUNT
SUM
AVG
ISNULL
GETDATE
DATEADD
DATEDIFF
STRING_AGG
```

No asumir que todos los motores usan exactamente las mismas funciones.

---

# 11. Keywords por dialecto SQL

Crear proveedores de dialecto.

Ejemplo conceptual:

```python
class SQLDialectProvider:
    def keywords(self) -> list[str]:
        ...

    def functions(self) -> list[str]:
        ...

    def data_types(self) -> list[str]:
        ...
```

Implementaciones:

```text
PostgreSQLDialectProvider
MySQLDialectProvider
SQLiteDialectProvider
SQLServerDialectProvider
```

No llenar el editor con `if database == ...` distribuidos por el código.

---

# 12. Metadata de base de datos

Crear una capa independiente para obtener metadata.

Interfaz conceptual:

```python
class MetadataProvider:
    async def get_schemas(self):
        ...

    async def get_tables(self, schema=None):
        ...

    async def get_views(self, schema=None):
        ...

    async def get_columns(self, table, schema=None):
        ...

    async def get_foreign_keys(self, table, schema=None):
        ...

    async def get_functions(self):
        ...
```

Cada motor debe implementar su propio proveedor.

---

# 13. Metadata Cache

PROHIBIDO consultar la base de datos cada vez que el usuario escribe una letra.

Crear un cache local.

Ejemplo:

```text
ConnectionMetadataCache
```

Debe almacenar:

```text
schemas
tables
views
columns
foreign_keys
functions
procedures
```

El flujo correcto es:

```text
Conexión DB
    ↓
MetadataProvider
    ↓
MetadataCache
    ↓
AutocompleteEngine
    ↓
SQL Editor
```

---

# 14. Refresco de metadata

Agregar una acción:

```text
Refresh Metadata
```

El usuario debe poder refrescar manualmente:

- schemas

- tablas

- vistas

- columnas

- procedimientos

- funciones

También refrescar automáticamente cuando el usuario ejecute operaciones como:

```sql
CREATE TABLE
ALTER TABLE
DROP TABLE
CREATE VIEW
DROP VIEW
```

No es necesario hacer un parser SQL perfecto en la primera versión.

Puede utilizarse una detección inicial de DDL ejecutado correctamente.

---

# 15. AutocompleteEngine

Crear un componente central.

Ejemplo:

```python
class AutocompleteEngine:
    def complete(
        self,
        sql: str,
        cursor_position: int,
        metadata,
        dialect,
    ) -> list[CompletionItem]:
        ...
```

No poner toda la lógica dentro del widget Qt.

---

# 16. CompletionItem

Definir un modelo similar a:

```python
@dataclass
class CompletionItem:
    label: str
    insert_text: str
    kind: CompletionKind
    detail: str | None = None
    documentation: str | None = None
    score: float = 0
```

Tipos:

```python
class CompletionKind(Enum):
    KEYWORD = "keyword"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    SCHEMA = "schema"
    FUNCTION = "function"
    PROCEDURE = "procedure"
    DATA_TYPE = "data_type"
    ALIAS = "alias"
    SNIPPET = "snippet"
```

---

# 17. Ranking

No ordenar simplemente alfabéticamente.

Usar ranking.

Prioridad aproximada:

```text
1. coincidencia exacta
2. comienza con texto escrito
3. contexto SQL
4. alias actual
5. columnas de tabla activa
6. tablas del schema activo
7. fuzzy match
8. keywords genéricos
```

Ejemplo:

Si escribe:

```sql
SELECT us
FROM users
```

Debe priorizar:

```text
username
user_status
```

antes que:

```text
USING
```

si el contexto indica claramente que está seleccionando columnas.

---

# 18. Popup visual

El popup debe verse moderno.

Cada tipo debe tener un icono o indicador.

Ejemplo:

```text
▤ users                 table
▥ user_roles            table
◇ username              column
◇ user_id               column
ƒ COUNT                  function
K SELECT                 keyword
```

No utilizar colores chillones.

Debe integrarse con:

- dark mode

- light mode

---

# 19. Información adicional

Cuando una sugerencia esté seleccionada debe poder mostrarse información adicional.

Ejemplo columna:

```text
email
varchar(255)
NOT NULL
```

Ejemplo:

```text
customer_id
bigint
FK -> customers.id
```

Ejemplo función:

```text
COUNT(expression)

Returns the number of input rows.
```

---

# 20. Navegación del popup

Soportar:

```text
Arrow Up
Arrow Down
Enter
Tab
Escape
```

Comportamiento:

`Enter`

acepta sugerencia.

`Tab`

también puede aceptar sugerencia.

`Escape`

cierra popup.

---

# 21. Activación manual

Atajo obligatorio:

```text
Ctrl + Space
```

Debe abrir el autocompletado aunque el sistema no lo haya mostrado automáticamente.

En macOS considerar:

```text
Cmd + Space
```

si no genera conflicto con el sistema operativo.

---

# 22. Activación con punto

Cuando se escriba:

```text
.
```

debe dispararse inmediatamente el autocompletado contextual.

Ejemplo:

```sql
r.
```

---

# 23. Debounce

No ejecutar análisis pesado en cada tecla.

Implementar debounce aproximado:

```text
100–200 ms
```

El editor debe sentirse instantáneo.

No debe congelar la UI.

---

# 24. Threads / Async

La carga de metadata NO debe ejecutarse en el hilo principal de Qt si puede bloquear la interfaz.

Utilizar apropiadamente:

```text
QThread
QThreadPool
QRunnable
asyncio
```

o la arquitectura async que ya utilice el proyecto.

El usuario nunca debe experimentar congelamientos por cargar metadata.

---

# 25. Parser SQL

Separar el análisis de SQL del UI.

Crear inicialmente:

```text
SQLContextAnalyzer
```

Debe detectar por lo menos:

```text
statement actual
cursor position
FROM tables
JOIN tables
aliases
schema actual
token anterior
contexto del cursor
```

Ejemplo:

```python
context = analyzer.analyze(sql, cursor_position)
```

resultado aproximado:

```python
SQLContext(
    clause="SELECT",
    current_token="u",
    aliases={
        "u": "users"
    },
    tables=["users"]
)
```

---

# 26. Preparar arquitectura para parser avanzado

No implementar regex gigantescas imposibles de mantener.

Puede usarse una combinación inicial de:

```text
tokenizer
state machine
parser SQL
```

Evaluar bibliotecas existentes si reducen complejidad, pero evitar introducir dependencias pesadas sin necesidad.

La lógica debe ser testeable independientemente de Qt.

---

# 27. Snippets SQL

Agregar snippets básicos.

Por ejemplo escribir:

```text
sel
```

puede sugerir:

```sql
SELECT *
FROM table_name;
```

`ins`:

```sql
INSERT INTO table_name (
    column
)
VALUES (
    value
);
```

`upd`:

```sql
UPDATE table_name
SET column = value
WHERE condition;
```

`ct`:

```sql
CREATE TABLE table_name (
    id BIGINT PRIMARY KEY
);
```

Los snippets deben poder extenderse posteriormente.

---

# 28. Completion de INSERT

Ejemplo:

```sql
INSERT INTO users (
```

debe mostrar columnas de:

```text
users
```

Idealmente excluir columnas autogeneradas cuando se conozca la metadata.

Por ejemplo:

```text
id SERIAL
created_at DEFAULT NOW()
```

podrían tener menor prioridad.

---

# 29. Completion de UPDATE

Ejemplo:

```sql
UPDATE users
SET
```

mostrar columnas de `users`.

Después:

```sql
UPDATE users
SET ema
```

priorizar:

```text
email
```

---

# 30. Completion de WHERE

Ejemplo:

```sql
SELECT *
FROM reservations r
WHERE r.
```

mostrar columnas de `reservations`.

---

# 31. Completion de ORDER BY

Ejemplo:

```sql
SELECT *
FROM reservations r
ORDER BY r.
```

mostrar columnas.

---

# 32. Completion de GROUP BY

Ejemplo:

```sql
SELECT supplier_id, COUNT(*)
FROM reservations
GROUP BY
```

mostrar columnas de `reservations`.

---

# 33. Múltiples tablas

Ejemplo:

```sql
SELECT
FROM reservations r
JOIN customers c ON c.id = r.customer_id
```

En `SELECT` deben estar disponibles:

```text
r.id
r.customer_id
r.total
c.id
c.name
c.email
```

pero agrupados visualmente por tabla o alias cuando sea posible.

---

# 34. Subqueries

La arquitectura debe permitir posteriormente soportar:

```sql
SELECT *
FROM (
    SELECT *
    FROM reservations
) r
WHERE r.
```

No es obligatorio resolver todos los casos complejos en la primera implementación.

Pero no diseñar una solución que impida agregarlo posteriormente.

---

# 35. CTE

Preparar soporte para:

```sql
WITH active_users AS (
    SELECT *
    FROM users
    WHERE active = true
)
SELECT *
FROM active_users;
```

Una CTE debe poder convertirse posteriormente en una fuente de autocompletado.

---

# 36. Performance

Objetivo:

El popup de sugerencias debe aparecer prácticamente de inmediato.

Objetivo razonable:

```text
< 100 ms
```

para consultas normales cuando la metadata ya esté en cache.

Bases con miles de tablas no deben congelar la aplicación.

---

# 37. Virtualización

Si existen miles de resultados, no crear miles de widgets Qt.

Usar:

```text
model/view architecture
```

Preferentemente:

```text
QAbstractListModel
QListView
```

o equivalente.

Evitar crear un QPushButton/QLabel por resultado.

---

# 38. Arquitectura sugerida

Estructura aproximada:

```text
src/
├── editor/
│   ├── sql_editor.py
│   ├── autocomplete/
│   │   ├── autocomplete_engine.py
│   │   ├── completion_item.py
│   │   ├── completion_model.py
│   │   ├── completion_popup.py
│   │   ├── context_analyzer.py
│   │   ├── fuzzy_matcher.py
│   │   └── snippet_provider.py
│   │
│   └── syntax/
│       ├── sql_highlighter.py
│       └── dialect_highlighter.py
│
├── database/
│   ├── metadata/
│   │   ├── metadata_provider.py
│   │   ├── metadata_cache.py
│   │   ├── postgres_metadata.py
│   │   ├── mysql_metadata.py
│   │   ├── sqlite_metadata.py
│   │   └── sqlserver_metadata.py
│   │
│   └── dialects/
│       ├── base.py
│       ├── postgres.py
│       ├── mysql.py
│       ├── sqlite.py
│       └── sqlserver.py
```

Adaptar los paths a la arquitectura real del repositorio.

NO reorganizar todo el proyecto innecesariamente si ya existe una estructura válida.

---

# 39. Separación de responsabilidades

El editor:

```text
SQL Editor
```

NO debe conocer cómo PostgreSQL obtiene sus columnas.

El editor únicamente debe consumir:

```text
AutocompleteEngine
```

El engine consume:

```text
MetadataCache
SQLContextAnalyzer
DialectProvider
SnippetProvider
```

---

# 40. Tests obligatorios

Crear tests REALES.

No tests vacíos.

No mocks que únicamente prueben que el propio mock funciona.

Casos mínimos:

### Keywords

```text
SEL -> SELECT
```

### Tabla

Metadata:

```text
users
customers
reservations
```

Entrada:

```sql
SELECT * FROM use
```

Resultado esperado:

```text
users
```

### Alias

```sql
SELECT u.
FROM users u
```

Resultado:

columnas de `users`.

### JOIN

```sql
SELECT *
FROM users u
JOIN orders o ON o.
```

Resultado:

columnas de `orders`.

### Schema

```sql
SELECT *
FROM public.
```

Resultado:

tablas/vistas de `public`.

### UPDATE

```sql
UPDATE users
SET ema
```

Resultado:

```text
email
```

### INSERT

```sql
INSERT INTO users (
```

Resultado:

columnas de `users`.

### WHERE

```sql
SELECT *
FROM users u
WHERE u.
```

Resultado:

columnas de `users`.

---

# 41. Pruebas por motor

Probar al menos:

```text
PostgreSQL
SQLite
```

desde la primera implementación.

Posteriormente:

```text
MySQL
SQL Server
```

Pero la arquitectura debe soportar los cuatro desde ahora.

---

# 42. Reglas importantes para Codex

NO realizar cambios masivos sin necesidad.

NO reemplazar componentes funcionales solamente para acomodar esta feature.

NO dejar archivos vacíos.

NO considerar una tarea terminada únicamente porque los tests existentes están verdes.

NO crear tests triviales para aparentar cobertura.

NO eliminar funcionalidades existentes.

NO cambiar APIs públicas sin necesidad.

NO introducir dependencias grandes sin justificarlo.

---

# 43. Antes de programar

Primero revisar el repositorio completo relacionado con:

```text
editor
SQL editor
database connections
metadata
models
UI
tests
```

Identificar qué componentes existentes pueden reutilizarse.

Después entregar brevemente:

```text
1. Estado actual
2. Componentes encontrados
3. Componentes que faltan
4. Archivos que serán modificados
5. Archivos nuevos
6. Estrategia de implementación
```

Después comenzar la implementación.

No inventar clases que ya existan con otro nombre.

---

# 44. Criterio de terminado

La feature NO está terminada hasta que pueda demostrarse algo como:

```sql
SELECT r.
FROM reservations r
```

y aparezca un popup con columnas reales de la tabla `reservations`.

También debe funcionar:

```sql
SELECT *
FROM customers c
WHERE c.
```

y:

```sql
SELECT *
FROM reservations r
JOIN customers c ON c.
```

---

# 45. UX esperada

El usuario debe sentir que está usando un editor de desarrollo profesional.

La experiencia debe ser:

```text
rápida
limpia
predecible
contextual
útil
no invasiva
```

No llenar la pantalla de sugerencias irrelevantes.

Mostrar primero lo que probablemente necesita el usuario.

---

# 46. Primera entrega

La primera entrega funcional debe incluir:

- keywords SQL

- tablas

- vistas

- schemas

- columnas

- aliases

- funciones

- `Ctrl + Space`

- popup automático

- activación con `.`

- fuzzy search

- metadata cache

- soporte inicial PostgreSQL

- soporte inicial SQLite

- tests reales

- integración con dark/light theme

---

# 47. Segunda entrega

Posteriormente agregar:

- MySQL

- SQL Server

- Foreign Key suggestions

- JOIN suggestions

- CTE

- subqueries

- procedures

- advanced snippets

- documentación de funciones

- signature help

- parámetros de funciones

---

# 48. Objetivo final

Queremos que el editor pueda evolucionar hacia una experiencia similar a un IDE.

Ejemplo final:

```sql
SELECT
    r.id,
    r.confirmation_number,
    c.name,
    c.email
FROM reservations r
JOIN customers c
    ON c.id = r.customer_id
WHERE r.status = 'confirmed'
ORDER BY r.created_at DESC;
```

Mientras el usuario escribe, el manejador debe comprender razonablemente el contexto y asistirlo con:

```text
schemas
tables
views
columns
aliases
relationships
functions
keywords
snippets
```

sin bloquear la UI y sin realizar consultas innecesarias contra la base de datos.

---

# Instrucción final para Codex

Inspecciona primero el código real del repositorio.

Implementa esta funcionalidad siguiendo la arquitectura existente siempre que sea razonable.

Prioriza calidad sobre cantidad.

No marques la tarea como terminada hasta haber ejecutado los tests y comprobado manualmente que el autocompletado funciona con metadata real.

Al finalizar entrega:

1. resumen de implementación;

2. archivos creados;

3. archivos modificados;

4. decisiones arquitectónicas;

5. tests ejecutados;

6. resultado de los tests;

7. funcionalidades verificadas manualmente;

8. limitaciones conocidas;

9. deuda técnica pendiente;

10. siguiente paso recomendado.
