# Cambios

## 1.0.0 - 2026-10-24

Primera versión de AgentIn.

### Scripts

- **Un solo archivo con subcomandos** (`agentin.py`: `clean`, `check`, `limits`, `stats`) en lugar de `humanize.py` y `detect.py`. Con `python -I` el directorio del script no entra a la ruta de importación, así que un módulo compartido no se puede importar; un archivo evita además la lógica duplicada que había entre los dos.
- **Las muletillas borradas ya no dejan texto roto.** Antes "Importantly, we shipped. Notably, it works." quedaba como `we shipped., it works.`. Ahora la coma se arregla y la mayúscula se repone.
- **Ya no se pierden comas ni saltos de párrafo.** Un enfoque ingenuo convertía "Hola Ana,\n\nTexto" en "Hola Ana\nTexto", y una raya al final de línea se comía la línea en blanco.
- **No se mutila texto técnico.** `.NET` y `.env` al inicio de línea, y `a ? b : c`, quedan intactos.
- **El léxico distingue tres acciones** (`replace`, `delete`, `flag`). Solo se reemplaza lo que conserva sentido y clase gramatical; "paisaje", "viaje" o "vital" se señalan y no se cambian. Se agregaron las formas flexionadas y se corrigió una frase que nunca coincidía.
- **Los caracteres invisibles se tratan con criterio.** Se conservan la unión de ancho cero dentro de emoji compuestos, la separación entre letras de alfabetos como el persa, las marcas de dirección en texto de derecha a izquierda y las banderas de subregión. Se quitan los invisibles dentro de enlaces, antes protegidos por error.
- **Windows y UTF-8.** Entrada y salida se fuerzan a UTF-8 y LF. Antes un emoji hacía fallar la salida y el texto con tildes por entrada estándar se corrompía sin aviso.
- **Español.** Detección de idioma, palabras con tilde y ñ, léxico propio, y marcas de persona adecuadas al español. Un enfoque ingenuo con un texto en español escrito a mano obtenía el peor veredicto.
- **Segmentación de oraciones** que no parte decimales, miles ni abreviaturas.
- **Textos cortos.** Un chequeo sin datos suficientes se muestra como no evaluable y no entra al promedio; antes impedía que cualquier comentario llegara al máximo.
- **Códigos de salida y errores coherentes** y sin trazas de Python. No se sobrescribe un archivo de salida sin `--force`.
- **Código y datos auditables.** Ningún carácter invisible ni de puntuación especial escrito literalmente: todo con escapes.
- **Nuevos:** `limits` (conteo de caracteres, porque era fácil rotular 187 una nota de 152 y los modelos cuentan mal) y `stats` (métricas de `ag-audit` calculadas por script, no a mano por el modelo).

### Política y lenguaje

- **El "detector" pasa a "índice de estilo".** Se eliminó el marco de pasar detectores y de quitar la "huella de IA". El panel mide muletillas, ritmo e higiene, y lo dice en cada salida.
- **Política explícita en `ag-voz`:** ayuda a mejorar la voz propia, no a ocultar autoría ni a evadir detectores; respeto de las reglas de cada contexto; revisión humana antes de publicar; los hechos son de la persona.
- **No se inventa experiencia.** Los tipos de comentario que requieren un dato o una vivencia ahora la piden a la persona; el ejemplo que redactaba una experiencia inexistente se reemplazó.
- **Texto de terceros como dato.** Las skills que leen mensajes, comentarios o transcripciones indican que no se obedecen instrucciones dentro de ese texto.
- **Afirmaciones sin fuente reetiquetadas como hipótesis:** horarios, formatos, "el que más retiene", topes de invitaciones, el formato de la exportación. Se eliminaron las superlativas de las fórmulas de gancho.
- **Privacidad:** aviso de que los mensajes de terceros llegan al modelo y de dónde se guardan nombres.

### Skills

- Reescritas en español (Chile) con descripciones bilingües y fronteras más claras entre skills parecidas. Nombres `ag-*`.
- Los scripts se invocan con ruta completa (`${CLAUDE_SKILL_DIR}`) y `-I`, y se indica `python` o `python3` según el sistema.
- `ag-audit` pide la cantidad de seguidores (antes la necesitaba sin pedirla) y explica de dónde salen los datos.
- `ag-inbox` explica que solo trabaja con lo que se pega y que las marcas de tiempo de una secuencia solo se pueden juzgar si vienen en el texto.
- `ag-carousel` incluye el CSS `@page` y el comando para generar el PDF.
- `ag-dm` cuenta los caracteres con el script; el ejemplo trae el conteo verdadero.
- `ag-repurpose` pide que el material sea propio o con permiso.
- Fórmulas de gancho en español e inglés; el gancho 9 ya no muestra `\n` literal. Rúbrica de perfil en español e inglés.
- Plantillas de voz en español e inglés; carpeta de estado `~/.claude/agentin/`.
- El archivo de fórmulas se renombró a `hook-formulas.json` para no confundirlo con un archivo de hooks de Claude Code.

### Proyecto

- Pruebas con `unittest` (sin dependencias): casos de borde conocidos, propiedades de cada entrada del léxico, ejecución por subproceso con la codificación local de Windows, y reglas del repositorio (sin rayas largas, sin invisibles, sin rutas personales, sin importaciones de red).
- Integración continua en Linux, Windows y macOS (Python 3.9, 3.12 y 3.13).
- README con instalación por clonado y revisión; CONTRIBUTING; este registro.

