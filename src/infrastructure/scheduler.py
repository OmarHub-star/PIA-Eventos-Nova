import asyncio
import logging

from src.application.security import Principal

logger = logging.getLogger(__name__)


async def expiry_loop(service, interval):
    """Un proceso por instancia. El plazo se valida también en respond()."""
    principal = Principal("SISTEMA", "COORDINADOR")
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(service.expire_requests, principal)
        except Exception:
            logger.exception(
                "No se pudieron revisar vencimientos; se reintentará en el siguiente ciclo"
            )
