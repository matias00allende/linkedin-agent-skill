# Configuración de ag-publish

Se hace una sola vez. Lo hace la persona en su propia cuenta; AgentIn no crea apps, no usa credenciales ajenas y no incluye una app compartida.

## Cómo encaja

- Tú publicas en tu perfil personal. El permiso w_member_social (producto Share on LinkedIn) autoriza a una app a publicar a nombre del miembro que la autoriza, es decir, tú. El script usa tu identificador de persona como autor.
- La app necesita una página de empresa solo como dueña para registrarla. LinkedIn lo exige y no acepta un perfil personal. Esa página no publica nada, y el administrador de la página debe aprobar la asociación (el plazo que da LinkedIn no está verificado aquí). Si la página es tuya, la apruebas tú.
- Publicar en una página de empresa u organización requiere otro permiso (w_organization_social) y otra aprobación de LinkedIn. AgentIn no lo hace.
- Si no tienes una página, puedes crear una mínima solo para esto, con tu nombre de proyecto. Es pública, tú quedas como administrador y no necesita contenido ni seguidores. Si no quieres asociar una página a tu nombre, no uses ag-publish: todo lo demás de AgentIn funciona igual y publicas a mano.

## Alcance y condiciones

Los Términos de Uso de las APIs de LinkedIn prohíben, en su cláusula 3.1.26, usar las APIs para automatizar publicaciones. El Acuerdo de Usuario prohíbe además los métodos automatizados no autorizados para comentar, reaccionar o enviar mensajes. Por eso ag-publish es publicación asistida:

- una pieza por vez, con vista previa y aprobación de esa pieza;
- sin programar, sin lotes, sin bucles, sin repetir el mismo texto y con un tope local de 3 en 24 horas (es una salvaguarda del programa, no una cifra que LinkedIn haya dicho que permite);
- la confirmación la escribe la persona, en su terminal;
- sin comentarios, reacciones, mensajes ni invitaciones.

Ninguna de estas salvaguardas es una excepción confirmada por LinkedIn. Esto reduce el riesgo, pero no es asesoría legal ni garantía de cómo LinkedIn lo interprete: la línea entre "publicar con aprobación" y "automatizar" la define LinkedIn. Si piensas usarlo con más intensidad, o quieres tranquilidad contractual, pregunta por escrito al soporte de desarrolladores de LinkedIn (linkedin.com/help/linkedin/ask/dsapi) y guarda la respuesta.

## Qué se necesita

1. Una app en el portal de desarrolladores de LinkedIn (www.linkedin.com/developers). El formulario pide nombre, página de LinkedIn, logo y aceptar los términos de la API. Aceptar esos términos lo haces tú.
2. En la pestaña Products de la app, activar dos productos de autoservicio (la documentación de LinkedIn los llama permisos abiertos, disponibles sin aprobación especial):
   - Share on LinkedIn: concede w_member_social.
   - El producto de inicio de sesión con OpenID Connect (en el portal su nombre empieza con Sign In): concede openid y profile, necesarios para saber quién es el miembro.
3. En la pestaña Auth, registrar una dirección de retorno que empiece con https. Puede ser cualquiera que controles: no hace falta que la página cargue, porque la dirección se copia de la barra del navegador.
4. Tres variables de entorno:
   - LINKEDIN_CLIENT_ID: el identificador de la app.
   - LINKEDIN_CLIENT_SECRET: el secreto de la app. Guárdalo en tu gestor de secretos, no en el repositorio ni en el chat.
   - LINKEDIN_REDIRECT_URI: la dirección de retorno registrada, idéntica.
5. Opcional: LINKEDIN_API_VERSION, en formato AAAAMM. Si no la defines, el script usa la versión indicada en su constante DEFAULT_API_VERSION.

## Autorizar

1. auth-start imprime una dirección. Ábrela en el navegador e inicia sesión en LinkedIn.
2. Al aceptar, LinkedIn redirige a tu dirección de retorno con los parámetros code y state. Copia la dirección completa de la barra del navegador.
3. Ejecuta auth-finish en tu terminal, sin argumentos: el programa te pide la dirección en pantalla y así no queda en el historial ni en la lista de procesos (si prefieres, también acepta la dirección como argumento). Debe ser exactamente la dirección registrada, con sus parámetros. Intercambia el código por un token, consulta quién eres y guarda la sesión en ~/.agentin/token.json con permisos 600. En Windows los permisos dependen de tu carpeta de usuario.

El script compara el valor state y se niega a continuar si no coincide. La sesión dura 60 días; para apps de autoservicio no hay renovación automática y hay que repetir la autorización.

## Primera prueba

1. Escribe un texto corto y neutro, sin datos de nadie.
2. Ejecuta post con --visibility CONNECTIONS y revisa la vista previa.
3. En tu propia terminal (no la del agente), ejecuta post con --confirm y la huella, y escríbela cuando el programa lo pida. El programa se niega si no hay una terminal interactiva.
4. Abre el enlace que imprime el script y comprueba cómo se ve en LinkedIn.
5. Si no te gusta, borra la prueba con delete IDENTIFICADOR --yes, o desde LinkedIn.

## Qué guarda y dónde

- token.json: el token de acceso, su vencimiento y el identificador del miembro.
- publicaciones.json: huella, fecha, estado (pendiente, publicado, incierto o borrado) e identificador de cada intento. Sirve para el tope de 3 al día, para no repetir un texto y para delete. Un borrado no libera el tope ni el texto. Es un límite local: si borras el archivo, se pierde.
- previews.json: huellas de las vistas previas recientes. El script exige una vista previa de las últimas 24 horas antes de publicar.
- auth_state.json: temporal, se borra al terminar. Guarda la app y la dirección de retorno del intento.

La dirección de retorno completa que copias es sensible mientras el código siga vigente (30 minutos): no la pegues en el chat ni la guardes. Aunque la página no cargue, el servidor de esa dirección puede haber recibido y registrado el código. Nada de esto se guarda sin tu consentimiento; logout borra la sesión, las vistas previas y el estado de autorización, pero conserva publicaciones.json, que sostiene el tope de 3 al día y evita repetir un texto. Si quieres borrarlo, mira antes tu perfil: al borrarlo se pierden esas salvaguardas. CONNECTIONS limita quién ve la publicación, pero no la vuelve confidencial: no publiques nada que no quieras que alguien copie.

Para cerrar: logout borra la sesión del equipo (no el registro de publicaciones). Para que LinkedIn deje de aceptar el token, revoca el permiso de la app en la configuración de tu cuenta de LinkedIn.

## Cómo se envía una publicación

Se usa la Posts API (POST /rest/posts), que reemplaza a ugcPosts. Cada llamada lleva las cabeceras Linkedin-Version (obligatoria, LinkedIn no aplica una por defecto) y X-Restli-Protocol-Version 2.0.0. LinkedIn mantiene cada versión al menos un año, así que el valor por defecto del script se revisa una vez al año. El texto se envía en el formato de la API, con los caracteres reservados escapados; las palabras con # salen como hashtag real y no se generan menciones. Con enlace, la API no lee el título de la página: hay que darlo con --link-title.

## Lo que está verificado y lo que no

Verificado en la documentación oficial de LinkedIn (octubre de 2026): el flujo de autorización con código y la dirección del token; que Share on LinkedIn y el inicio de sesión con OpenID Connect son permisos abiertos; la Posts API, su versión más reciente (202610), sus cabeceras y su esquema; el formato de texto y sus caracteres reservados; que la Posts API reemplaza a ugcPosts; la vigencia de 60 días del token; la cláusula 3.1.26 de los términos de las APIs; que una app exige una página de empresa que no sea un perfil personal.

No verificado: que /rest/posts acepte tu app solo con los dos productos de autoservicio (la documentación lista w_member_social, pero no lo he podido probar con una cuenta real); qué página de empresa es la "predeterminada" para desarrolladores individuales (la ayuda de LinkedIn no la nombra); el límite de solicitudes diarias de la Posts API (la página antigua indicaba 150 por miembro); el comportamiento real con tu cuenta; cómo interpretaría LinkedIn tu uso frente a la cláusula 3.1.26.

## Siguientes pasos posibles

Nada de esto está implementado. Cada uno se evaluaría aparte y con tu autorización.

- Publicar el PDF de un carrusel (ag-carousel): la Posts API admite documentos (se sube con la Documents API y se referencia en la publicación). Habría que verificar que tu producto lo permita y agregar la subida. Hoy el PDF se sube a mano.
- Imágenes: se suben con la Images API y se referencian por identificador. Mismo método.
- Comentar o reaccionar: la Comments API existe y su permiso (w_member_social_feed) figura en la documentación, pero no está confirmado que se obtenga por autoservicio, y los términos restringen la automatización. Hoy no se implementa y ag-comment solo redacta.
- Mensajes e invitaciones: no hay API pública. Seguirán siendo manuales.
- Métricas: leer tus publicaciones requiere r_member_social, que es restringido y solo para usuarios aprobados. ag-audit seguirá trabajando con el CSV que exportes.
- Renovación de la sesión cada 60 días y revisión anual de la versión de la API.
