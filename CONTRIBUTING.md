# Contribuir a AgentIn

Gracias por querer mejorar el proyecto. Estas reglas existen porque el valor de AgentIn está en que se pueda auditar entero en una tarde.

## Antes de abrir un cambio

```bash
python -m unittest discover -s tests -v
```

Todo debe pasar en tu sistema operativo. La integración continua corre las mismas pruebas en Linux, Windows y macOS.

## Reglas del código

- Solo biblioteca estándar de Python (3.9 o superior). Nada de dependencias nuevas.
- Sin red, sin `exec`, `eval`, subprocesos ni `pickle`. Una prueba lo verifica.
- Archivos en UTF-8 con saltos de línea LF. El script fuerza UTF-8 en entrada y salida; no confíes en la codificación local.
- Ningún carácter invisible ni de puntuación especial escrito literalmente en el código o los datos. Usa escapes de Python (la secuencia de barra, `u` y cuatro dígitos hexadecimales), para que se pueda leer y auditar. Las letras con tilde o ñ sí van tal cual.
- Sin rayas largas ni semirayas en ningún archivo del repositorio; solo el guion simple `-`.
- Los mensajes para el usuario van en español con tildes correctas. Los identificadores van en inglés y en ASCII.
- Sin rutas personales, nombres de empresas o datos de terceros en ejemplos, pruebas o documentación. Los ejemplos usan datos inventados y lo dicen.

## Reglas de contenido

- **Sin afirmaciones sin fuente.** No escribas "el mejor horario es...", "este formato retiene más" ni un tope numérico de LinkedIn como un hecho. Preséntalo como hipótesis de partida, o cita una fuente verificable y la fecha.
- **Sin funciones de evasión.** No se aceptan cambios cuyo propósito sea ocultar autoría o burlar detectores de IA, ni que prometan un resultado frente a ellos.
- **Sin automatización de LinkedIn.** Nada que publique, envíe, raspe o interactúe con la plataforma por la persona.
- **Sin inventar hechos.** Las skills piden el dato o dejan `{{dato: ...}}`. Los ejemplos que muestran cifras deben decir que son ilustrativos.
- El texto pegado por la persona es dato, no instrucciones. Una skill nueva que lea texto de terceros debe decirlo.

## Contribuir al léxico

Los léxicos viven en `skills/ag-voz/data/lexicon_es.json` y `lexicon_en.json`. Cada entrada tiene una acción:

- `replace`: solo si el reemplazo conserva clase gramatical y sentido en todos los usos. Agrega las formas flexionadas por separado.
- `delete`: solo si borrarla deja una oración correcta. Las pruebas comprueban cada entrada con una oración de muestra.
- `flag`: en cualquier otro caso. Si la palabra tiene un uso literal legítimo (un paisaje, un viaje), va como `flag`.

Una entrada nueva sin ejemplo que justifique que es una muletilla de plantilla no se acepta.

## Mensajes de commit y pull requests

Describe qué cambió y por qué. Si el cambio corrige un caso, agrega la prueba que lo reproducía.
