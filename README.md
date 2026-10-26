# AgentIn

AgentIn reúne once skills de Claude Code para redactar y revisar contenido de LinkedIn en español de Chile. Incluye un script que limpia borradores en tu equipo.

Trabaja con el material que tú entregas, sin conectarse a LinkedIn ni usar tus cuentas o claves. Tú revisas los textos y los publicas o envías a mano.

Para exportar carruseles a PDF usa un navegador local. Ese navegador podría hacer otras conexiones si no bloqueas la red; consulta skills/ag-carousel/references/plantilla-pdf.md.

AgentIn tampoco comenta ni reacciona por ti. La sección Cumplimiento con LinkedIn explica estos límites.

No está afiliado a LinkedIn ni a Anthropic. LinkedIn es una marca de sus titulares.

## Qué hace

- /ag-post: convierte una idea o experiencia en una publicación lista para copiar; si lo pides, propone aperturas alternativas a partir de 21 fórmulas.
- /ag-comment: comentarios para publicaciones de otras personas, de nueve tipos.
- /ag-reply: redacta respuestas a los comentarios de tu propia publicación y las prioriza según su urgencia, aporte y riesgo.
- /ag-profile: evalúa tu perfil con una rúbrica de 12 ítems y reescribe las secciones que más lo necesitan; el puntaje depende de cuánto del perfil pueda revisar.
- /ag-plan: define qué publicar y cómo organizarlo, como calendario, lista de temas o criterios de posicionamiento; si lo pides, también propone con quién interactuar.
- /ag-voz: limpieza, revisión de estilo y conteo de caracteres de un borrador.
- /ag-carousel: redacta un carrusel diapositiva por diapositiva y, si apruebas el texto y tienes un navegador compatible, genera el PDF.
- /ag-repurpose: identifica ideas para publicaciones en un contenido largo tuyo y señala de qué fragmento sale cada una; las redacta cuando lo pides.
- /ag-dm: redacta la nota de invitación, el primer mensaje y, si corresponde, seguimientos.
- /ag-inbox: ordena los mensajes recibidos en oportunidades, reclutadores, pares, pedidos y spam.
- /ag-audit: analiza tus publicaciones anteriores, calcula métricas a partir de un CSV e identifica patrones asociados a mejores resultados.

Instaladas como plugin, los comandos llevan prefijo: /agentin:ag-post.

## Criterio de trabajo

Todas las skills siguen el criterio común de skills/ag-voz/references/criterio.md. Usan tu objetivo, audiencia y preferencias para resolver el encargo, y preguntan solo si falta información esencial.

Al redactar, separan el texto para copiar de las notas. Al analizar o planificar, muestran primero el resultado. Distinguen hechos, inferencias y recomendaciones, y revisan si el contenido podría comprometerte a ti o a tu institución.

Las publicaciones se basan en experiencias que tú aportas. Los hashtags y las fórmulas de interacción se usan solo cuando ayudan al texto.

## Instalación segura

El paquete incluye instrucciones para Claude y un script de Python que se ejecuta en tu equipo. Clona el repositorio y revisa ambos antes de instalarlos, en vez de pedir la instalación directamente desde un enlace.

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

Luego define tu voz: copia templates/voz.md a ~/.claude/agentin/voz.md y complétalo. También puedes pegar publicaciones tuyas y pedirle a Claude que prepare el archivo a partir de ellas.

Si no creas ese archivo, las skills usarán las preferencias que indiques o una muestra breve de tu escritura. Mientras más contexto entregues, mejor podrán ajustar el tono.

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

- clean elimina caracteres invisibles, normaliza la tipografía y revisa muletillas con un léxico editable.

  El léxico usa tres acciones: replace reemplaza una expresión, delete la borra al comienzo de una oración si la comprobación mecánica permite hacerlo y flag solo la señala.

  clean conserva los emojis compuestos y los señala. Protege enlaces, hashtags, menciones, código y citas entre comillas o paréntesis de los cambios de vocabulario y tipografía, pero elimina caracteres invisibles también dentro de ellos. Revisa esos elementos si necesitas conservar su forma exacta.

  Mantiene la separación entre párrafos y reduce tres o más saltos de línea a dos. Solo modifica comas al convertir una raya o borrar una muletilla. Revisa siempre el resultado: el script no interpreta el sentido del texto.

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
