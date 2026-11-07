import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from src.api import schemas as s
from src.application.security import Principal
from src.application.services import NovaService
from src.domain.errors import BusinessError
from src.infrastructure.database import SqlUnitOfWork, make_engine, metadata
from src.infrastructure.fixtures import seed
from src.infrastructure.scheduler import expiry_loop


def create_app(database_url=None, tokens=None, clock=None, seed_data=None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./nova.db")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = make_engine(url)
    credentials = tokens if tokens is not None else json.loads(os.getenv("TOKENS_JSON", "{}"))
    roles = {"ADMIN", "COORDINADOR", "CLIENTE", "PROVEEDOR"}
    if any(
        not token or value.get("role") not in roles or not value.get("id")
        for token, value in credentials.items()
    ):
        raise ValueError("TOKENS_JSON requiere tokens, id y rol válido")

    def uow_factory():
        return SqlUnitOfWork(engine)

    service = NovaService(uow_factory, clock)

    @asynccontextmanager
    async def lifespan(app):
        metadata.create_all(engine)
        if (
            seed_data
            if seed_data is not None
            else os.getenv("SEED_DATA", "false").lower() == "true"
        ):
            seed(uow_factory)
        interval = float(os.getenv("EXPIRY_INTERVAL_SECONDS", "60"))
        task = asyncio.create_task(expiry_loop(service, interval)) if interval > 0 else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            engine.dispose()

    app = FastAPI(
        title="Eventos Nova - PIA Equipo 16",
        version="1.0.0",
        lifespan=lifespan,
        description="Propuestas, contratación, proveedores, cambios y cierre. Importes en MXN. Autenticación Bearer por usuario. Las alertas quedan en el registro interno de eventos.",
    )
    app.state.engine = engine
    app.state.service = service
    bearer = HTTPBearer(auto_error=False)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Portal del sistema de gestión de eventos Eventos Nova, PIA Equipo 16.">
  <title>Eventos Nova | PIA Equipo 16</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; color: #f5f7ff;
      background: radial-gradient(circle at 90% 10%, #273e69 0, transparent 38%),
                  radial-gradient(circle at 10% 90%, #27305a 0, transparent 40%), #0b1223; }
    .wrap { max-width: 980px; margin: auto; padding: 28px 24px 64px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    .brand { display: flex; align-items: center; gap: 12px; font-size: 19px; font-weight: 800; }
    .mark { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 13px;
      background: linear-gradient(135deg, #9a76ff, #44d9d0); color: #10152c; }
    .eyebrow { color: #9db4ff; font-size: 13px; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; }
    main { padding-top: 100px; }
    h1 { font-size: clamp(42px, 7vw, 74px); line-height: 1.08; letter-spacing: -.045em; margin: 16px 0 22px; }
    .highlight { color: #83e4dd; }
    .intro { max-width: 640px; font-size: 19px; line-height: 1.7; color: #c8d0e5; }
    .actions { display: flex; flex-wrap: wrap; gap: 14px; margin: 34px 0 56px; }
    a.button { display: inline-flex; align-items: center; justify-content: center; padding: 15px 23px;
      border-radius: 12px; font-weight: 750; text-decoration: none; min-height: 52px; }
    .primary { background: #8ceee4; color: #0b1827; }
    .secondary { color: #f5f7ff; border: 1px solid #52617e; background: #ffffff0d; }
    a:focus-visible { outline: 3px solid #ffd68a; outline-offset: 4px; }
    .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .card { border: 1px solid #354361; border-radius: 18px; padding: 24px; background: #ffffff0a; }
    .card h2 { font-size: 17px; margin: 0 0 10px; }
    .card p { margin: 0; line-height: 1.55; color: #b9c4dc; font-size: 14px; }
    footer { margin-top: 58px; padding-top: 22px; border-top: 1px solid #34405b; color: #aab6cc; font-size: 13px; }
    @media (max-width: 650px) { main { padding-top: 66px; } .cards { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand"><span class="mark" aria-hidden="true">✦</span> Eventos Nova</div>
      <span class="eyebrow">PIA · Equipo 16</span>
    </header>
    <main>
      <div class="eyebrow">Sistema de gestión de eventos</div>
      <h1>Tu evento,<br><span class="highlight">nuestra organización.</span></h1>
      <p class="intro">Plataforma académica para administrar propuestas, contrataciones,
      proveedores y seguimiento de eventos mediante una API REST desarrollada con FastAPI.</p>
      <div class="actions">
        <a class="button primary" href="/docs">Explorar API / Swagger</a>
        <a class="button secondary" href="/health">Ver estado del sistema</a>
      </div>
      <div class="cards" aria-label="Funciones del sistema">
        <section class="card"><h2>📅 Eventos</h2>
          <p>Consulta, creación y seguimiento del ciclo de vida de cada evento.</p></section>
        <section class="card"><h2>🤝 Proveedores</h2>
          <p>Solicitudes, asignaciones y respuestas para coordinar los servicios.</p></section>
        <section class="card"><h2>📊 Administración</h2>
          <p>Auditoría, cambios, pagos y consulta de rentabilidad de eventos.</p></section>
      </div>
    </main>
    <footer>Eventos Nova · Proyecto Integrador de Aprendizaje · Equipo 16
      · <a href="/openapi.json" style="color:#9febe4">Especificación OpenAPI</a></footer>
  </div>
</body>
</html>"""


    def authenticated(auth: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if auth:
            for token, principal in credentials.items():
                if hmac.compare_digest(auth.credentials, token):
                    return Principal(principal["id"], principal["role"])
        raise HTTPException(401, "Token ausente o inválido", headers={"WWW-Authenticate": "Bearer"})

    @app.exception_handler(BusinessError)
    async def business_error(request, exc):
        return JSONResponse(
            status_code=exc.status, content={"detail": str(exc), "type": type(exc).__name__}
        )

    @app.get("/health", tags=["Operación"])
    def health():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/me", tags=["Identidad"])
    def me(principal=Depends(authenticated)):
        return vars(principal)

    @app.get("/catalogs/{kind}", tags=["Catálogos"])
    def catalog(kind: str, principal=Depends(authenticated)):
        return service.catalog(principal, kind)

    @app.get("/events", tags=["Eventos"])
    def list_events(principal=Depends(authenticated)):
        return service.list_events(principal)

    @app.post(
        "/events",
        status_code=201,
        tags=["Eventos"],
        responses={
            422: {"description": "Datos o regla inválidos"},
            409: {"description": "Identificador duplicado"},
            404: {"description": "Referencia inexistente"},
        },
    )
    def create_event(body: s.CreateEvent, principal=Depends(authenticated)):
        return service.create_event(principal, body.model_dump(mode="json", exclude_none=True))

    @app.get("/events/{event_id}", tags=["Eventos"])
    def get_event(event_id: str, principal=Depends(authenticated)):
        return service.get_event(principal, event_id)

    @app.get("/events/{event_id}/audit", tags=["Auditoría"])
    def audit(event_id: str, principal=Depends(authenticated)):
        return service.audit(principal, event_id)

    @app.get("/events/{event_id}/profitability", tags=["Administración"])
    def profitability(event_id: str, principal=Depends(authenticated)):
        return service.profitability(principal, event_id)

    # Cada operación genera un esquema de entrada propio en OpenAPI.
    def command_endpoint(command, model):
        def endpoint(event_id: str, body, principal=Depends(authenticated)):
            return service.execute(
                principal, event_id, command, body.model_dump(mode="json", exclude_none=True)
            )

        endpoint.__annotations__["body"] = model
        endpoint.__name__ = "event_" + command
        return endpoint

    commands = [
        ("send", s.Empty),
        ("accept", s.Empty),
        ("reject", s.Reason),
        ("sign", s.Reference),
        ("pay", s.Payment),
        ("revise", s.Revision),
        ("change", s.Change),
        ("approve", s.Approval),
        ("reject_change", s.Rejection),
        ("extra", s.Extra),
        ("pay_extra", s.ExtraPayment),
        ("deliver_extra", s.ExtraId),
        ("start", s.Empty),
        ("finish", s.Empty),
        ("close", s.Closure),
        ("cancel", s.Reason),
    ]
    for command, model in commands:
        app.add_api_route(
            "/events/{event_id}/" + command,
            command_endpoint(command, model),
            methods=["POST"],
            tags=["Ciclo del evento"],
            responses={
                401: {"description": "Token inválido"},
                403: {"description": "Rol o propietario incorrecto"},
                404: {"description": "Evento inexistente"},
                409: {"description": "Conflicto de estado o concurrencia"},
                422: {"description": "Regla de negocio o entrada inválida"},
            },
        )

    @app.post("/events/{event_id}/requests", status_code=201, tags=["Proveedores"])
    def request_supplier(
        event_id: str, body: s.SupplierAssignment, principal=Depends(authenticated)
    ):
        return service.request_supplier(
            principal, event_id, body.model_dump(mode="json", exclude_none=True)
        )

    @app.get("/requests", tags=["Proveedores"])
    def requests(event_id: str | None = None, principal=Depends(authenticated)):
        return service.requests(principal, event_id)

    @app.post("/requests/expire", tags=["Proveedores"])
    def expire(principal=Depends(authenticated)):
        return service.expire_requests(principal)

    @app.post("/requests/{request_id}/respond", tags=["Proveedores"])
    def respond(request_id: str, body: s.Response, principal=Depends(authenticated)):
        return service.supplier_action(principal, request_id, "respond", body.model_dump())

    @app.post("/requests/{request_id}/cancel", tags=["Proveedores"])
    def cancel_supplier(request_id: str, body: s.Reason, principal=Depends(authenticated)):
        return service.supplier_action(principal, request_id, "cancel", body.model_dump())

    return app


app = create_app()
