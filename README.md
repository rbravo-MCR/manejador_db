# Backend Development IDE

**Aplicación de escritorio profesional y multiplataforma** para trabajar con bases de datos
relacionales, explorar esquemas, escribir y ejecutar SQL y, progresivamente, generar modelos y
backends desde una representación universal del esquema. Está diseñada para ejecutarse de forma
nativa en Windows, Linux y macOS, sin depender de un navegador.

> [!IMPORTANT]
> El proyecto se encuentra en estado **pre-alpha**. La arquitectura base y varios flujos ya
> cuentan con pruebas, pero la aplicación todavía no está preparada para usarse contra bases de
> datos de producción.

## Visión

Backend Development IDE busca reunir en una sola aplicación de escritorio:

- administración y exploración de PostgreSQL, MySQL/MariaDB, SQLite y SQL Server;
- editor SQL con asistencia basada en metadatos;
- ejecución no bloqueante y visualización de resultados;
- modelo universal de esquemas independiente del motor;
- diagramas ER, comparación y sincronización de esquemas;
- generación de modelos, acceso SQL nativo y backends;
- herramientas de migración y modernización de sistemas legacy.

## Estado actual

Actualmente el repositorio incluye:

- modelo universal de esquemas con serialización JSON;
- inspector y adaptador inicial para PostgreSQL;
- perfiles de conexión con secretos almacenados mediante el keyring del sistema;
- shell de escritorio construido con PySide6;
- explorador de objetos de base de datos;
- editor SQL con resaltado, números de línea y completado básico;
- ejecución de consultas mediante `QThreadPool` y `QRunnable`;
- grid de resultados y exportación a CSV y JSON;
- temas oscuro y claro;
- 31 pruebas automatizadas.

La conexión completa entre todos los controles de la interfaz y una base real, el sistema de
seguridad para entornos de producción y el nuevo diseño visual todavía están en desarrollo.

## Requisitos

- Python **3.14.4**
- [`uv`](https://docs.astral.sh/uv/)
- dependencias nativas requeridas por Qt, keyring y los drivers de base de datos del sistema

## Instalación

```bash
git clone https://github.com/rbravo-MCR/manejador_db.git
cd manejador_db
uv sync --extra dev
```

El extra `dev` instala pytest, pytest-qt, Ruff y maturin además de las dependencias de ejecución.

## Ejecutar la aplicación

```bash
uv run python -m backend_ide.ui.app
```

## Pruebas y calidad

```bash
# Pruebas automatizadas
uv run pytest

# Análisis estático
uv run ruff check .

# Verificar formato sin modificar archivos
uv run ruff format --check .
```

## Stack tecnológico

| Área | Tecnología |
| --- | --- |
| Lenguaje | Python 3.14.4 |
| Escritorio | PySide6 y Qt 6 |
| Modelos y validación | Pydantic |
| PostgreSQL | psycopg 3 |
| MySQL/MariaDB | PyMySQL |
| SQLite | `sqlite3` |
| SQL Server | pyodbc |
| SQL y metadatos | SQLAlchemy Core, sqlglot y RapidFuzz |
| Credenciales | keyring |
| Tooling | uv, pytest y Ruff |
| Core nativo futuro | Rust, PyO3 y maturin |

## Estructura del repositorio

```text
src/backend_ide/
├── application/       Casos de uso y coordinación
├── domain/            Modelos neutrales de esquema, conexión y SQL
├── generators/        Generadores de código (en desarrollo)
├── infrastructure/    Drivers, inspectores, almacenamiento y logging
├── legacy/            Migración y modernización legacy (planeado)
└── ui/                Aplicación de escritorio PySide6

tests/                 Pruebas automatizadas
docs/                  Especificación, arquitectura, decisiones y roadmap
```

## Arquitectura

El **Universal Schema Model** es el contrato central del producto. Los inspectores convierten la
metadata específica de cada motor a ese modelo neutral; el editor, los diagramas, los comparadores
y los generadores consumen la misma representación.

```text
Database / ORM / Legacy Source
              ↓
      Universal Schema Model
              ↓
 SQL IDE · ERD · Diff · Generators
```

La lógica de dominio no depende de PySide6 ni de drivers de base de datos. Las operaciones de base
de datos que puedan tardar se ejecutan fuera del hilo principal de Qt.

## Documentación

- [Especificación del producto](docs/PRODUCT_SPEC.md)
- [Arquitectura](docs/ARCHITECTURE%281%29.md)
- [Decisiones de arquitectura](docs/DECISIONS.md)
- [Roadmap técnico](docs/ROADMAP%2820260813-213518%29.md)
- [Plan de trabajo original](Plan%20de%20trabajo.md)

## Seguridad

- Las contraseñas no deben guardarse en el repositorio ni en archivos de configuración.
- Los perfiles utilizan el almacén seguro del sistema operativo mediante `keyring`.
- No se recomienda conectar esta versión pre-alpha a entornos de producción.
- Las operaciones destructivas nunca deberán ejecutarse automáticamente.

## Desarrollo

El proyecto evoluciona por fases. Antes de enviar cambios:

1. conserva las dependencias del dominio independientes de Qt y de los drivers;
2. agrega o actualiza las pruebas correspondientes;
3. ejecuta pytest y Ruff;
4. documenta las decisiones que modifiquen límites arquitectónicos.

## Licencia

El paquete declara licencia MIT en `pyproject.toml`. El archivo de licencia del repositorio está
pendiente de incorporarse.
