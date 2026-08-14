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
