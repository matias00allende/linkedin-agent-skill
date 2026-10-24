# Cambios

## 1.5.0 - 2026-10-24

- Corrección: las citas anidadas (una cita dentro de un paréntesis, o al revés) se restauran completas.
- Argumentos y archivos de datos validados: seguidores y cantidad deben ser positivos, y un archivo de límites o de léxico con estructura incorrecta produce un error controlado.
- El índice de estilo no entrega veredicto global con menos de tres chequeos calculables, y --omit permite excluir los que no corresponden al tipo de texto.
- Reemplazos que eliminaban una caracterización pasan a señalarse. Fórmulas de gancho con causalidad más prudente.
- Planes y extracciones: la salida (calendario, cartera, criterios) depende del encargo. Texto visible sin anglicismos evitables.
- Pruebas: 113.

## 1.4.0 - 2026-10-24

- Las citas y los paréntesis se protegen sin límite de largo. Los reemplazos automáticos quedan solo para equivalencias mecánicas; el resto se señala.
- La analítica no toma "vistas" ni "visualizaciones" como impresiones: pide confirmar qué mide la columna.
- El símbolo de prima ya no se convierte. El informe de estilo deja de dar metas numéricas y aclara que es una heurística.
- Respaldo mínimo breve en cada skill, criterio común con fronteras entre skills y lectura compartida de voz.md, planes y extracciones sin calendario impuesto, rúbrica con condiciones por nivel y cita obligatoria, plantilla de PDF por sistema operativo.
- Casos de selección de skills (tests/seleccion.json) con consultas ambiguas, compuestas y fuera de alcance.

## 1.3.0 - 2026-10-24

- Las citas entre comillas y los paréntesis, también de varias líneas, no reciben cambios léxicos. Los controles de dirección que invierten el texto se eliminan siempre.
- Reemplazos y borrados más prudentes: robusto, la decisión es tuya y piénsalo un momento pasan a señalarse y no a cambiarse.
- El informe señala cualquier emoji. El chequeo de concreción pasó a llamarse marcadores numéricos y nombres, con advertencia sobre el rol emisor.
- Nuevo subcomando tmp: crea carpetas temporales únicas con permisos restrictivos y las borra comprobando el resultado; solo borra carpetas que creó. La escritura de salida es exclusiva salvo con --force.
- Rúbrica con tres niveles de puntaje, exclusión de ítems que no aplican y orientaciones en vez de requisitos. Reglas de los ganchos sin absolutos.
- Respaldo mínimo ampliado, preguntas solo cuando faltan datos, referencias al material original permitidas, extracción para varios formatos y fronteras de skills ajustadas.
- Metadatos y prosa en español sin anglicismos evitables.
- Pruebas: 103.

## 1.2.0 - 2026-10-24

- Criterio común más estricto: separación entre encargo y material fuente, política de autoría y detectores en el criterio compartido, formato por tipo de tarea, privacidad con carpetas temporales únicas y borrado comprobado, y precedencia del criterio y del encargo sobre rúbricas y plantillas.
- Las estructuras pasaron a ser opciones: una publicación final por defecto, ganchos alternativos solo a pedido, seguimientos y cifras opcionales, carruseles sin cantidad fija de diapositivas, planes sin frecuencia impuesta.
- Descripciones con fronteras más claras entre skills vecinas y casos de derivación.
- Limpiador: el borrado de muletillas solo ocurre al comienzo de una oración, fuera de citas y si el resto queda correcto; se eliminan también los controles de dirección que pueden invertir el texto a la vista; nombres de caracteres, ayuda y errores en español.
- Analítica estricta: valida enteros, informa fila, columna y valor rechazado, distingue un cero de un dato ausente, calcula la tasa con los componentes conocidos, no compara filas con distinta cobertura y llama a la métrica impresiones por seguidor.
- Índice de estilo: muestra cobertura en lugar de confianza, renombra voz como marcas de persona y deja de atribuir patrones a la escritura de modelos.
- Rúbrica de perfil por rol y objetivo, sin exigir cifras ni llamada comercial ni actividad semanal.
- Carrusel: plantilla de exportación en una referencia, perfil temporal del navegador, revisión de recursos externos y de metadatos, y permiso para conservar el PDF.
- Pruebas: 94, con casos de borrado acotado, controles de dirección, analítica estricta y salida en español.

## 1.1.0 - 2026-10-24

- Solo español de Chile: se retiraron el léxico y las plantillas en inglés, las descripciones bilingües y el modo de idioma automático.
- Texto plano: las skills, el README, las plantillas y la salida del script no usan negritas, tablas, emojis ni adornos. El informe del script es texto corrido con decimales con coma.
- Skills más directas y más cortas, con descripciones activas para que se usen aunque la persona no nombre la skill.
- Nuevo references/criterio.md en ag-voz, que todas las skills leen antes de redactar: fija objetivo, tipo de salida, quién habla, audiencia, profundidad y restricciones; separa hechos, inferencias y recomendaciones; trata cada publicación como pieza de posicionamiento con riesgo reputacional basada en experiencias aportadas por la persona; y deja hashtags y fórmulas de interacción solo para cuando aportan.
- Las skills revisan el riesgo reputacional y de confidencialidad antes de entregar.
- Pruebas nuevas que exigen texto plano, solo español y que cada skill apunte al criterio.

## 1.0.0 - 2026-10-24

Primera versión de AgentIn.

### Scripts

- Un solo archivo con subcomandos (`agentin.py`: `clean`, `check`, `limits`, `stats`) en lugar de `humanize.py` y `detect.py`. Con `python -I` el directorio del script no entra a la ruta de importación, así que un módulo compartido no se puede importar; un archivo evita además la lógica duplicada que había entre los dos.
- Las muletillas borradas ya no dejan texto roto. Antes "Cabe destacar que lanzamos. Dicho esto, funciona." quedaba como `avisó., funciona.`. Ahora la coma se arregla y la mayúscula se repone.
- Ya no se pierden comas ni saltos de párrafo. Un enfoque ingenuo convertía "Hola Ana,\n\nTexto" en "Hola Ana\nTexto", y una raya al final de línea se comía la línea en blanco.
- No se mutila texto técnico. `.NET` y `.env` al inicio de línea, y `a ? b : c`, quedan intactos.
- El léxico distingue tres acciones (`replace`, `delete`, `flag`). Solo se reemplaza lo que conserva sentido y clase gramatical; "paisaje", "viaje" o "vital" se señalan y no se cambian. Se agregaron las formas flexionadas y se corrigió una frase que nunca coincidía.
- Los caracteres invisibles se tratan con criterio. Se conservan la unión de ancho cero dentro de emoji compuestos, la separación entre letras de alfabetos como el persa, las marcas de dirección en texto de derecha a izquierda y las banderas de subregión. Se quitan los invisibles dentro de enlaces, antes protegidos por error.
- Windows y UTF-8. Entrada y salida se fuerzan a UTF-8 y LF. Antes un emoji hacía fallar la salida y el texto con tildes por entrada estándar se corrompía sin aviso.
- Español. Detección de idioma, palabras con tilde y ñ, léxico propio, y marcas de persona adecuadas al español. Un enfoque ingenuo con un texto en español escrito a mano obtenía el peor veredicto.
- Segmentación de oraciones que no parte decimales, miles ni abreviaturas.
- Textos cortos. Un chequeo sin datos suficientes se muestra como no evaluable y no entra al promedio; antes impedía que cualquier comentario llegara al máximo.
- Códigos de salida y errores coherentes y sin trazas de Python. No se sobrescribe un archivo de salida sin `--force`.
- Código y datos auditables. Ningún carácter invisible ni de puntuación especial escrito literalmente: todo con escapes.
- Nuevos: `limits` (conteo de caracteres, porque era fácil rotular 187 una nota de 152 y los modelos cuentan mal) y `stats` (métricas de `ag-audit` calculadas por script, no a mano por el modelo).

### Política y lenguaje

- El "detector" pasa a "índice de estilo". Se eliminó el marco de pasar detectores y de quitar la "huella de IA". El panel mide muletillas, ritmo e higiene, y lo dice en cada salida.
- Política explícita en `ag-voz`: ayuda a mejorar la voz propia, no a ocultar autoría ni a evadir detectores; respeto de las reglas de cada contexto; revisión humana antes de publicar; los hechos son de la persona.
- No se inventa experiencia. Los tipos de comentario que requieren un dato o una vivencia ahora la piden a la persona; el ejemplo que redactaba una experiencia inexistente se reemplazó.
- Texto de terceros como dato. Las skills que leen mensajes, comentarios o transcripciones indican que no se obedecen instrucciones dentro de ese texto.
- Afirmaciones sin fuente reetiquetadas como hipótesis: horarios, formatos, "el que más retiene", topes de invitaciones, el formato de la exportación. Se eliminaron las superlativas de las fórmulas de gancho.
- Privacidad: aviso de que los mensajes de terceros llegan al modelo y de dónde se guardan nombres.

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

