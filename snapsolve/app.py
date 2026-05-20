from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from .config import AppConfig
from .network import build_access_info
from .service import SnapSolveService
from .web import INDEX_HTML


def create_app(config: AppConfig) -> FastAPI:
    service = SnapSolveService(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service.bind_loop(asyncio.get_running_loop())
        service.start_hotkey()
        try:
            yield
        finally:
            service.stop_hotkey()

    app = FastAPI(title="SnapSolve", lifespan=lifespan)
    app.state.service = service

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(INDEX_HTML)

    @app.get("/events")
    async def events() -> StreamingResponse:
        return StreamingResponse(
            service.stream_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/capture")
    async def capture() -> dict[str, object]:
        return await service.request_capture()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/info")
    async def info() -> dict[str, object]:
        access = build_access_info(config.server)
        return {
            "listen_host": access.listen_host,
            "port": access.port,
            "local_url": access.local_url,
            "lan_urls": access.lan_urls,
            "lan_enabled": access.lan_enabled,
            "hotkey": {
                "enabled": config.hotkey.enabled,
                "sequence": config.hotkey.sequence,
            },
        }

    return app
