# Seguridad

Este servidor maneja **tu sesión de Tinkercad**: `.tinkercad_profile/` es, en la
práctica, tu contraseña. Por eso:

## Nunca lo compartas

- No subas `.tinkercad_profile/` a un issue, a un gist ni a un zip.
- No pegues cookies, tokens ni capturas del panel de cuenta.
- Si alguien te pide el perfil "para reproducir el bug", está pidiendo tu
  cuenta. No se lo des.

`.tinkercad_profile/`, `.env` y `screenshots/` están en `.gitignore`; si aparecen
en un `git status`, algo se rompió: no commitees y avisa.

## Cómo reportar un problema de seguridad

Usa el **reporte privado de vulnerabilidades** de GitHub (*Security → Report a
vulnerability*) en lugar de un issue público. Incluye:

- versión del repo (`git rev-parse --short HEAD`),
- qué tool se llamaba y con qué parámetros (sin credenciales),
- traza o mensaje de error.

## Alcance

Esto automatiza el editor web de Tinkercad con un navegador. No hay servidor
propio, no se envían datos a terceros y todas las llamadas van a
`tinkercad.com` y su API. El riesgo real no es una fuga del código: es el
perfil del navegador y la cuenta de cada quien.
