# Publicación y verificación

## Estado de esta entrega

Aplicación y pruebas preparadas y verificadas localmente según `evidencias/RESUMEN.md`. No hay URL pública ni ejecución remota de GitHub Actions que se pueda atribuir todavía a este PIA. Docker y PostgreSQL deben verificarse donde estén disponibles. Los archivos de configuración se incluyen completos.

Repositorio creado: https://github.com/OmarHub-star/PIA-Eventos-Nova (privado). El usuario autorizó la carga del proyecto completo y delegó la selección del alojamiento. Se seleccionó Render Free para App y PostgreSQL; el YAML fija ambos planes explícitamente. La base gratuita vence a los 30 días y el servicio puede suspenderse tras 15 minutos sin uso. El temporizador de vencimientos retoma su revisión cuando el servicio vuelve a estar activo; la validación del límite de respuesta se aplica siempre al procesar la solicitud. Fuente vigente: https://render.com/docs/free.

## 1. Repositorio GitHub

El equipo indica un repositorio para el PIA, preferentemente independiente de los laboratorios U4/U5. Agrega el contenido de esta carpeta a su raíz, incluidos `.github`, `.env.example`, Dockerfile y los documentos. Nunca agregues `.env`, bases con datos reales ni tokens. El pipeline se activa con push o pull request. Registra el enlace de la ejecución verde y el SHA realmente presentado.

```bash
git init -b main
git add .
git commit -m "Integrar PIA de Eventos Nova con pruebas y documentación"
# Configura el remote con la URL real elegida por el equipo y realiza el push.
```

Los commits deben ser reales y con autoría correcta. No reconstruyas contribuciones ni fechas ficticias. Si se conserva el historial preparado, revisa `historial_preparacion.bundle` y sus instrucciones antes de importar. El equipo documenta sus cambios posteriores.

## 2. Comprobación de contenedores

Ejecuta `python scripts/init_env.py`, después `docker compose --profile quality up --build --abort-on-container-exit --exit-code-from tests`. Espera salida 0 de Tests. Se ejecutan pruebas de PostgreSQL y HTTP real adicionales a SQLite. Comprueba que App está saludable. Guarda el log real, fecha y commit. No publiques las variables ni tokens en capturas.

## 3. Plataforma de despliegue

Se incluye un Dockerfile y `render.yaml` como configuración propuesta. La plataforma deberá aceptar una aplicación Python con conexión PostgreSQL, una variable `PORT` y persistencia. Revisa disponibilidad del plan y costos en tu cuenta antes de activar recursos. También puedes usar cualquier plataforma equivalente admitida por el profesor.

Variables necesarias: `DATABASE_URL` (PostgreSQL), `TOKENS_JSON` (identidades con tokens aleatorios), `SEED_DATA=true` para demostración ficticia, `PORT` suministrado por hosting y opcional `EXPIRY_INTERVAL_SECONDS=60`. Las URLs `postgresql://` se normalizan al driver psycopg3. El repositorio no contiene secretos reales.

La API no implementa un formulario para generar usuarios. Genera los tokens por identidad con `init_env.py` y transfiere exclusivamente el JSON al panel de variables del servicio. El archivo local permanece fuera de Git. Configura una sola réplica/worker para el temporizador de esta demo.

## 4. CD tras pruebas

Desactiva un despliegue automático que no espere a los checks y configura el secreto de GitHub `RENDER_DEPLOY_HOOK` con el hook privado del servicio, si utilizas esa modalidad. El job deploy solo lo invoca en main y tras quality y containers. La aceptación del hook solicita un despliegue, no certifica que haya terminado correctamente. Verifica el estado y el endpoint real antes de afirmar que está publicado.

## 5. Evidencia de producción

Registra en README: URL real del repositorio, SHA, URL del sistema, `/health`, `/docs` y `/openapi.json`, fecha y enlace a Actions. Recorre la demo contra esa URL. Captura estados válidos, un rechazo 409/422 y un flujo persistido tras reinicio. Usa datos ficticios y oculta los tokens. Entrega la misma versión que se presenta.

## 6. Operación

Conservar el volumen de PostgreSQL. Realizar backup antes de cambiar la estructura JSON. Esta versión inicial usa `metadata.create_all`, no un sistema de migraciones para esquemas productivos existentes. El temporizador vuelve a evaluar vencimientos al estar en ejecución; tras una caída, el siguiente ciclo recupera las solicitudes pendientes vencidas. La aceptación vencida siempre se rechaza por la regla del dominio.
