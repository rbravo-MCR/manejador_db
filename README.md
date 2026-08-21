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
- adaptador e inspector PostgreSQL con descubrimiento de bases y carga bulk de metadatos;
- adaptador y proveedor inicial de metadatos para SQLite;
- perfiles de conexión con secretos almacenados mediante el keyring del sistema;
- shell de escritorio nativo construido con PySide6 y componentes reutilizables;
- barra superior compacta con grupos de conexión, consulta y apariencia;
- indicador no interactivo del entorno del perfil seleccionado;
- explorador en vivo con selector de base de datos, filtro, carga diferida de columnas y
  generación de consultas comunes;
- editor SQL con resaltado, pestañas e IntelliSense contextual basado en metadatos en memoria;
- sugerencias por dialecto, schemas, tablas, vistas, columnas, aliases, funciones y snippets;
- ejecución no bloqueante del documento o de la selección SQL contra la conexión y base activas;
- grid de resultados y exportación a CSV y JSON;
- temas Sistema, Claro y Oscuro con selección persistente;
- 114 pruebas automatizadas.

El proyecto continúa en pre-alpha. La protección adicional para operaciones en producción, las
transacciones explícitas, los adaptadores completos de MySQL/MariaDB y SQL Server, la segunda
entrega de IntelliSense, los diagramas ER y los generadores permanecen en desarrollo o planeados.

### Interfaz actual

La ventana principal mantiene una distribución compacta orientada a desarrollo:

- conexión a la izquierda, acciones SQL al centro y apariencia a la derecha;
- explorador ajustable junto al workspace SQL;
- editor y resultados distribuidos inicialmente en proporción aproximada 65/35;
- `Ejecutar` como única acción primaria y `Diagrama ER` deshabilitado hasta implementar su flujo;
- soporte visual validado en temas Claro y Oscuro a 1340 × 840 y 1100 × 700.

El IntelliSense usa snapshots de metadatos por conexión y base de datos. No consulta el motor en
cada pulsación: el editor aplica debounce de 150 ms, abre inmediatamente al escribir punto y
admite invocación manual mediante `Ctrl/Cmd+Space`.

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

# Construir los paquetes distribuibles
uv build
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
- [Especificación del editor SQL](docs/FEATURE%20SPEC%20%E2%80%94%20Editor%20SQL%20con%20Autocompletado%20Inteligente.md)
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
3. ejecuta pytest, Ruff y la verificación de formato;
4. documenta las decisiones que modifiquen límites arquitectónicos.

## Licencia

El paquete declara licencia MIT en `pyproject.toml`. El archivo de licencia del repositorio está
pendiente de incorporarse.
