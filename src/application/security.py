from dataclasses import dataclass

from src.domain.errors import Forbidden


@dataclass(frozen=True)
class Principal:
    id: str
    role: str

    def require(self, *roles):
        if self.role not in roles:
            raise Forbidden("El rol no permite esta acción")

    def event_access(self, event):
        if self.role in {"ADMIN", "COORDINADOR"}:
            return
        if self.role == "CLIENTE" and event.client_id == self.id:
            return
        raise Forbidden("No tiene acceso a este evento")
