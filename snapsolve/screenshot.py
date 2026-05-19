from __future__ import annotations

from dataclasses import dataclass

import mss
from mss import tools


@dataclass(frozen=True)
class Screenshot:
    png: bytes
    monitor_index: int
    width: int
    height: int


class Screenshotter:
    def capture_png(self, monitor_index: int) -> Screenshot:
        with mss.mss() as sct:
            index = self._resolve_monitor_index(sct.monitors, monitor_index)
            monitor = sct.monitors[index]
            shot = sct.grab(monitor)
            png = tools.to_png(shot.rgb, shot.size)
            return Screenshot(
                png=png,
                monitor_index=index,
                width=shot.width,
                height=shot.height,
            )

    def _resolve_monitor_index(self, monitors: list[dict[str, int]], preferred: int) -> int:
        if preferred > 0 and preferred < len(monitors):
            return preferred
        if len(monitors) > 1:
            return 1
        return 0
