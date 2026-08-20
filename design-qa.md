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
| Estado de entorno explícito y no interactivo | `test_environment_indicator_uses_full_semantic_labels_without_badge_chrome` y cuatro capturas abiertas |
| Ejecución por teclado | `test_ctrl_enter_executes_the_active_query` |
| Ejecución prioritaria del SQL seleccionado | `test_sql_editor_returns_only_selected_multiline_sql`, `test_execute_dispatches_only_the_selected_sql` y prueba real con resultado `answer = 2` |
| Superficies legibles de la cuadrícula | `test_results_grid_defines_non_black_base_and_alternate_surfaces` y capturas claro/oscuro |
| Contraste de menús emergentes | `test_popup_menus_use_readable_theme_surfaces` y capturas claro/oscuro |
| Consultas e inspecciones fuera del hilo UI | `test_query_worker_background_execution`, `test_schema_worker_emits_database_names_and_schema` y `test_table_columns_worker_emits_fields_and_closes_transient_connection` |
| Conservación de flujos de conexión y consulta | `test_execute_uses_active_connection_and_displays_real_rows` y pruebas de perfiles/cambio de base |
| Estilos centralizados en componentes rediseñados | `ThemeManager`, propiedades dinámicas del entorno y tokens de `ThemePalette`; el color personalizado del perfil permanece como metadato y no reemplaza la semántica del entorno |
