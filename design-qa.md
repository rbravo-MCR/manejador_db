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

### Evidencia

- Oscuro, tamaño inicial: `/tmp/manejador-db-layout-dark-1340x840.png`.
- Oscuro, tamaño mínimo: `/tmp/manejador-db-layout-dark-1100x700.png`.
- Claro, tamaño inicial: `/tmp/manejador-db-layout-light-1340x840.png`.
- Claro, tamaño mínimo: `/tmp/manejador-db-layout-light-1100x700.png`.

### Geometría verificada

- A 1340 × 840, la barra distribuye conexión en `(12, 8, 527, 36)`, consultas en
  `(551, 8, 388, 36)` y tema en `(1296, 10, 32, 32)`.
- A 1100 × 700, conserva conexión en `(12, 8, 527, 36)`, consultas en
  `(551, 8, 388, 36)` y tema en `(1056, 10, 32, 32)`.
- Ningún grupo se recorta o solapa; se conservan al menos 12 px entre conexión y consultas.
- El separador horizontal conserva 340 px para el explorador en ambos tamaños.
- El separador vertical asigna exactamente 65 % al editor y 35 % a resultados en ambos tamaños.
- El botón dividido de tema mide 32 × 32 y su tamaño recomendado por Qt es 29 × 29; icono y
  acceso al menú caben sin recorte.

### Revisión visual

- La barra superior presenta las tres zonas documentadas y `Ejecutar` es la única acción
  primaria.
- `Diagrama ER` permanece visible pero deshabilitado, por lo que no comunica una función inerte
  como disponible.
- El encabezado del explorador concentra título, contador, refresco y nueva conexión en una fila;
  selector y filtro quedan alineados debajo.
- El editor y los resultados aprovechan el alto disponible y conservan sus controles visibles.
- La barra de resultados alinea estado a la izquierda y filtro/exportación a la derecha.
- Los temas Oscuro y Claro mantienen contraste, jerarquía, márgenes y estados deshabilitados.
- No hay emojis en las acciones reorganizadas; los iconos proceden de QtAwesome.
- Sin limitaciones visuales conocidas.

### Auditoría de trazabilidad

| Requisito | Evidencia actual | Estado |
| --- | --- | --- |
| Barra con conexión, consultas y tema | `test_top_bar_groups_controls_by_documented_function` y cuatro capturas | Cumple |
| Explorador, workspace, resultados y status bar | `test_main_window_creation`, geometrías medidas y capturas | Cumple |
| Layout adaptable sin recortes | `test_documented_window_sizes_have_no_clipped_toolbar_controls` | Cumple |
| Acciones contextuales y feedback | pruebas de carga/error del explorador y barras agrupadas | Cumple |
| Sistema, Claro, Oscuro y persistencia | cuatro pruebas de tema en `test_ui_shell.py` | Cumple |
| Tokens y componentes reutilizables | `ThemeManager`, `ThemePalette` y ausencia de colores literales en componentes tocados | Cumple |
| UI sin lógica de motor | servicios/workers conservados y `test_no_pyside_or_db_driver_imports` | Cumple |
| Explorador denso de 340 px | geometría horizontal `[340, 996]` y `[340, 756]` | Cumple |
| Base de datos fuera del hilo UI | pruebas existentes de `QueryWorker`, inspección y columnas | Cumple |

final result: passed
