# Eventos Nova · PIA · Equipo 16

Aplicación de coordinación de bodas, graduaciones y eventos empresariales. Implementa propuestas versionadas, aceptación, contrato, anticipo, proveedores, cambios, servicios adicionales, liquidación y cierre mediante una API REST con persistencia.

**Integrantes:** Omar Tadeo Gasca Deciga (2226708), Osmar Abdi Sánchez Santiago (2226699), Gabriela Alejandra Fernández Briones (2226870). Curso: Componentes de Lógica de Negocios. Profesor: Miguel Ángel Gómez Marroquín. FIME, UANL. Entrega preparada el 6 de noviembre de 2026.

## Acceso público a Eventos Nova (Render)

**Uso principal: portal web para clientes, coordinación, proveedores y administración.** No necesitas instalar Python, Docker ni dependencias en el equipo para utilizar la aplicación: el servidor y la API se ejecutan en Render.

- **[Abrir interfaz de usuario de Eventos Nova]**(https://eventos-nova-pia-cv0t.onrender.com/)
- [Swagger UI — documentación y pruebas de la API](https://eventos-nova-pia-cv0t.onrender.com/docs)
- [Especificación OpenAPI](https://eventos-nova-pia-cv0t.onrender.com/openapi.json)
- [Estado de la aplicación y base de datos](https://eventos-nova-pia-cv0t.onrender.com/health)
- [Servicio en Render (panel de administración)](https://dashboard.render.com/web/srv-dbn6m9ec6qcc73cqj5pg)

### Acceso y roles

El **portal web** muestra formularios y botones de acuerdo con cada rol. El responsable del sistema proporciona un token distinto para cada identidad: **ADMIN**, **COORDINADOR**, **CLIENTE** y **PROVEEDOR**. Para entrar en el portal, pega el token en el campo de acceso. El portal verifica el rol contra `/me` y utiliza la API existente en segundo plano. Swagger es opcional para inspección técnica; sus rutas de negocio están igualmente protegidas con Bearer.

La interfaz no genera contraseñas ni usuarios y no almacena el token en `localStorage` o `sessionStorage`: la clave se mantiene solo en memoria y se pierde al actualizar la página o cerrar sesión. Los tokens reales están configurados fuera del repositorio, en la variable de entorno `TOKENS_JSON` de Render. **No publiques tokens, contraseñas, el archivo `.env` ni capturas que revelen credenciales.** La plantilla `.env.example` solo contiene identificadores de reemplazo; no autoriza peticiones. Los tokens que hayan sido compartidos deben rotarse antes de una entrega con datos no ficticios.

Recorrido guiado por roles y reglas: [docs/DEMO.md](docs/DEMO.md). El portal es el frontend funcional, FastAPI es el backend y Swagger queda como interfaz técnica de demostración. Las notificaciones se registran internamente y no se envían por correo.

### Ejecución local opcional (desarrollo y pruebas)

Solo es necesaria si se desea modificar o probar el código fuera de Render. Se utiliza Python 3.12. Después de crear y activar un entorno virtual de Python, instala las dependencias con `python -m pip install -r requirements.txt`, ejecuta `python scripts/init_env.py` para crear la configuración ficticia local y arranca con `python scripts/serve.py`. El Swagger local estará en `http://localhost:8000/docs`.

Los archivos de arranque rápido `.bat` y `.sh` se retiraron porque no son necesarios para usar Render. Los scripts Python permanecen: `scripts/serve.py` arranca **también** la aplicación dentro de Docker; `scripts/init_env.py` participa en las pruebas de CI.

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
- `src/api`: esquemas Pydantic, endpoints FastAPI y `web/index.html` (interfaz de usuario HTML/CSS/JavaScript, servida desde `/`).
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

## GitHub, integración y despliegue

- **Repositorio público:** [OmarHub-star/PIA-Eventos-Nova](https://github.com/OmarHub-star/PIA-Eventos-Nova), rama `main`.
- **Despliegue:** [Eventos Nova en Render](https://eventos-nova-pia-cv0t.onrender.com/). El servicio utiliza el `Dockerfile` y escucha en el puerto suministrado por el entorno.
- **CI:** [Ejecución verificada antes de la limpieza](https://github.com/OmarHub-star/PIA-Eventos-Nova/actions/runs/42343111534): comprobaciones de formato y calidad; 270 pruebas aprobadas en contenedores con PostgreSQL y cobertura del 97.39 %. Las próximas modificaciones se verifican en su propia ejecución.
- **Actualización:** Render tiene activado el despliegue automático al pasar las verificaciones (`checksPass`). El job `deploy` de GitHub Actions permite opcionalmente un hook, pero Render puede desplegar por su propia integración GitHub.
- **Documentos de entrega:** [reporte PDF](entrega/Reporte_Final_PIA_EventosNova_Equipo16.pdf), [presentación PPTX](entrega/Presentacion_Defensa_EventosNova.pptx) y [presentación PDF](entrega/Presentacion_Defensa_EventosNova.pdf).

Consulta [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) para operar el servicio y [docs/evidencias/RESUMEN.md](docs/evidencias/RESUMEN.md) para diferenciar las pruebas históricas de las verificaciones actuales.

El uso de asistencia de IA y los límites del proyecto se documentan en [docs/USO_IA.md](docs/USO_IA.md). El equipo debe revisar sus aportaciones reales y prepararse para explicar y defender el código.
