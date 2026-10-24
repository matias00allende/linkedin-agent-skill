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

Chrome o Edge sin interfaz, con un perfil temporal sin sesión y sin cuentas. Ajusta la ruta del ejecutable y usa una carpeta temporal para el perfil, que se borra al terminar.

```
chrome --headless --disable-gpu --no-pdf-header-footer --user-data-dir=PERFIL_TEMPORAL --print-to-pdf=carrusel.pdf carrusel.html
```

Antes de exportar, comprueba que el HTML no contiene recursos externos: busca "http", "src=", "<script", "<iframe" y "@import". Un HTML sin recursos remotos no impide por sí solo que el navegador haga otras conexiones: si necesitas procesamiento estrictamente local, exporta con la red bloqueada; si no puedes garantizarlo, adviértelo a la persona antes de exportar.

## Revisión

Abre el PDF y revisa que cada diapositiva sea una página, que nada se corte y que los metadatos (título, autor) no revelen datos que la persona no quiere publicar. Un solo color de acento y letra de al menos 28 px.
