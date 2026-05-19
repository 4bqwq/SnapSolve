from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
import json
import threading
import time
from typing import Any
import uuid

import keyboard

from .config import AppConfig
from .model_client import OpenAICompatibleClient
from .prompts import (
    EXTRACT_PROMPT,
    FAST_SYSTEM_PROMPT,
    FAST_USER_PROMPT,
    SLOW_SYSTEM_PROMPT,
    build_slow_user_prompt,
)
from .screenshot import Screenshotter


Lane = str
ANSWER_REASONING_TITLE = "【思考过程】\n"
ANSWER_SEPARATOR = "\n\n--- 正式回答 ---\n\n"
EXTRACT_REASONING_TITLE = "【识别过程】\n"
EXTRACT_SEPARATOR = "\n\n--- 提取结果 ---\n\n"


@dataclass
class StreamResult:
    content: str
    reasoning: str

    @property
    def answer_for_history(self) -> str:
        return self.content or self.reasoning


@dataclass
class TabState:
    id: str
    title: str
    created_at: str
    fast: str = ""
    slow: str = ""
    extract: str = ""
    statuses: dict[str, str] = field(
        default_factory=lambda: {"fast": "idle", "slow": "idle", "extract": "idle"}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "fast": self.fast,
            "slow": self.slow,
            "extract": self.extract,
            "statuses": dict(self.statuses),
        }


class EventHub:
    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._clients.discard(queue)

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        message = self._format(event, payload)
        stale: list[asyncio.Queue[str]] = []
        for queue in tuple(self._clients):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)

    def _format(self, event: str, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=False)
        return f"event: {event}\ndata: {data}\n\n"


class SnapSolveService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.hub = EventHub()
        self.client = OpenAICompatibleClient()
        self.screenshotter = Screenshotter()
        self.tabs: list[TabState] = []
        self.active_tab_id: str | None = None
        self.fast_history: list[dict[str, Any]] = []
        self.slow_history: list[dict[str, Any]] = []
        self._state_lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._hotkey_handle: Any = None
        self._trigger_lock = threading.Lock()
        self._last_trigger_at = 0.0

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start_hotkey(self) -> None:
        if not self.config.hotkey.enabled:
            return
        try:
            self._hotkey_handle = keyboard.add_hotkey(
                self.config.hotkey.sequence,
                self.trigger_from_thread,
                suppress=True,
            )
            print(f"Hotkey registered: {self.config.hotkey.sequence}")
        except Exception as exc:
            print(f"Failed to register hotkey `{self.config.hotkey.sequence}`: {exc}")

    def stop_hotkey(self) -> None:
        if self._hotkey_handle is None:
            return
        try:
            keyboard.remove_hotkey(self._hotkey_handle)
        except Exception:
            pass
        self._hotkey_handle = None

    def trigger_from_thread(self) -> None:
        loop = self._loop
        if loop is None:
            return
        now = time.monotonic()
        with self._trigger_lock:
            if now - self._last_trigger_at < self.config.hotkey.debounce_seconds:
                return
            self._last_trigger_at = now
        loop.call_soon_threadsafe(lambda: asyncio.create_task(self.handle_capture()))

    async def handle_capture(self) -> str:
        tab = await self._create_tab()
        try:
            shot = await asyncio.to_thread(
                self.screenshotter.capture_png,
                self.config.screenshot.monitor_index,
            )
        except Exception as exc:
            message = f"\n截图失败：{exc}\n"
            await self._set_status(tab.id, "fast", "error", message)
            await self._set_status(tab.id, "slow", "error", message)
            return tab.id

        asyncio.create_task(self._run_fast_path(tab.id, shot.png))
        asyncio.create_task(self._run_slow_path(tab.id, shot.png))
        return tab.id

    async def stream_events(self) -> AsyncIterator[str]:
        queue = self.hub.subscribe()
        try:
            yield self.hub._format("snapshot", await self.snapshot())
            while True:
                message = await queue.get()
                yield message
        finally:
            self.hub.unsubscribe(queue)

    async def snapshot(self) -> dict[str, Any]:
        async with self._state_lock:
            return {
                "tabs": [tab.to_dict() for tab in self.tabs],
                "active_tab_id": self.active_tab_id,
            }

    async def _create_tab(self) -> TabState:
        now = datetime.now().strftime("%H:%M:%S")
        async with self._state_lock:
            index = len(self.tabs) + 1
            tab = TabState(
                id=f"tab-{uuid.uuid4().hex}",
                title=f"题目 {index}",
                created_at=now,
            )
            self.tabs.append(tab)
            self.active_tab_id = tab.id

        await self.hub.publish(
            "tab_created",
            {
                "tab": tab.to_dict(),
                "active_tab_id": tab.id,
            },
        )
        return tab

    async def _run_fast_path(self, tab_id: str, image_png: bytes) -> None:
        await self._set_status(tab_id, "fast", "running")
        user_message = self._image_user_message(FAST_USER_PROMPT, image_png)
        async with self._state_lock:
            messages = [
                {"role": "system", "content": FAST_SYSTEM_PROMPT},
                *self.fast_history,
                user_message,
            ]

        try:
            result = await self._stream_to_lane(
                tab_id,
                "fast",
                messages,
                self.config.models.vlm,
                reasoning_title=ANSWER_REASONING_TITLE,
                content_separator=ANSWER_SEPARATOR,
            )
            async with self._state_lock:
                self.fast_history.extend(
                    [
                        user_message,
                        {"role": "assistant", "content": result.answer_for_history},
                    ]
                )
                self.fast_history = self._trim_history(self.fast_history)
            await self._set_status(tab_id, "fast", "done")
        except Exception as exc:
            await self._set_status(tab_id, "fast", "error", f"\n快路失败：{exc}\n")

    async def _run_slow_path(self, tab_id: str, image_png: bytes) -> None:
        await self._set_status(tab_id, "slow", "waiting")
        await self._set_status(tab_id, "extract", "waiting")
        await asyncio.sleep(1.0)
        await self._set_status(tab_id, "slow", "extracting")
        await self._set_status(tab_id, "extract", "extracting")

        extract_message = self._image_user_message(EXTRACT_PROMPT, image_png)
        try:
            extracted_result = await self._stream_to_lane(
                tab_id,
                "extract",
                [extract_message],
                self.config.models.vlm,
                reasoning_title=EXTRACT_REASONING_TITLE,
                content_separator=EXTRACT_SEPARATOR,
            )
            extracted = extracted_result.answer_for_history
            if not extracted.strip():
                raise RuntimeError("VLM extraction returned empty text")
            await self._set_status(tab_id, "extract", "done")
        except Exception as exc:
            await self._set_status(tab_id, "extract", "error", f"\n题目提取失败：{exc}\n")
            await self._set_status(tab_id, "slow", "error", f"\n题目提取失败：{exc}\n")
            return

        await self._set_status(tab_id, "slow", "thinking")
        user_message = {
            "role": "user",
            "content": build_slow_user_prompt(extracted),
        }
        async with self._state_lock:
            messages = [
                {"role": "system", "content": SLOW_SYSTEM_PROMPT},
                *self.slow_history,
                user_message,
            ]

        try:
            result = await self._stream_to_lane(
                tab_id,
                "slow",
                messages,
                self.config.models.llm,
                reasoning_title=ANSWER_REASONING_TITLE,
                content_separator=ANSWER_SEPARATOR,
            )
            async with self._state_lock:
                self.slow_history.extend(
                    [
                        user_message,
                        {"role": "assistant", "content": result.answer_for_history},
                    ]
                )
                self.slow_history = self._trim_history(self.slow_history)
            await self._set_status(tab_id, "slow", "done")
        except Exception as exc:
            await self._set_status(tab_id, "slow", "error", f"\n慢路失败：{exc}\n")

    async def _stream_to_lane(
        self,
        tab_id: str,
        lane: Lane,
        messages: list[dict[str, Any]],
        model_config: Any,
        *,
        reasoning_title: str,
        content_separator: str,
    ) -> StreamResult:
        queue: asyncio.Queue[Any | Exception | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                for token in self.client.iter_chat_events(messages, model_config):
                    loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=worker, daemon=True).start()

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        saw_content = False
        saw_reasoning = False
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item

            if item.kind == "reasoning":
                if not saw_reasoning:
                    await self._append_token(tab_id, lane, reasoning_title)
                    saw_reasoning = True
                reasoning_parts.append(item.text)
                await self._append_token(tab_id, lane, item.text)
                continue

            if item.kind == "content":
                if saw_reasoning and not saw_content:
                    await self._append_token(tab_id, lane, content_separator)
                saw_content = True
                content_parts.append(item.text)
                await self._append_token(tab_id, lane, item.text)

        return StreamResult(
            content="".join(content_parts),
            reasoning="".join(reasoning_parts),
        )

    async def _append_token(self, tab_id: str, lane: Lane, text: str) -> None:
        async with self._state_lock:
            tab = self._find_tab(tab_id)
            if tab is None:
                return
            current = getattr(tab, lane)
            setattr(tab, lane, current + text)

        await self.hub.publish(
            "token",
            {
                "tab_id": tab_id,
                "lane": lane,
                "text": text,
            },
        )

    async def _set_status(
        self,
        tab_id: str,
        lane: Lane,
        status: str,
        message: str = "",
    ) -> None:
        async with self._state_lock:
            tab = self._find_tab(tab_id)
            if tab is None:
                return
            tab.statuses[lane] = status
            if message:
                current = getattr(tab, lane)
                setattr(tab, lane, current + message)

        await self.hub.publish(
            "status",
            {
                "tab_id": tab_id,
                "lane": lane,
                "status": status,
                "message": message,
            },
        )

    def _trim_history(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return history[-self.config.context.max_history_messages :]

    def _find_tab(self, tab_id: str) -> TabState | None:
        return next((tab for tab in self.tabs if tab.id == tab_id), None)

    def _image_user_message(self, prompt: str, image_png: bytes) -> dict[str, Any]:
        data_url = "data:image/png;base64," + base64.b64encode(image_png).decode("ascii")
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
