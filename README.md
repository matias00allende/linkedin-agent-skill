# AgentIn

Once skills de Claude Code para redactar y revisar contenido de LinkedIn en español (Chile) e inglés, más un limpiador de borradores que corre en tu máquina. Sin cuentas, sin claves de API, sin conexión a LinkedIn.

**Nada se publica hasta que tú lo hagas.** Las skills redactan; tú revisas, corriges y publicas.


No está afiliado a LinkedIn ni a Anthropic. LinkedIn es una marca de sus titulares.

## Qué hace

| Comando | Para qué |
| --- | --- |
| `/ag-post` | Una idea a un post. Tres ganchos entre [21 fórmulas](skills/ag-post/hook-formulas.json), un borrador y un bloque listo para copiar. |
| `/ag-comment` | Comentarios para posts de otras personas, de nueve tipos, según lo que el post realmente es. |
| `/ag-reply` | Respuestas a los comentarios de tu propio post, ordenados por valor. |
| `/ag-profile` | Puntúa tu perfil sobre 100 con una [rúbrica de 12 ítems](skills/ag-profile/rubric.json) y reescribe en orden de impacto. |
| `/ag-plan` | La semana: qué publicar, cuándo y con quién interactuar. Escribe `~/.claude/agentin/plan.md`. |
| `/ag-voz` | Limpieza y revisión de estilo de un borrador, y conteo de caracteres. Ver abajo. |
| `/ag-carousel` | Carruseles: texto diapositiva por diapositiva y el PDF. |
| `/ag-repurpose` | Un contenido largo propio a una semana de posts que se sostienen solos. |
| `/ag-dm` | Nota de invitación, primer mensaje y dos seguimientos. |
| `/ag-inbox` | Ordena la bandeja en oportunidades, reclutadores, pares, pedidos y spam. |
| `/ag-audit` | Qué funcionó en lo ya publicado, con métricas calculadas por script desde un CSV. |

Si instalas AgentIn como plugin, los comandos llevan el prefijo del plugin: `/agentin:ag-post`.

## Instalación segura

Estas skills son instrucciones que Claude ejecuta y un script de Python que corre en tu equipo. Revísalas antes de instalarlas. No pegues en un chat un "instala esto" con un enlace: clona y lee.

```bash
git clone https://github.com/matias00allende/agentin.git
cd agentin
# 1. Lee el único script (un archivo, solo biblioteca estándar, sin red):
#    skills/ag-voz/scripts/agentin.py
# 2. Corre las pruebas:
python -m unittest discover -s tests
# 3. Copia las skills (todas juntas: ag-voz contiene el script que usan las demás):
cp -r skills/ag-* ~/.claude/skills/            # macOS o Linux
```

En Windows (PowerShell): `Copy-Item -Recurse skills\ag-* $HOME\.claude\skills\`

Para usarlas solo en un proyecto, copia las mismas carpetas a `.claude/skills/` del proyecto.

Como plugin, desde Claude Code:

```
/plugin marketplace add matias00allende/agentin
/plugin install agentin@agentin
```

Luego dedica diez minutos a [`templates/voz.md`](templates/voz.md) (versión en inglés: [`templates/voice.en.md`](templates/voice.en.md)). Cópialo a `~/.claude/agentin/voz.md` y complétalo, o pega tres posts tuyos en Claude y pide "escribe mi voz.md a partir de estos". Todas las skills lo leen. Sin él, todo sale con la voz promedio.

Requisitos: Claude Code y Python 3.9 o superior (en Windows `python`, en macOS y Linux `python3`). Escrito para 3.9 o superior; las pruebas se han corrido localmente en Python 3.14 y el repositorio trae una configuración de integración continua para Linux, Windows y macOS.

## El limpiador de borradores (`/ag-voz`)

Un solo archivo, `skills/ag-voz/scripts/agentin.py`, solo biblioteca estándar. Corre en tu máquina y no sube nada. Siempre se invoca con `python -I` y la ruta completa.

```bash
python -I skills/ag-voz/scripts/agentin.py clean  borrador.txt -o limpio.txt --report
python -I skills/ag-voz/scripts/agentin.py check  borrador.txt limpio.txt
python -I skills/ag-voz/scripts/agentin.py limits --kind invite nota.txt
python -I skills/ag-voz/scripts/agentin.py stats  analitica.csv --followers 4200
```

- **`clean`** quita caracteres invisibles que se cuelan al copiar y pegar (espacios de ancho cero, marca de orden de bytes, guion blando, caracteres "tag" que pueden esconder texto), ordena la tipografía (rayas, comillas curvas, puntos suspensivos) y trata las muletillas con un léxico editable en español e inglés. Cada entrada del léxico es `replace` (cambio seguro), `delete` (se borra solo si la oración queda correcta) o `flag` (solo se señala). Conserva los emoji compuestos, los alfabetos que necesitan marcas invisibles, los enlaces, los `#hashtags`, las `@menciones` y el código, y no toca saltos de párrafo.
- **`check`** entrega un índice de estilo con cinco chequeos (ritmo, concreción, muletillas, higiene, voz). Los chequeos sin datos suficientes se marcan `n/e` en vez de inventar un valor.
- **`limits`** cuenta caracteres contra los límites de [`limits.json`](skills/ag-voz/data/limits.json) (reportados, no verificados).
- **`stats`** calcula tasa de interacción, razón comentarios/reacciones y múltiplo de alcance desde un CSV (separador coma, punto y coma o tabulador).

Códigos de salida: 0 correcto, 1 resultado negativo pedido (`limits` fuera de rango, `check --fail-under`), 2 error de uso.

## Política de uso

1. **Ayuda a mejorar tu voz, no a ocultar autoría.** Si usas IA para redactar, cómo lo comunicas lo decides tú. AgentIn no incluye funciones para disimularlo.
2. **No evade detectores de IA y no los mide.** El índice de estilo mide muletillas, ritmo e higiene tipográfica. No predice el veredicto de ningún detector externo y nadie puede prometerlo honestamente.
3. **Respeta las reglas de cada contexto.** Si un trabajo académico, un concurso, una postulación o un empleador exige declarar o prohíbe el uso de IA, cúmplelo.
4. **Revisión humana siempre.** Cada skill termina en un texto para copiar y pegar. Tú lo lees, lo corriges y lo publicas.
5. **Los hechos son tuyos.** Las skills no inventan cifras, clientes ni experiencias. Si falta un dato, preguntan o dejan `{{dato: ...}}`.
6. **No automatiza LinkedIn.** No hay publicación, raspado ni envío automático: el Acuerdo de Usuario de LinkedIn restringe esas prácticas y pueden costarte la cuenta.

## Privacidad

El limpiador procesa el texto en tu equipo. Pero las skills trabajan con Claude, y lo que pegas en el chat (mensajes, comentarios, perfiles de otras personas) llega al modelo que uses. Esos textos contienen datos personales de terceros: no pegues información sensible, y recuerda que `~/.claude/agentin/log.md` puede guardar nombres de personas con quienes interactúas.

El contenido que pegas se trata como dato, no como instrucciones: si un mensaje de terceros contiene órdenes dirigidas al modelo, las skills deben ignorarlas.

## Lo que no está verificado

Varias ideas de oficio circulan como hechos sobre LinkedIn (el mejor horario, qué formato retiene más, si los enlaces restan alcance, los topes de invitaciones, la forma de la exportación de analítica). AgentIn las trata como hipótesis de partida, no como resultados, y usa `/ag-audit` para contrastarlas con los datos de tu propia cuenta. Los límites de caracteres de `limits.json` también son reportados y no verificados: confírmalos en la interfaz.

## Estructura

```
skills/ag-voz/           limpieza, estilo, límites y métricas (SKILL.md, scripts/agentin.py, data/)
skills/ag-post/          SKILL.md, hook-formulas.json (21 fórmulas, es y en)
skills/ag-profile/       SKILL.md, rubric.json (rúbrica de 100 puntos)
skills/ag-<otras>/       comment, reply, plan, carousel, repurpose, dm, inbox, audit
templates/               voz.md, voice.en.md
tests/                   pruebas con unittest
.claude-plugin/          manifiestos de plugin y marketplace
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren casos de borde conocidos (comas y párrafos, muletillas, Windows y UTF-8, texto en español), las propiedades de cada entrada del léxico, y la higiene del propio repositorio (sin rayas largas, sin rutas personales, sin caracteres invisibles, sin importaciones de red).

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

MIT. Ver [LICENSE](LICENSE), que conserva los avisos de copyright exigidos por la licencia.

## Autor

Matías Allende
[LinkedIn](https://www.linkedin.com/in/matiasallende/) · matias.allende.contreras@gmail.com

---

## English summary

AgentIn is a set of eleven Claude Code skills for drafting and reviewing LinkedIn content in Spanish (Chile) and English, plus a local, stdlib-only Python tool (`skills/ag-voz/scripts/agentin.py`) that cleans drafts (invisible characters, typography, stock phrases), scores style, counts characters and computes engagement metrics from a CSV. It never posts, scrapes or automates LinkedIn; you review and publish. It is not an AI-detector evasion tool and makes no claim about any detector. Install by cloning, reading the single script, running `python -m unittest discover -s tests`, then copying `skills/ag-*` into `~/.claude/skills/` (or as a plugin: `/plugin marketplace add matias00allende/agentin`, `/plugin install agentin@agentin`).
