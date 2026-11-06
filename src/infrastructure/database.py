from copy import deepcopy
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from src.domain.errors import Conflict, NotFound

metadata = MetaData()
documents = Table(
    "aggregates",
    metadata,
    Column("kind", String(30), primary_key=True),
    Column("id", String(80), primary_key=True),
    Column("data", JSON, nullable=False),
    Column("version", Integer, nullable=False),
)
outbox = Table(
    "domain_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("event_id", String(80), index=True),
    Column("name", String(80), nullable=False),
    Column("actor", String(80), nullable=False),
    Column("at", String(40), nullable=False),
    Column("payload", JSON, nullable=False),
)
bookings = Table(
    "supplier_bookings",
    metadata,
    Column("supplier_id", String(80), primary_key=True),
    Column("day", String(10), primary_key=True),
    Column("request_id", String(80), unique=True, nullable=False),
)


def make_engine(url: str):
    options = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    return create_engine(url, **options)


class SqlUnitOfWork:
    """El snapshot JSON conserva el agregado; la versión evita escrituras perdidas."""

    def __init__(self, engine):
        self.engine = engine
        self.versions = {}

    def __enter__(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        return self

    def __exit__(self, *exc):
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def get(self, kind, entity_id):
        row = (
            self.connection.execute(
                select(documents).where(documents.c.kind == kind, documents.c.id == entity_id)
            )
            .mappings()
            .first()
        )
        if row is None:
            raise NotFound(f"No existe {kind}: {entity_id}")
        self.versions[(kind, entity_id)] = row["version"]
        return deepcopy(row["data"])

    def list(self, kind):
        rows = self.connection.execute(
            select(documents).where(documents.c.kind == kind).order_by(documents.c.id)
        ).mappings()
        result = []
        for row in rows:
            self.versions[(kind, row["id"])] = row["version"]
            result.append(deepcopy(row["data"]))
        return result

    def save(self, kind, entity_id, data):
        key = (kind, entity_id)
        version = self.versions.get(key)
        try:
            if version is None:
                self.connection.execute(
                    insert(documents).values(
                        kind=kind, id=entity_id, data=deepcopy(data), version=1
                    )
                )
                self.versions[key] = 1
            else:
                result = self.connection.execute(
                    update(documents)
                    .where(
                        documents.c.kind == kind,
                        documents.c.id == entity_id,
                        documents.c.version == version,
                    )
                    .values(data=deepcopy(data), version=version + 1)
                )
                if result.rowcount != 1:
                    raise Conflict("El registro cambió en otra transacción; vuelva a consultarlo")
                self.versions[key] += 1
        except IntegrityError as exc:
            raise Conflict("Identificador duplicado") from exc

    def emit(self, name, event_id, actor, at, payload):
        self.connection.execute(
            insert(outbox).values(
                id=str(uuid4()),
                name=name,
                event_id=event_id,
                actor=actor,
                at=at,
                payload=deepcopy(payload),
            )
        )

    def events(self, event_id):
        return [
            dict(r)
            for r in self.connection.execute(
                select(outbox)
                .where(outbox.c.event_id == event_id)
                .order_by(outbox.c.at, outbox.c.id)
            ).mappings()
        ]

    def book(self, supplier_id, day, request_id):
        try:
            self.connection.execute(
                insert(bookings).values(supplier_id=supplier_id, day=day, request_id=request_id)
            )
        except IntegrityError as exc:
            raise Conflict("Proveedor ocupado en esa fecha") from exc

    def release(self, request_id):
        self.connection.execute(delete(bookings).where(bookings.c.request_id == request_id))

    def commit(self):
        self.transaction.commit()
