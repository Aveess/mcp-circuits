# Seguridad

El cerebro no guarda credenciales: la sesión de Tinkercad vive en el
`.tinkercad_profile/` del **puente**, que está en `.gitignore` de ese repo.
Aquí lo que hay que cuidar son los datos acumulados y los informes.

## Reglas

- Nada de `.env`, tokens, cookies ni volcados del perfil en el repo.
- `~/jarvis_data/` (logs, estados, evidencia) queda **fuera** del repo y se
  referencia por variable de entorno, no se copia dentro.
- Los reportes de `docs/reportes/` llevan ids de diseños de Tinkercad. Son
  enlaces de lectura a los circuitos de quien los construyó: si un diseño es
  privado, no pegues su id en un issue.

## Cómo reportar

Reporte privado de vulnerabilidades de GitHub (*Security → Report a
vulnerability*). Sin issues públicos para esto.

## Alcance

Proyecto personal, sin garantías. No hay servicio ni backend propio: todo el
tráfico lo hace el puente hacia `tinkercad.com`.
