# Seguridad

Este repo automatiza un navegador con **tu sesión de Tinkercad**. La sesión es
una credencial: quien tenga el perfil del navegador puede entrar a tu cuenta.

## Qué nunca se comparte

| Ruta | Qué es |
|---|---|
| `packages/bridge/.tinkercad_profile/` | Tu sesión de Tinkercad (cookies incluidas). Es tu contraseña |
| `.env` | Variables de entorno con secretos locales |
| `~/.config/jarvis/` | Configuración personal de OpenCode y secretos |

Si alguien necesita el MCP, hace su propio login con **su** cuenta. Pasar el
perfil solo tiene sentido entre máquinas tuyas.

Ya están en `.gitignore`, pero un `git add -f` o un zip armado a mano se las
salta. Antes de publicar un archivo comprimido:

```bash
unzip -l paquete.zip | grep -Ei 'profile|env|cookie|token|\.netrc'
```

## Si algo se filtró

1. Cierra la sesión de Tinkercad desde la cuenta (Autodesk ID → seguridad).
2. Borra `packages/bridge/.tinkercad_profile/` y vuelve a hacer el login.
3. Si estaba en un commit, reescribe la historia (`git filter-repo`) y fuerza
   el push: borrar el archivo en un commit nuevo **no** lo saca del historial.

## Reportar una vulnerabilidad

Abre un reporte privado en **Security → Report a vulnerability** de este repo.
No abras un issue público con el detalle.

## Alcance

- El proyecto no es de Autodesk y no tiene soporte oficial.
- Manejar el editor web puede ir contra los términos de uso de Tinkercad. El
  riesgo real es que suspendan la cuenta, no una demanda. Un build a la vez.
- El código corre en tu máquina con tus credenciales: no hay servidor nuestro
  ni telemetría.
