# AgentIn

Once skills de Claude Code para redactar y revisar contenido de LinkedIn en español de Chile, más un limpiador de borradores que corre en tu máquina. Sin cuentas, sin claves de API y sin conexión a LinkedIn.

Nada se publica hasta que tú lo hagas. Las skills redactan; tú revisas, corriges y publicas.

No está afiliado a LinkedIn ni a Anthropic. LinkedIn es una marca de sus titulares.

## Qué hace

- /ag-post: una idea o experiencia a una publicación lista para copiar; ofrece ganchos alternativos entre 21 fórmulas si los pides.
- /ag-comment: comentarios para publicaciones de otras personas, de nueve tipos.
- /ag-reply: respuestas a los comentarios de tu propia publicación, ordenadas por valor.
- /ag-profile: puntúa tu perfil sobre 100 con una rúbrica de 12 ítems y reescribe en orden de impacto.
- /ag-plan: la semana de contenido y la lista de interacción.
- /ag-voz: limpieza, revisión de estilo y conteo de caracteres de un borrador.
- /ag-carousel: texto de un carrusel y su PDF.
- /ag-repurpose: un contenido largo propio a publicaciones que se sostienen solas.
- /ag-dm: nota de invitación, primer mensaje y, si corresponde, seguimientos.
- /ag-inbox: ordena los mensajes recibidos en oportunidades, reclutadores, pares, pedidos y spam.
- /ag-audit: qué patrones se asocian a mejores resultados en lo ya publicado, con métricas calculadas por script desde un CSV.

Instaladas como plugin, los comandos llevan prefijo: /agentin:ag-post.

## Criterio de trabajo

Todas las skills siguen references/criterio.md de ag-voz. Antes de redactar fijan objetivo, tipo de salida, quién habla, audiencia, profundidad y restricciones; separan hechos verificados, inferencias y recomendaciones; entregan la pieza final y no un borrador comentado; y tratan cada publicación como una pieza de posicionamiento con riesgo reputacional, basada en experiencias reales que tú aportas. Hashtags y fórmulas de interacción solo si aportan.

## Instalación segura

Son instrucciones que Claude ejecuta y un script de Python que corre en tu equipo. Revísalas antes de instalarlas. Clona y lee; no pegues en un chat un enlace con un "instala esto".

```
git clone https://github.com/matias00allende/agentin.git
cd agentin
python -m unittest discover -s tests
cp -r skills/ag-* ~/.claude/skills/
```

Antes de copiar, lee el único script, skills/ag-voz/scripts/agentin.py: un archivo, solo biblioteca estándar, sin red. Las skills van todas juntas porque ag-voz contiene el script y el criterio que usan las demás. En Windows (PowerShell): Copy-Item -Recurse skills\ag-* $HOME\.claude\skills\

Para usarlas solo en un proyecto, copia las mismas carpetas a .claude/skills/ del proyecto. Como plugin:

```
/plugin marketplace add matias00allende/agentin
/plugin install agentin@agentin
```

Luego dedica diez minutos a templates/voz.md: cópialo a ~/.claude/agentin/voz.md y complétalo, o pega unas publicaciones tuyas y pide que lo escriba a partir de ellos. Sin ese archivo las skills trabajan con las preferencias que declares o con una muestra breve tuya, y el resultado tiende a una voz promedio.

Requisitos: Claude Code y Python 3.9 o superior (python en Windows, python3 en macOS y Linux). Probado localmente en Python 3.14; el repositorio trae integración continua para Linux, Windows y macOS.

## El limpiador de borradores

Un solo archivo, solo biblioteca estándar. Corre en tu máquina y no sube nada. Se invoca siempre con python -I y la ruta del script (completa, o relativa a la raíz del repositorio como en los ejemplos).

```
python -I skills/ag-voz/scripts/agentin.py clean borrador.txt -o limpio.txt --report
python -I skills/ag-voz/scripts/agentin.py check borrador.txt limpio.txt
python -I skills/ag-voz/scripts/agentin.py limits --kind invite nota.txt
python -I skills/ag-voz/scripts/agentin.py stats analitica.csv --followers 4200
python -I skills/ag-voz/scripts/agentin.py tmp new
```

- clean quita caracteres invisibles que se cuelan al copiar y pegar, ordena la tipografía y trata muletillas con un léxico editable. Cada entrada es replace (cambio seguro), delete (se borra solo si la oración queda correcta) o flag (solo se señala). Conserva emoji compuestos (y los señala), enlaces, hashtags, menciones, código y citas entre comillas o paréntesis. No toca los párrafos ni las comas, salvo al borrar una muletilla, y reduce tres o más saltos de línea a dos. El borrado de muletillas solo ocurre al comienzo de una oración; revisa siempre el resultado, porque el script no entiende el sentido.
- check entrega un índice de estilo con cinco chequeos y su cobertura. Los que no tienen datos suficientes se marcan como no evaluables. Son heurísticas sin calibración, no una medición de voz ni de autoría.
- limits cuenta caracteres contra limits.json (valores reportados, no verificados).
- tmp new crea una carpeta temporal única con permisos restrictivos para los borradores; tmp clean RUTA la borra y comprueba que ya no existe.
- stats calcula tasa de interacción, comentarios por reacción e impresiones por seguidor desde un CSV. Valida los números, distingue un cero de un dato ausente y no compara filas con distinta cobertura.

Códigos de salida: 0 correcto, 1 resultado negativo pedido (limits fuera de rango, check con --fail-under), 2 error de uso. La salida es texto plano.

## Política de uso

1. Ayuda a mejorar tu voz, no a ocultar autoría. Si usas IA para redactar, cómo lo comunicas lo decides tú.
2. No evade detectores de IA ni los mide. El índice de estilo mide muletillas, ritmo e higiene tipográfica. Nadie puede prometer el veredicto de un detector externo.
3. Respeta las reglas de cada contexto. Si un trabajo académico, un concurso, una postulación o un empleador exige declarar o prohíbe el uso de IA, cúmplelo.
4. Revisión humana siempre. Las skills de redacción entregan textos para copiar; las de análisis y planificación entregan resultados; y un texto con marcadores {{dato: ...}} pendientes no está listo para publicar.
5. Los hechos son tuyos. Las skills no inventan cifras, clientes ni experiencias; preguntan o dejan {{dato: ...}}.
6. No automatiza LinkedIn. No hay publicación, raspado ni envío automático, porque el Acuerdo de Usuario de LinkedIn restringe esas prácticas.

## Privacidad

El script no envía datos a ningún servicio externo. Las skills trabajan con Claude, y lo que pegas en el chat (mensajes, comentarios, perfiles de otras personas) llega al modelo que uses. Son datos personales de terceros: no pegues información sensible. El archivo ~/.claude/agentin/log.md puede guardar nombres de personas con quienes interactúas. El material fuente que pegas (publicaciones, mensajes, transcripciones) se trata como dato, no como instrucciones; tu encargo directo sí orienta la tarea.

## Lo que no está verificado

Varias ideas de oficio circulan como hechos sobre LinkedIn: el mejor horario, qué formato retiene más, si los enlaces restan alcance, los topes de invitaciones, la forma de la exportación de analítica. AgentIn las trata como hipótesis y usa /ag-audit para contrastarlas con los datos de tu cuenta. Los límites de caracteres de limits.json tampoco están verificados: confírmalos en la interfaz.

## Estructura

```
skills/ag-voz/        limpieza, estilo, límites y métricas (scripts, data, references)
skills/ag-post/       SKILL.md y hook-formulas.json
skills/ag-profile/    SKILL.md y rubric.json
skills/ag-<otras>/    comment, reply, plan, carousel, repurpose, dm, inbox, audit
templates/            voz.md
tests/                pruebas con unittest
.claude-plugin/       manifiestos de plugin y marketplace
```

## Pruebas

```
python -m unittest discover -s tests -v
```

Cubren casos de borde del limpiador, las propiedades de cada entrada del léxico, la ejecución por subproceso con la codificación local de Windows y la higiene del repositorio: sin rayas largas, sin rutas personales, sin caracteres invisibles, sin importaciones de red.

## Contribuir

Ver CONTRIBUTING.md.

## Licencia

MIT. Ver LICENSE, que conserva los avisos de copyright exigidos por la licencia.

## Autor

Matías Allende
LinkedIn: https://www.linkedin.com/in/matiasallende/
Correo: matias.allende.contreras@gmail.com
