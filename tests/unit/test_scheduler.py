import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.infrastructure.scheduler import expiry_loop


def test_scheduler_runs_then_stops_on_cancellation(monkeypatch):
    service = Mock()
    sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
    monkeypatch.setattr("src.infrastructure.scheduler.asyncio.sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(expiry_loop(service, 60))
    assert service.expire_requests.call_count == 1
    assert service.expire_requests.call_args.args[0].id == "SISTEMA"


def test_scheduler_recovers_from_transient_database_error(monkeypatch, caplog):
    service = Mock()
    service.expire_requests.side_effect = RuntimeError("Base temporalmente no disponible")
    sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
    monkeypatch.setattr("src.infrastructure.scheduler.asyncio.sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(expiry_loop(service, 60))
    assert "se reintentará" in caplog.text
