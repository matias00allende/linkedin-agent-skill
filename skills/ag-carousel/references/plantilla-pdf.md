# Plantilla para exportar el carrusel a PDF

Uso: copia el HTML a una carpeta temporal única (la misma que describe criterio.md), reemplaza cada sección por el texto de una diapositiva ya escapado como texto, y exporta.

## HTML y CSS base

```
<style>
  @page { size: 1080px 1350px; margin: 0; }
  html, body { margin: 0; }
  section { width: 1080px; height: 1350px; box-sizing: border-box; padding: 96px;
            page-break-after: always; font-size: 40px; }
</style>
<section>Texto de la diapositiva 1</section>
<section>Texto de la diapositiva 2</section>
```

## Exportación

Guarda el HTML y el perfil temporal del navegador dentro de la carpeta que imprime tmp new, y usa rutas absolutas entre comillas. El ejecutable depende del sistema:

- Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" o el msedge.exe de Edge.
- macOS: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome".
- Linux: google-chrome o chromium.

```
EJECUTABLE --headless --disable-gpu --no-pdf-header-footer --user-data-dir="CARPETA/perfil" --print-to-pdf="CARPETA/carrusel.pdf" "file:///CARPETA/carrusel.html"
```

Cuando la persona confirme dónde conservar el PDF, comprueba que el destino no existe (si existe, pide otra ruta), copia sin sobrescribir, verifica que la copia está completa y se abre, y solo entonces borra la carpeta con tmp clean. Verifica que la carpeta temporal ya no existe.

Construye el HTML solo a partir de la plantilla fija de arriba: elementos section con texto escapado, sin atributos, sin enlaces y sin nada tomado del material de terceros que no sea texto. Un HTML así no tiene recursos remotos, pero eso no impide por sí solo que el navegador haga otras conexiones: si necesitas procesamiento estrictamente local, exporta con la red bloqueada; si no puedes garantizarlo, adviértelo a la persona antes de exportar.

## Revisión

Abre el PDF y revisa que cada diapositiva sea una página, que nada se corte y que los metadatos (título, autor) no revelen datos que la persona no quiere publicar. Un solo color de acento y letra de al menos 28 px.
