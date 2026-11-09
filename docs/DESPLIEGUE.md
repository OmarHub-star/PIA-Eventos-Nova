# Despliegue y operación de Eventos Nova

## Estado real del proyecto

- **Repositorio:** [PIA-Eventos-Nova](https://github.com/OmarHub-star/PIA-Eventos-Nova), público y con rama principal `main`.
- **Servicio de Render:** [eventos-nova-pia-cv0t](https://dashboard.render.com/web/srv-dbn6m9ec6qcc73cqj5pg).
- **Aplicación:** https://eventos-nova-pia-cv0t.onrender.com/
- **Swagger:** https://eventos-nova-pia-cv0t.onrender.com/docs
- **OpenAPI:** https://eventos-nova-pia-cv0t.onrender.com/openapi.json
- **Salud:** https://eventos-nova-pia-cv0t.onrender.com/health

**Última verificación previa a la limpieza (7 de noviembre de 2026):** Render confirmó el despliegue `dep-dbnbgdi9lscs73bsmd10` en estado `live`, asociado al commit `e1f43a15dfea9a9d2aef87daabfc2bce6881c986`. La ejecución [GitHub Actions 42343111534](https://github.com/OmarHub-star/PIA-Eventos-Nova/actions/runs/42343111534) terminó satisfactoriamente. Cada modificación posterior requiere una nueva verificación antes de afirmar que está publicada.

## 1. ¿Qué utiliza Render?

El servicio es de tipo **Web Service / Docker** y construye la aplicación con `Dockerfile`, que instala `requirements.txt` y ejecuta `python scripts/serve.py`. La configuración de Render sigue la rama `main` y permite despliegue automático tras superar las comprobaciones de GitHub (`checksPass`). La ruta de salud configurada es `/health`.

Render sustituye la necesidad de instalar Python o dependencias **en el equipo que usa la aplicación**, pero no elimina la instalación dentro del contenedor. Los archivos `EJECUTAR_WINDOWS.bat` y `EJECUTAR_LINUX_MAC.sh` eran accesos directos para desarrollo local; no son parte de la operación en la nube.

Se conserva `render.yaml` para documentar el despliegue como infraestructura declarativa y `docker-compose.yml` porque la etapa de pruebas con PostgreSQL de GitHub Actions todavía lo utiliza. El `Dockerfile`, `scripts/serve.py`, `scripts/init_env.py`, `src/`, `tests/` y los seis CSV originales siguen siendo necesarios para ejecución, pruebas o evidencias.

## 2. Variables y seguridad

| Variable | Función |
| --- | --- |
| `DATABASE_URL` | Conexión a PostgreSQL; debe configurarse de forma segura en el servicio. |
| `TOKENS_JSON` | Mapa de tokens Bearer a identidades y roles. Es un secreto; no guardarlo en Git. |
| `SEED_DATA` | Permite inicializar el catálogo y los datos de demostración cuando está habilitado. |
| `PORT` | Puerto de escucha; Render o el contenedor proporcionan el valor correspondiente. |
| `EXPIRY_INTERVAL_SECONDS` | Frecuencia opcional de revisión de solicitudes vencidas; valor por defecto del código: 60 segundos. |

Los tokens se administran mediante variables de entorno privadas en Render y se distribuyen por separado a los usuarios autorizados. Swagger `/docs` es accesible sin clave, pero los endpoints de negocio protegidos requieren el botón **Authorize** y un token Bearer válido. Los roles implementados son `ADMIN`, `COORDINADOR`, `CLIENTE` y `PROVEEDOR`. Nunca incluir credenciales reales en capturas ni en archivos del repositorio. Regenerar las credenciales que hayan quedado expuestas.

## 3. Flujo de cambios y publicación

1. Revisar o modificar el código en GitHub, rama `main` (o mediante una rama de trabajo y pull request).
2. GitHub Actions ejecuta comprobaciones con Ruff, pruebas pytest y verificación de los 140 casos CSV adaptados.
3. La etapa `containers` construye Docker Compose y ejecuta pruebas contra PostgreSQL; exige una cobertura mínima del 80 %.
4. Render, conectado a GitHub, despliega automáticamente los cambios que satisfacen sus verificaciones. **No hace falta crear un nuevo servicio ni iniciar un despliegue manual si Auto Deploy ya está habilitado.**
5. Comprobar en Render que el despliegue correspondiente al último commit esté en estado `Live`; después comprobar `/`, `/health`, `/docs` y `/openapi.json`.

El workflow contiene también un job `deploy` con hook opcional `RENDER_DEPLOY_HOOK`. Si no hay hook, ese paso se omite; no significa que Render esté desconectado, pues el servicio tiene integración GitHub propia. No se deben compartir hooks privados.

## 4. Desarrollo y comprobación local (opcional)

Solo es necesario para desarrollo, depuración o reproducir las pruebas fuera de Render. Python 3.12, `requirements.txt`, `scripts/init_env.py` y `scripts/serve.py` permiten ejecutar una instancia local; el archivo `.env` generado queda excluido de Git. Las pruebas de integración completas utilizan `docker-compose.yml` y PostgreSQL. Nunca ejecutar `docker compose down -v` sobre una base cuyos datos deban conservarse.

## 5. Evidencias para el PIA

Presentar enlaces reales del repositorio y el despliegue, el commit exacto, una ejecución aprobada de GitHub Actions, estado `Live` en Render, `/health`, Swagger y ejemplos de reglas de negocio y permisos. Para la demostración se usan datos ficticios y se ocultan los tokens.

Los registros históricos de `docs/evidencias/` documentan ejecuciones anteriores; el estado vigente debe comprobarse en [GitHub Actions](https://github.com/OmarHub-star/PIA-Eventos-Nova/actions) y [Render](https://dashboard.render.com/web/srv-dbn6m9ec6qcc73cqj5pg). El recorrido recomendado está en [DEMO.md](DEMO.md).

## 6. Limitaciones operativas

El plan gratuito puede suspender el servicio por inactividad y tiene límites de almacenamiento/retención sujetos a las condiciones vigentes de Render. Verificar el servicio antes de la defensa. El esquema actual se prepara con `metadata.create_all`; no sustituye un sistema de migraciones de producción. Las reglas de caducidad se verifican al procesar solicitudes y mediante el temporizador cuando el servicio está ejecutándose. Respaldar cualquier base con datos que se necesiten conservar.
