import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
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

    @app.get("/", include_in_schema=False)
    def home():
        """Interfaz de usuario estática servida desde el mismo contenedor de la API."""
        return FileResponse(Path(__file__).resolve().parent / "web" / "index.html")

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
