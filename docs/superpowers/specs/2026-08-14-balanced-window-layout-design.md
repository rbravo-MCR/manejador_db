# Diseño de distribución equilibrada de la ventana

## Objetivo

Reorganizar todos los controles visibles de la ventana principal para que la jerarquía de acciones sea clara, el espacio se reparta de forma consistente y la interfaz siga siendo cómoda al redimensionarse. El cambio conserva el comportamiento existente de conexiones, consultas, exploración, exportación y temas.

## Dirección elegida

Se aplicará una distribución por grupos funcionales. Las acciones se colocarán junto al contexto al que pertenecen, con una única acción primaria por zona y controles secundarios visualmente contenidos. Se conservarán el sistema de color Catppuccin, la tipografía y los componentes Qt actuales.

## Barra superior

La barra utilizará tres zonas estables:

1. **Conexión, a la izquierda:** etiqueta de perfil, selector, distintivo de entorno y acciones `Nueva conexión` y `Editar`.
2. **Consulta, en el centro:** `Ejecutar` como acción primaria, seguida de `Nueva consulta` y `Diagrama ER` como acciones secundarias.
3. **Aplicación, a la derecha:** selector de tema.

Un layout de tres columnas mantendrá centrado el grupo de consulta cuando haya espacio suficiente. La zona izquierda podrá crecer y el selector de perfil podrá reducirse hasta un ancho legible, sin desplazar las utilidades del extremo derecho. Todos los botones tendrán 32 px de alto y una separación base de 8 px. La barra tendrá márgenes horizontales de 12 px y no dependerá de anchos fijos para sus grupos.

Los emojis de los botones se reemplazarán por iconos de QtAwesome. Las etiquetas y los `tooltips` conservarán la función explícita de cada acción.

## Explorador lateral

El encabezado reunirá el título `DATABASE EXPLORER`, el contador de entidades y, en el extremo derecho, los botones compactos de refrescar y agregar conexión. Debajo se mostrarán, en este orden:

1. selector de base de datos a todo el ancho;
2. filtro de tablas a todo el ancho;
3. mensajes de carga o error;
4. árbol de objetos, ocupando todo el espacio restante.

Esta organización elimina una fila exclusiva para dos botones pequeños y alinea los campos en una sola columna visual. El panel tendrá un ancho inicial de 330 px, un mínimo de 280 px y seguirá siendo ajustable mediante el separador.

## Editor y resultados

El espacio de trabajo mantendrá el editor arriba y los resultados abajo. El separador vertical asignará inicialmente 65 % al editor y 35 % a resultados, con ambos paneles ajustables. El editor tendrá una altura mínima de 240 px y los resultados una altura mínima de 180 px.

La barra de resultados tendrá el estado de ejecución a la izquierda. El filtro y `Exportar` se agruparán a la derecha, con alturas y espaciado iguales a los de la barra superior. Las pestañas y la tabla ocuparán el espacio restante.

## Reglas visuales

- Escala de espaciado: 4 px para separación interna compacta, 8 px entre controles relacionados y 12 px entre grupos.
- Altura estándar: 32 px para botones, selectores y campos de las barras.
- Acción primaria: únicamente `Ejecutar`, usando el color de éxito existente.
- Acciones secundarias: superficie neutra con icono y texto; las acciones compactas del explorador serán solo icono y `tooltip`.
- Alineación: controles de una misma barra centrados verticalmente.
- Iconografía: QtAwesome; no se añadirán recursos rasterizados ni SVG personalizados.
- Temas: la distribución y la legibilidad deberán funcionar en modo oscuro y claro.

## Componentes y límites

- `MainWindow` será responsable de la cuadrícula de la barra superior y de las proporciones de los separadores.
- `ConnectionSelector` será responsable únicamente del orden y tamaño adaptable de los controles de conexión.
- `DatabaseExplorerWidget` será responsable del encabezado compacto y de la columna de selector, búsqueda, estado y árbol.
- `ResultsWidget` será responsable de su barra de estado, filtro y exportación.
- `ThemeManager` centralizará los tamaños y estilos por `objectName` cuando sea necesario, evitando hojas de estilo duplicadas en widgets individuales.

No se cambiarán señales, servicios, modelos, carga en segundo plano ni flujos de datos. La redistribución no introducirá nuevas páginas, menús o acciones.

## Estados y errores

Los controles deshabilitados durante una inspección conservarán su estado visual. Los mensajes de carga y error del explorador permanecerán inmediatamente antes del árbol y no modificarán la altura del encabezado. Los errores de consulta seguirán apareciendo en la pestaña de mensajes; la barra de resultados solo resumirá el estado.

En ventanas estrechas, el selector de perfil cederá ancho antes que los botones de acción. La ventana tendrá un tamaño mínimo de 1100 × 700 px para impedir solapamientos; no se ocultarán controles silenciosamente.

## Verificación

Las pruebas automatizadas comprobarán:

- pertenencia y orden de los controles en cada grupo;
- dimensiones estándar y anchos mínimos adaptables;
- factores de estiramiento y tamaños iniciales de los separadores;
- conservación de señales y estados habilitado/deshabilitado;
- ausencia de emojis en las acciones reorganizadas.

La revisión visual se realizará con capturas de la ventana completa en tema oscuro y claro, tanto al tamaño inicial de 1340 × 840 como al tamaño mínimo admitido. Se comprobarán alineación, recortes, solapamientos, márgenes, contraste y distribución del espacio.

## Criterios de aceptación

El trabajo quedará terminado cuando:

1. todas las acciones estén agrupadas por función y alineadas según este documento;
2. `Ejecutar` sea la única acción visualmente primaria;
3. explorador, editor y resultados aprovechen el espacio sin filas de control innecesarias;
4. la ventana inicial y la mínima no presenten recortes ni solapamientos;
5. los dos temas mantengan legibilidad y jerarquía;
6. las pruebas automatizadas y la revisión visual pasen sin regresiones funcionales.
