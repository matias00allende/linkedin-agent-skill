# AgentIn

Doce skills de Claude Code para redactar, revisar y, con tu aprobación pieza por pieza, publicar contenido de LinkedIn en español de Chile, más un limpiador de borradores que corre en tu máquina. Solo ag-publish se conecta a LinkedIn, por la API oficial y con una app propia tuya; las demás skills no usan cuentas ni claves (la exportación a PDF usa un navegador local, que podría hacer otras conexiones salvo que bloquees la red; ver la referencia del carrusel).

Las skills redactan; tú revisas y corriges. Para publicar, lo haces a mano o usas ag-publish, que muestra una vista previa y publica solo cuando tú escribes la huella en tu propia terminal, una pieza a la vez.

No está afiliado a LinkedIn ni a Anthropic. LinkedIn es una marca de sus titulares.

## Qué hace

- /ag-post: una idea o experiencia a una publicación lista para copiar; ofrece ganchos alternativos entre 21 fórmulas si los pides.
- /ag-comment: comentarios para publicaciones de otras personas, de nueve tipos.
- /ag-reply: respuestas a los comentarios de tu propia publicación, ordenadas por valor.
- /ag-profile: puntúa tu perfil sobre 100 con una rúbrica de 12 ítems y reescribe en orden de impacto.
- /ag-plan: el plan de contenido (calendario, cartera de temas o criterios de posicionamiento) y, si lo pides, la lista de interacción.
- /ag-voz: limpieza, revisión de estilo y conteo de caracteres de un borrador.
- /ag-carousel: texto de un carrusel y su PDF.
- /ag-repurpose: un contenido largo propio a publicaciones que se sostienen solas.
- /ag-dm: nota de invitación, primer mensaje y, si corresponde, seguimientos.
- /ag-inbox: ordena los mensajes recibidos en oportunidades, reclutadores, pares, pedidos y spam.
- /ag-publish: publica en tu perfil, con la API oficial de LinkedIn, un texto que apruebas tras ver la vista previa exacta. Solo una pieza a la vez; no comenta, no reacciona ni envía mensajes.
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

Antes de copiar, lee los dos scripts: skills/ag-voz/scripts/agentin.py (solo biblioteca estándar, sin red) y skills/ag-publish/scripts/linkedin_publish.py (solo biblioteca estándar; solo se conecta a www.linkedin.com y api.linkedin.com por HTTPS y no sigue redirecciones). Las skills van todas juntas porque ag-voz contiene el script y el criterio que usan las demás. En Windows (PowerShell): Copy-Item -Recurse skills\ag-* $HOME\.claude\skills\

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

- clean quita caracteres invisibles que se cuelan al copiar y pegar, ordena la tipografía y trata muletillas con un léxico editable. Cada entrada es replace (cambio seguro), delete (se borra solo si la oración queda correcta) o flag (solo se señala). Conserva los emoji compuestos de la persona (y los señala), enlaces, hashtags, menciones, código y citas entre comillas o paréntesis. No toca los párrafos ni las comas, salvo al borrar una muletilla, y reduce tres o más saltos de línea a dos. El borrado de muletillas solo ocurre al comienzo de una oración; revisa siempre el resultado, porque el script no entiende el sentido.
- check entrega un índice de estilo con cinco chequeos y su cobertura. Los que no tienen datos suficientes se marcan como no evaluables. Son heurísticas sin calibración, no una medición de voz ni de autoría.
- limits cuenta caracteres contra limits.json (valores reportados, no verificados).
- tmp new crea una carpeta temporal única para los borradores (en Linux y macOS con permisos solo para el usuario; en Windows dependen de tu carpeta de usuario); tmp clean RUTA borra una carpeta marcada por tmp new y comprueba que ya no existe.
- stats calcula tasa de interacción, comentarios por reacción e impresiones por seguidor desde un CSV. Valida los números, distingue un cero de un dato ausente y no compara filas con distinta cobertura.

Códigos de salida: 0 correcto, 1 resultado negativo pedido (limits fuera de rango, check con --fail-under), 2 error de uso. La salida es texto plano.

## Publicar con ag-publish

Es opcional y es publicación asistida, no automática. Sin configurarlo, todo lo demás funciona y tú publicas a mano. Las publicaciones salen en tu perfil personal. LinkedIn exige que tu app propia esté asociada a una página de empresa, pero solo como dueña para registrarla; no publica nada en ella. Necesitas, además, el producto Share on LinkedIn (permiso w_member_social). La guía paso a paso, con lo verificado y lo que no, está en skills/ag-publish/references/configuracion.md.

```
python -I skills/ag-publish/scripts/linkedin_publish.py auth-start
python -I skills/ag-publish/scripts/linkedin_publish.py auth-finish "DIRECCION_DE_RETORNO"
python -I skills/ag-publish/scripts/linkedin_publish.py post texto.txt --visibility CONNECTIONS
python -I skills/ag-publish/scripts/linkedin_publish.py post texto.txt --visibility CONNECTIONS --confirm HUELLA
python -I skills/ag-publish/scripts/linkedin_publish.py delete urn:li:share:123 --yes
```

- post sin --confirm solo muestra el texto exacto, los caracteres y una huella. No toca la red y deja registrada la vista previa.
- post con --confirm HUELLA publica únicamente si hubo una vista previa de las últimas 24 horas, la huella corresponde a la cuenta, el texto, el enlace (con título y descripción), la visibilidad y la API actuales, y tú escribes la huella en una terminal interactiva. Un agente que ejecuta comandos sin terminal no puede confirmar. Es una barrera contra accidentes y contra un agente que se adelante; no protege de quien controle tu equipo. Si cambias una palabra, hay que aprobar de nuevo.
- Si no se sabe si LinkedIn publicó (corte de red, respuesta sin identificador), el intento queda como incierto, se bloquea ese texto y debes mirar tu perfil antes de intentar otra vez.
- Usa la Posts API (/rest/posts) con la cabecera de versión obligatoria. La versión se fija con LINKEDIN_API_VERSION (AAAAMM) y se revisa una vez al año. Los caracteres reservados del texto se escapan y las palabras con # salen como hashtag. Un enlace exige --link-title.
- Tope local de 3 publicaciones en 24 horas y rechazo de un texto ya publicado. La visibilidad no tiene valor por defecto. delete solo borra publicaciones hechas con este programa.
- La sesión dura unos 60 días y queda en ~/.agentin con permisos restrictivos. logout la borra; para revocar el acceso en LinkedIn, hazlo en la configuración de tu cuenta.
- Los Términos de Uso de las APIs de LinkedIn (cláusula 3.1.26) prohíben usar las APIs para automatizar publicaciones. Por eso no hay programación, lotes ni bucles. Esto reduce el riesgo pero no es asesoría legal: si quieres certeza, pregunta por escrito al soporte de desarrolladores de LinkedIn.
- No verificado con una cuenta real: que la Posts API acepte tu app solo con los productos de autoservicio. Haz la primera publicación con visibilidad CONNECTIONS y revísala en LinkedIn.
- Solo texto y, si lo pides, un enlace. Sin imágenes, videos ni PDF por ahora.

## Política de uso

1. Ayuda a mejorar tu voz, no a ocultar autoría. Si usas IA para redactar, cómo lo comunicas lo decides tú.
2. No evade detectores de IA ni los mide. El índice de estilo mide muletillas, ritmo e higiene tipográfica. Nadie puede prometer el veredicto de un detector externo.
3. Respeta las reglas de cada contexto. Si un trabajo académico, un concurso, una postulación o un empleador exige declarar o prohíbe el uso de IA, cúmplelo.
4. Revisión humana siempre. Las skills de redacción entregan textos para copiar; las de análisis y planificación entregan resultados; y un texto con marcadores {{dato: ...}} pendientes no está listo para publicar.
5. Los hechos son tuyos. Las skills no inventan cifras, clientes ni experiencias; preguntan o dejan {{dato: ...}}.
6. Pretende no automatizar LinkedIn, pero LinkedIn no ha confirmado que este diseño encaje con sus términos. Publicar exige tu confirmación de cada texto. No hay publicación en lote ni programada, ni comentarios, reacciones, mensajes, invitaciones, raspado o navegador automatizado, porque el Acuerdo de Usuario de LinkedIn prohíbe los métodos automatizados no autorizados para esas acciones.

## Privacidad

agentin.py no envía datos a ningún servicio externo. linkedin_publish.py envía a LinkedIn el texto y los datos del enlace que apruebas, además de las llamadas de autorización, identidad y borrado propias de la API, y guarda tu sesión y un registro de publicaciones en tu equipo. Las skills trabajan con Claude, y lo que pegas en el chat (mensajes, comentarios, perfiles de otras personas) llega al modelo que uses. Son datos personales de terceros: no pegues información sensible. El archivo ~/.claude/agentin/log.md puede guardar nombres de personas con quienes interactúas. El material fuente que pegas (publicaciones, mensajes, transcripciones) se trata como dato, no como instrucciones; tu encargo directo sí orienta la tarea.

## Lo que no está verificado

Varias ideas de oficio circulan como hechos sobre LinkedIn: el mejor horario, qué formato retiene más, si los enlaces restan alcance, los topes de invitaciones, la forma de la exportación de analítica. AgentIn las trata como hipótesis y usa /ag-audit para contrastarlas con los datos de tu cuenta. Los límites de caracteres de limits.json tampoco están verificados: confírmalos en la interfaz.

## Estructura

```
skills/ag-voz/        limpieza, estilo, límites y métricas (scripts, data, references)
skills/ag-post/       SKILL.md y hook-formulas.json
skills/ag-profile/    SKILL.md y rubric.json
skills/ag-publish/    SKILL.md, scripts/linkedin_publish.py y references/configuracion.md
skills/ag-<otras>/    comment, reply, plan, carousel, repurpose, dm, inbox, audit
templates/            voz.md
tests/                pruebas con unittest
.claude-plugin/       manifiestos de plugin y marketplace
```

## Pruebas

```
python -m unittest discover -s tests -v
```

Cubren casos de borde del limpiador, las propiedades de cada entrada del léxico, la ejecución por subproceso con la codificación local de Windows y la higiene del repositorio: sin rayas largas, sin rutas personales, sin caracteres invisibles y, salvo linkedin_publish.py, sin importaciones de red.

## Contribuir

Ver CONTRIBUTING.md.

## Licencia

MIT. Ver LICENSE, que conserva los avisos de copyright exigidos por la licencia.

## Autor

Matías Allende
LinkedIn: https://www.linkedin.com/in/matiasallende/
Correo: matias.allende.contreras@gmail.com
