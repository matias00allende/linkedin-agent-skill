# Configuración de ag-publish

Se hace una sola vez. Lo hace la persona en su propia cuenta; AgentIn no crea apps ni usa credenciales ajenas.

## Qué se necesita

1. Una app en el portal de desarrolladores de LinkedIn (www.linkedin.com/developers). LinkedIn puede pedir asociarla a una página de empresa; compruébalo en el portal, no está verificado aquí.
2. En la pestaña Products de la app, activar dos productos:
   - Share on LinkedIn: concede el permiso w_member_social, que sirve para crear una publicación a nombre del miembro autenticado.
   - El producto de inicio de sesión con OpenID Connect (en el portal su nombre empieza con Sign In): concede openid y profile, necesarios para saber quién es el miembro.
3. En la pestaña Auth, registrar una dirección de retorno que empiece con https. Puede ser cualquiera que controles: no hace falta que la página cargue, porque la dirección se copia de la barra del navegador.
4. Tres variables de entorno:
   - LINKEDIN_CLIENT_ID: el identificador de la app.
   - LINKEDIN_CLIENT_SECRET: el secreto de la app. Guárdalo en tu gestor de secretos, no en el repositorio ni en el chat.
   - LINKEDIN_REDIRECT_URI: la dirección de retorno registrada, idéntica.

## Autorizar

1. auth-start imprime una dirección. Ábrela en el navegador e inicia sesión en LinkedIn.
2. Al aceptar, LinkedIn redirige a tu dirección de retorno con los parámetros code y state. Copia la dirección completa de la barra del navegador.
3. auth-finish con esa dirección entre comillas intercambia el código por un token, consulta quién eres y guarda la sesión en ~/.agentin/token.json con permisos 600. En Windows los permisos dependen de tu carpeta de usuario.

El script compara el valor state y se niega a continuar si no coincide.

## Qué guarda y dónde

- token.json: el token de acceso, su vencimiento y el identificador del miembro.
- publicaciones.json: huella, fecha e identificador de cada publicación hecha con el programa. Sirve para el tope de 3 al día y para no repetir un texto.
- auth_state.json: temporal, se borra al terminar.

Para cerrar: logout borra la sesión del equipo. Para que LinkedIn deje de aceptar el token, revoca el permiso de la app en la configuración de tu cuenta de LinkedIn.

## Lo que está verificado y lo que no

Verificado en la documentación oficial de LinkedIn: el flujo de autorización con código, la dirección del token, el producto Share on LinkedIn y su permiso, la publicación con ugcPosts, el límite de 150 solicitudes diarias por miembro y la vigencia de 60 días del token, sin renovación programática para apps de autoservicio.

No verificado: que la API de ugcPosts siga siendo la vía recomendada (la documentación de esa página es antigua y existen APIs versionadas más nuevas), que LinkedIn acepte tu app sin pasos adicionales, y el comportamiento real con tu cuenta. La primera publicación conviene hacerla con visibilidad CONNECTIONS y revisarla en LinkedIn.

No incluye imágenes, videos ni documentos PDF: solo texto y, si se pide, un enlace.
