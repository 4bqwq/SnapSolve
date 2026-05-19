from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from .config import AppConfig
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
    async def capture() -> dict[str, str]:
        tab_id = await service.handle_capture()
        return {"tab_id": tab_id}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
