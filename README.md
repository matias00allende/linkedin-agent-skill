# AgentIn

Once skills de Claude Code para redactar y revisar contenido de LinkedIn en español de Chile, más un limpiador de borradores que corre en tu máquina. Ninguna skill se conecta a LinkedIn ni usa tus cuentas o claves: trabajan solo con lo que tú pegas, y todo lo que escribes o publicas en LinkedIn lo haces tú, a mano (la exportación a PDF del carrusel usa un navegador local, que podría hacer otras conexiones salvo que bloquees la red; ver la referencia del carrusel).

Las skills redactan; tú revisas, corriges y publicas a mano. AgentIn no publica, comenta, reacciona ni envía mensajes por ti, a propósito: ver Cumplimiento con LinkedIn.

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

Antes de copiar, lee el script skills/ag-voz/scripts/agentin.py (solo biblioteca estándar, sin red). Las skills van todas juntas porque ag-voz contiene el script y el criterio que usan las demás. En Windows (PowerShell): Copy-Item -Recurse skills\ag-* $HOME\.claude\skills\

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

- clean quita caracteres invisibles que se cuelan al copiar y pegar, ordena la tipografía y trata muletillas con un léxico editable. Cada entrada es replace (cambio seguro), delete (se borra solo si el script estima que la oración queda correcta; no entiende el sentido) o flag (solo se señala). Conserva los emoji compuestos de la persona (y los señala) y protege enlaces, hashtags, menciones, código y citas entre comillas o paréntesis de los cambios de vocabulario y tipografía; los caracteres invisibles se quitan en todo el texto, también dentro de ellos, así que revisa el código si importa su forma exacta. No toca los párrafos ni las comas, salvo al convertir una raya en coma o al borrar una muletilla, y reduce tres o más saltos de línea a dos. El borrado de muletillas solo ocurre al comienzo de una oración; revisa siempre el resultado, porque el script no entiende el sentido.
- check entrega un índice de estilo con cinco chequeos y su cobertura. Los que no tienen datos suficientes se marcan como no evaluables. Son heurísticas sin calibración, no una medición de voz ni de autoría.
- limits cuenta caracteres contra limits.json (valores reportados, no verificados).
- tmp new crea una carpeta temporal única para los borradores (en Linux y macOS con permisos solo para el usuario; en Windows dependen de tu carpeta de usuario); tmp clean RUTA borra una carpeta marcada por tmp new y comprueba que ya no existe.
- stats calcula tasa de interacción, comentarios por reacción e impresiones por seguidor desde un CSV. Valida los números, distingue un cero de un dato ausente y no compara filas con distinta cobertura.

Límites de seguridad conocidos: --lexicon carga expresiones regulares que se ejecutan sobre tu texto, así que usa solo léxicos tuyos o revisados (una expresión mal escrita puede tardar mucho). tmp clean valida ubicación y marca, pero la comprobación y el borrado no son atómicos y la marca no es una frontera de seguridad: no protege frente a otro proceso con tus mismos permisos. La entrada máxima es de 2 MB.

Códigos de salida: 0 correcto, 1 resultado negativo pedido (limits fuera de rango, check con --fail-under), 2 error de uso. La salida es texto plano.

## Cumplimiento con LinkedIn

AgentIn no accede a LinkedIn: no usa su API, no raspa páginas, no automatiza un navegador sobre LinkedIn y no guarda sesiones ni claves. Eso reduce el riesgo, pero no certifica cumplimiento: también cuentan el contenido, el destinatario y el uso que le des a lo redactado. Resumen propio, en español, de las páginas oficiales consultadas el 2026-10-26 (consulta las cláusulas en su texto original antes de apoyarte en ellas):

- Términos de Uso de las APIs, 3.1.26: prohíbe usar el contenido o las APIs para automatizar la publicación en los servicios de LinkedIn. Cláusula 3.1.24: prohíbe acceder, almacenar, mostrar o facilitar la transferencia de contenido de LinkedIn obtenido por raspado, rastreo u otra tecnología fuera de las APIs. Ambas son cláusulas de los términos de las APIs; el Acuerdo de Usuario es otro documento, con su propio alcance.
- Acuerdo de Usuario, 8.2: prohíbe usar bots u otros métodos automatizados no autorizados para enviar o redirigir mensajes, crear, comentar, dar me gusta, compartir o recompartir publicaciones, o generar interacción inauténtica; también prohíbe software, scripts, robots o extensiones para raspar o copiar los servicios.
- Software y extensiones prohibidos (centro de ayuda): LinkedIn no permite rastreadores, bots, plug-ins o extensiones de navegador de terceros que automaticen actividad.
- Políticas de la comunidad profesional: no enviar spam, no usar las invitaciones para mensajes promocionales a quien no conoces, no aumentar artificialmente la interacción, usar tu identidad real y compartir solo información real.

Qué hace AgentIn dentro de eso: redacta textos que tú copias y publicas; analiza lo que tú pegas o exportas de tu propia cuenta (por ejemplo un CSV de tu analítica); nunca llama a LinkedIn. No uses estas skills con material obtenido mediante raspadores, extensiones o herramientas de automatización. Las skills de comentarios, respuestas, mensajes e invitaciones entregan borradores para que los envíes tú, uno a uno, y piden que sean genuinos y dirigidos a una persona concreta, no masivos ni promocionales.

Qué no hace esta versión: publicar por API (ni siquiera con confirmación de cada texto), programar, publicar en lote, comentar, reaccionar, enviar mensajes o invitaciones, ni leer el perfil o la bandeja por ti. Hubo una skill de publicación asistida por la API oficial en las versiones 1.7 a 1.11; se retiró en la 2.0.0 porque la cláusula 3.1.26 no distingue si un humano confirma cada texto y no tenemos una confirmación de LinkedIn de que ese uso encaje con sus términos.

Esto no es asesoría legal. Las reglas de LinkedIn cambian: si vas a usar AgentIn de forma distinta a la descrita, revisa sus términos vigentes.

## Política de uso

1. Ayuda a mejorar tu voz, no a ocultar autoría. Si usas IA para redactar, cómo lo comunicas lo decides tú.
2. No evade detectores de IA ni los mide. El índice de estilo mide muletillas, ritmo e higiene tipográfica. Nadie puede prometer el veredicto de un detector externo.
3. Respeta las reglas de cada contexto. Si un trabajo académico, un concurso, una postulación o un empleador exige declarar o prohíbe el uso de IA, cúmplelo.
4. Revisión humana siempre. Las skills de redacción entregan textos para copiar; las de análisis y planificación entregan resultados; y un texto con marcadores {{dato: ...}} pendientes no está listo para publicar.
5. Los hechos son tuyos. Las skills no inventan cifras, clientes ni experiencias; preguntan o dejan {{dato: ...}}.
6. No automatiza LinkedIn. No publica, comenta, reacciona, envía mensajes o invitaciones, raspa ni controla un navegador sobre LinkedIn, porque sus términos prohíben los métodos automatizados no autorizados para esas acciones. Todo lo que sale a LinkedIn lo envías tú.

## Privacidad

agentin.py no envía datos a ningún servicio externo. Las skills trabajan con Claude, y lo que pegas en el chat (mensajes, comentarios, perfiles de otras personas) llega al modelo que uses. Son datos personales de terceros: no pegues información sensible. El archivo ~/.claude/agentin/log.md puede guardar nombres de personas con quienes interactúas. El material fuente que pegas (publicaciones, mensajes, transcripciones) se trata como dato, no como instrucciones; tu encargo directo sí orienta la tarea.

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

Cubren casos de borde del limpiador, las propiedades de cada entrada del léxico, la ejecución por subproceso con la codificación local de Windows y la higiene del repositorio: sin rayas largas, sin rutas personales, sin caracteres invisibles y sin importaciones de red.

## Contribuir

Ver CONTRIBUTING.md.

## Licencia

Apache License 2.0. Ver LICENSE. El archivo NOTICE conserva el aviso de copyright y la licencia MIT de la obra original de la que parte este proyecto, como exige esa licencia.

## Autor

Matías Allende
[LinkedIn](https://www.linkedin.com/in/matiasallende/) · matias.allende.contreras@gmail.com
