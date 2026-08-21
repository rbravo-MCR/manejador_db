# Design QA — Explorador de bases de datos

## Evidencia visual

- Fuente de referencia: `/home/rafael/Imágenes/Capturas de pantalla/Captura desde 2026-08-14 12-38-08.png`
- Implementación final: `/tmp/manejador-db-live-columns.png`
- Comparación normalizada: `/tmp/explorer-reference-normalized.png` y `/tmp/explorer-implementation-normalized.png`
- Referencia: 1198 × 841 px a escala 1x.
- Implementación: 1340 × 840 px a escala 1x.

La referencia muestra la base y el esquema contraídos. La implementación usa el estado real
solicitado: `db_outlet`, esquema `admin_service` y la tabla `activity_log` desplegada para
mostrar sus campos.

## Historial de comparación

### Iteración 1

Evidencia: `/tmp/manejador-db-live-explorer.png`.

- P1: el análisis profundo de 407 tablas tardaba más de 90 segundos y dejaba el explorador
  aparentemente vacío. Se sustituyó por una carga inicial resumida de dos consultas.
- P2: el panel era demasiado estrecho y poco denso. Se ajustó a 340 px, indentación de 16 px,
  espaciado compacto y acciones planas.
- P1: una tabla no mostraba sus campos al desplegarse. Se añadió carga diferida en segundo
  plano con nombre, tipo nativo, clave primaria y nulabilidad.

### Iteración 2

Evidencia: `/tmp/manejador-db-live-columns.png`.

- No quedan diferencias P0, P1 o P2.
- La jerarquía visible es Base de datos → Esquema → Tabla → Campo.
- Los controles superiores, filtro, contador de entidades y árbol tienen la densidad visual
  de la referencia conservando el sistema Catppuccin propio de la aplicación.

## Revisión de superficies

- Tipografía: familia nativa de escritorio con tamaño compacto de 13 px.
- Espaciado: selector, filtro, contador y árbol alineados en una sola columna visual.
- Color: tokens oscuros propios, contraste legible e iconos amarillos para tablas.
- Iconografía: QtAwesome; no se usan emojis ni recursos rasterizados en el explorador.
- Texto: etiquetas en español y valores procedentes de la conexión activa.
- Interacciones: conexión automática, selector de bases, cambio de base, refresco, filtro,
  expansión de tabla y conservación del árbol ante errores.
- Consola: aplicación nativa; ejecución y registros sin errores no controlados.

## Resultado

final result: passed

## Distribución completa de ventana

Evidencia del rediseño equilibrado:

- Tema oscuro, 1340 × 840: `/tmp/manejador-db-layout-dark-1340x840.png`
- Tema oscuro, 1100 × 700: `/tmp/manejador-db-layout-dark-1100x700.png`
- Tema claro, 1340 × 840: `/tmp/manejador-db-layout-light-1340x840.png`
- Tema claro, 1100 × 700: `/tmp/manejador-db-layout-light-1100x700.png`

Resultado de la revisión:

- La barra superior conserva las zonas de conexión, consulta y aplicación sin recortes.
- `Ejecutar` es la única acción primaria; `Diagrama ER` comunica su estado deshabilitado.
- El explorador mantiene 340 px inicialmente y puede reducirse hasta 280 px.
- Editor y resultados conservan una proporción inicial aproximada de 65/35.
- El encabezado compacto del explorador integra contador, refresco y nueva conexión.
- Iconos, texto, bordes y estados mantienen contraste en temas claro y oscuro.
- El entorno se presenta como un punto semántico y nombre completo (`Desarrollo`,
  `Pruebas`, `Preproducción` o `Producción`), sin fondo ni borde que sugieran interacción.
- Los controles permanecen visibles y alineados en el tamaño mínimo de 1100 × 700.
- `Ctrl+Enter` ejecuta la consulta del editor activo mediante el mismo flujo asíncrono del botón.
- Cuando existe una selección, botón y atajo ejecutan solo ese SQL y conservan correctamente
  sus saltos de línea; sin selección se ejecuta el documento completo.

Sin limitaciones visuales conocidas.

## Superficie de resultados

- Tema oscuro con consulta real: `/tmp/manejador-db-results-after.png`
- Tema claro con datos equivalentes: `/tmp/manejador-db-results-light-after.png`
- La cuadrícula define explícitamente fondo base, filas alternas, encabezado y selección
  mediante tokens; ya no hereda filas blancas o superficies negras de la paleta de plataforma.
- El contraste, la lectura horizontal y la diferenciación entre filas se conservan en ambos temas.

## Menús emergentes

- Tema oscuro: `/tmp/manejador-db-popup-dark.png`
- Tema claro: `/tmp/manejador-db-popup-light.png`
- Los menús de tema, exportación y contexto comparten superficie, texto, hover,
  selección, estados deshabilitados y separadores definidos mediante tokens.
- Las opciones mantienen contraste legible y la opción activa no depende solo del color de fondo.

## Trazabilidad del rediseño

| Requisito | Evidencia |
| --- | --- |
| Barra superior en tres zonas | `test_top_bar_groups_controls_by_documented_function` |
| Controles visibles a 1340 × 840 y 1100 × 700 | `test_documented_window_sizes_have_no_clipped_toolbar_controls` y cuatro capturas abiertas |
| Explorador inicial de 340 px y mínimo de 280 px | prueba geométrica de ventana y `test_explorer_header_contains_summary_and_compact_actions` |
| Editor/resultados 65/35 y mínimos 240/180 px | `test_documented_window_sizes_have_no_clipped_toolbar_controls` |
| Sistema, Claro y Oscuro persistentes | `test_theme_manager_persists_all_documented_modes`, `test_system_theme_resolves_to_a_concrete_palette` y `test_theme_control_exposes_system_light_and_dark` |
| `Ejecutar` como única acción primaria | estructura y textos comprobados en `test_top_bar_groups_controls_by_documented_function`; capturas claro/oscuro |
| Acciones futuras deshabilitadas | estado de `Diagrama ER` comprobado en `test_top_bar_groups_controls_by_documented_function` |
| Refrescar y agregar conexión desde el explorador | `test_explorer_header_actions_emit_their_documented_requests` |
| SQL ejecutable antes de cargar campos por lazy loading | `test_sql_generation_falls_back_safely_before_lazy_columns_load`; `SELECT *` evita resultados con filas sin columnas |
| Estado de entorno explícito y no interactivo | `test_environment_indicator_uses_full_semantic_labels_without_badge_chrome` y cuatro capturas abiertas |
| Ejecución por teclado | `test_ctrl_enter_executes_the_active_query` |
| Ejecución prioritaria del SQL seleccionado | `test_sql_editor_returns_only_selected_multiline_sql`, `test_execute_dispatches_only_the_selected_sql` y prueba real con resultado `answer = 2` |
| Superficies legibles de la cuadrícula | `test_results_grid_defines_non_black_base_and_alternate_surfaces` y capturas claro/oscuro |
| Contraste de menús emergentes | `test_popup_menus_use_readable_theme_surfaces` y capturas claro/oscuro |
| Consultas e inspecciones fuera del hilo UI | `test_query_worker_background_execution`, `test_schema_worker_emits_database_names_and_schema` y `test_table_columns_worker_emits_fields_and_closes_transient_connection` |
| Conservación de flujos de conexión y consulta | `test_execute_uses_active_connection_and_displays_real_rows` y pruebas de perfiles/cambio de base |
| Estilos centralizados en componentes rediseñados | `ThemeManager`, propiedades dinámicas del entorno y tokens de `ThemePalette`; el color personalizado del perfil permanece como metadato y no reemplaza la semántica del entorno |

## Editor SQL con autocompletado inteligente

Especificación implementada: `docs/FEATURE SPEC — Editor SQL con Autocompletado Inteligente.md`,
primera entrega funcional.

### Evidencia visual

- Popup con metadata PostgreSQL real, tema oscuro:
  `/tmp/manejador-db-intellisense-dark.png`.
- Popup con la misma metadata, tema claro:
  `/tmp/manejador-db-intellisense-light.png`.
- Ambos estados muestran iconos QtAwesome, etiqueta limpia, tipo nativo y objeto calificado;
  selección, texto, fondo, borde y scroll conservan contraste mediante `ThemeManager`.

### Verificación con metadata real

- Perfil: `B2B_OUTLET`; base: `db_outlet`.
- Carga bulk comprobada: 407 tablas, 4 vistas y 281 funciones.
- Caso manual: `SELECT a.` seguido por
  `FROM admin_service.activity_log a`.
- Resultado: el popup mostró, en orden, las 12 columnas reales de
  `admin_service.activity_log`, empezando por `id`, `log_name`, `description`,
  `subject_type`, `subject_id`, `event`, `causer_type` y `causer_id`.
- La interacción se ejecutó exclusivamente sobre el snapshot en memoria después de cerrar la
  conexión usada para la inspección; no hubo consultas de catálogo por pulsación.

### Trazabilidad funcional

| Requisito | Evidencia |
| --- | --- |
| `SEL` → `SELECT` y keywords por dialecto | `test_completion_engine_keywords`, `test_four_dialect_providers_are_available_without_ui_conditionals` |
| Schemas, tablas y vistas | `test_schema_dot_returns_only_tables_and_views_from_that_schema` |
| Columnas y aliases multilínea | `test_complete_uses_sources_after_cursor_for_alias_columns` y comprobación PostgreSQL real |
| JOIN, WHERE, UPDATE e INSERT | `test_complete_resolves_join_where_update_and_insert_columns` |
| Funciones del motor y de metadata | `test_dialect_functions_and_cached_database_functions_are_available` |
| Fuzzy matching y ranking contextual | `test_fuzzy_matching_finds_table_without_prefix_match`, `test_contextual_ranking_prioritizes_columns_over_generic_keywords` |
| Snippets básicos | `test_basic_snippet_is_ranked_for_its_trigger` |
| Caché por conexión/base y actualización atómica | `test_cache_isolates_database_snapshots_and_returns_no_cross_connection_data`, `test_column_update_replaces_snapshot_atomically` |
| Metadata PostgreSQL sin consulta por objeto | `test_postgresql_inspector_builds_completion_metadata_with_bulk_queries` |
| Soporte inicial SQLite | `test_connection_service_builds_a_working_sqlite_adapter`, `test_sqlite_provider_loads_tables_views_columns_and_primary_keys` |
| Debounce de 150 ms y punto inmediato | `test_automatic_completion_is_debounced_but_remains_responsive`, `test_dot_opens_alias_columns_immediately_without_waiting_for_debounce` |
| Ctrl/Cmd+Space, Enter, Tab y Escape | pruebas manuales y `test_ctrl_space_manually_opens_intellisense`, `test_tab_accepts_current_completion_and_replaces_only_prefix`, `test_enter_accepts_completion_and_escape_dismisses_popup` |
| Tema claro/oscuro e información adicional | dos capturas abiertas y `test_popup_model_exposes_insert_text_and_documentation` |
| Objetivo de menos de 100 ms y catálogos grandes | `test_cached_completion_stays_under_budget_and_caps_large_catalog_results`; 2,000 tablas y máximo de 200 resultados renderizados |
| Refresco manual y después de DDL exitoso | acción `Refrescar metadatos` y `test_successful_ddl_refreshes_cached_metadata` |

### Límites deliberados de esta primera entrega

- CTE, subqueries, sugerencias basadas en foreign keys, signature help y parámetros de
  funciones pertenecen a la segunda entrega definida por la especificación.
- MySQL/MariaDB y SQL Server ya tienen proveedores de lenguaje desacoplados; sus proveedores
  de metadata y adaptadores de conexión completos quedan para la segunda entrega.
- SQLite expone funciones integradas por dialecto porque SQLite no mantiene un catálogo
  estándar de funciones registradas por la aplicación.
- El analizador actual combina tokenización y estado para contextos comunes; queda aislado de
  Qt para poder sustituirse o ampliarse con un parser avanzado sin cambiar el editor.

Resultado del autocompletado: passed.

## QA de integración final

### Evidencia regenerada

- Ventana oscura, 1340 × 840: `/tmp/manejador-db-integration-dark-1340x840.png`.
- Ventana oscura, 1100 × 700: `/tmp/manejador-db-integration-dark-1100x700.png`.
- Ventana clara, 1340 × 840: `/tmp/manejador-db-integration-light-1340x840.png`.
- Ventana clara, 1100 × 700: `/tmp/manejador-db-integration-light-1100x700.png`.
- Popup IntelliSense oscuro: `/tmp/manejador-db-intellisense-integration-dark.png`.
- Popup IntelliSense claro: `/tmp/manejador-db-intellisense-integration-light.png`.

### Resultado de integración

- La barra superior mantiene sus tres grupos, el indicador `Desarrollo` no parece una acción y
  ningún control se recorta en los dos tamaños admitidos.
- Editor, explorador y resultados mantienen jerarquía, contraste y proporciones en ambos temas.
- Un snapshot PostgreSQL determinista con `admin_service.activity_log` produjo ocho columnas
  contextuales para `SELECT a.` sin realizar I/O durante la pulsación.
- El popup conserva iconos, tipo nativo, objeto calificado, selección, scroll y contraste en
  temas Claro y Oscuro.
- No se observaron limitaciones visuales nuevas durante la consolidación.
