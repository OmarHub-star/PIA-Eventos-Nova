# Eventos Nova · PIA · Equipo 16

Aplicación de coordinación de bodas, graduaciones y eventos empresariales. Implementa propuestas versionadas, aceptación, contrato, anticipo, proveedores, cambios, servicios adicionales, liquidación y cierre mediante una API REST con persistencia.

**Integrantes:** Omar Tadeo Gasca Deciga (2226708), Osmar Abdi Sánchez Santiago (2226699), Gabriela Alejandra Fernández Briones (2226870). Curso: Componentes de Lógica de Negocios. Profesor: Miguel Ángel Gómez Marroquín. FIME, UANL. Entrega preparada el 6 de noviembre de 2026.

## Empezar en Windows

1. Instala Python 3.12 con la opción de agregar Python al PATH.
2. Extrae el ZIP completo en una carpeta nueva y abre `EJECUTAR_WINDOWS.bat`.
3. Abre http://localhost:8000/docs. El archivo `.env` generado contiene tokens aleatorios locales. En **Authorize**, pega solo el token del rol que vas a utilizar.
4. Sigue `docs/DEMO.md`. Cada acción indica el rol correspondiente. Cambia de token al cambiar de actor.

La API constituye la aplicación funcional. Swagger UI es la interfaz de demostración. Las notificaciones son registros internos persistentes con destinatario, disponibles en auditoría para Coordinación y Administración. No se envían correos ni mensajes externos.

## Ejecución manual

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/init_env.py
python scripts/serve.py
```

Linux/macOS: también puedes ejecutar `sh EJECUTAR_LINUX_MAC.sh`. SQLite conserva los cambios en `nova.db` entre reinicios. Para limpiar una demo, usa otro identificador de evento o una nueva base de datos; no se borra la base automáticamente.

## Docker Compose: DB, App y Tests

Requiere Docker Engine y Docker Compose v2.

```bash
python scripts/init_env.py
docker compose up --build -d db app
docker compose --profile quality run --rm tests
docker compose down
```

La base PostgreSQL 16 conserva sus datos en `nova_db`. La prueba externa usa registros únicos y limpia solo sus propios datos. **No uses `down -v` si necesitas conservar el volumen.** Para reproducir el job de CI en una instalación de prueba:

```bash
docker compose --profile quality up --build --abort-on-container-exit --exit-code-from tests
```

## Verificación

```bash
ruff check src tests scripts
ruff format --check src tests scripts
python -m pytest -q --cov=src --cov-fail-under=80 --cov-report=html --cov-report=xml
python scripts/evaluate_csv.py
```

`docs/evidencias/RESUMEN.md` contiene los resultados reales de esta preparación. Las pruebas de PostgreSQL y HTTP externo se omiten explícitamente si no se configuran `TEST_DATABASE_URL` y `API_BASE_URL`. La suite cubre dominio, API, transacciones, concurrencia optimista, permisos, límites temporales y los 140 casos CSV con sus adaptaciones documentadas. Las historias Gherkin se verifican mediante los tests identificados en la matriz; no se requiere un motor BDD adicional.

## Estructura

- `src/domain`: `Event`, `Proposal`, `SupplierRequest`, `Money`, `Line`, Specifications, política de cambios y máquina de estados.
- `src/application`: casos de uso, puertos, reloj e identidad autenticada.
- `src/infrastructure`: SQLAlchemy, unidad de trabajo, registro de eventos, reservas de proveedores, importador y temporizador.
- `src/api`: esquemas Pydantic y endpoints FastAPI.
- `docs`: BRD, historias/Gherkin, BPMN, glosario, arquitectura, ADR, OpenAPI, trazabilidad, evidencia, despliegue y defensa.
- `data/original`: los seis CSV del paquete del alumno, conservados sin modificación.
- `tests`: pruebas unitarias, integración y adaptación de CSV.

## Reglas y decisiones principales

- El contrato y el 30% acumulado del monto firmado confirman el evento. El anticipo registrado se conserva al cancelar.
- Se acepta una respuesta de proveedor antes de cumplir 48 horas continuas. Al cumplirlas vence. El temporizador revisa cada 60 segundos y genera alerta interna; la API también rechaza respuestas vencidas de inmediato. Una sola instancia de la aplicación basta para esta demo.
- A 15 días exactos no hay recargo. A 14 o menos se calcula 15% sobre el incremento y Administración autoriza o rechaza.
- Los cambios del Cliente esperan revisión comercial. Coordinación puede aplicar un cambio dentro de plazo. El incremento es cotizado manualmente y su aprobación queda registrada. No existe una tarifa por invitado en los documentos fuente.
- Las versiones anteriores permanecen en el historial. Evento, propuesta y avisos se confirman en la misma transacción.
- Los adicionales requieren registro y pago específico por terminal o transferencia antes de prestarse. La liquidación general puede ocurrir antes o después de la ejecución, según H1 del informe U3. El cierre exige saldo cero, adicionales resueltos y acta.
- Roles y propietarios se validan a partir del token configurado, nunca de un rol enviado en el cuerpo. Los tokens son por identidad, reemplazables por configuración. No se implementa OAuth, firma electrónica certificada ni pasarela bancaria: se registran comprobantes y referencias.

## API

Swagger: `/docs`. OpenAPI vivo: `/openapi.json`. Copia versionada: `docs/api/openapi.json`. Salud de aplicación y DB: `/health`. Importes decimales en MXN serializados como texto. `401` token inválido, `403` permiso, `404` referencia inexistente, `409` transición/duplicado/concurrencia, `422` formato o regla inválida. Este contrato usa `422` para validación, no `400`.

## Fuentes y continuidad

- U2: cuatro PDF y paquete PIA entregados en el ZIP.
- U3: https://github.com/Oxmar99/EventosNova-Equipo-16, revisión `ca039e6e79fb070a3b9b8c09dfcc20e71ef85a82`.
- U4: https://github.com/OmarHub-star/Actividad-Unidad-4, revisión `b7ff94501a38e0d2b1cc6d63698dfd4d74fb8df0`.
- U5: https://github.com/OmarHub-star/Unidad-5-COMPONENTES-DE-L-GICA-DE-NEGOCIOS, revisión `eb2401519d947a9c8de2dc1d03d116820042c13b`.

Se reutilizan las técnicas de U4/U5, como Decimal, Specification, pytest, casos parametrizados, commit/rollback y CI. Las reglas de descuentos de las tiendas de práctica no se trasladan al negocio de Eventos Nova. Consulta `docs/ADAPTACION_DATOS.md`.

## GitHub y despliegue

El repositorio de entrega es **https://github.com/OmarHub-star/PIA-Eventos-Nova** y permanece privado. **URL pública del sistema: pendiente de desplegar.** No se presenta un workflow sin ejecutar como evidencia de CI activo.

`docs/DESPLIEGUE.md` contiene los pasos de publicación, variables y comprobaciones. Se eligió Render para la demostración y `render.yaml` fija el plan Free tanto en App como en PostgreSQL. El servicio gratuito puede suspenderse por inactividad y la base vence a los 30 días. No se configura un plan de pago. La cuenta de Render debe quedar vinculada y el despliegue debe verificarse antes de anunciar una URL funcional.

El desarrollo asistido por IA está registrado en `docs/USO_IA.md`. El equipo debe revisar y comprender la entrega, registrar sus aportaciones reales y defender las decisiones. Los commits preparados no acreditan participación individual ni sustituyen el historial de trabajo del equipo.
