from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


class ConfigError(RuntimeError):
    """Raised when the local TOML configuration is invalid."""


@dataclass(frozen=True)
class ModelConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 120.0
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ModelsConfig:
    vlm: ModelConfig
    llm: ModelConfig


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "info"


@dataclass(frozen=True)
class HotkeyConfig:
    enabled: bool = True
    sequence: str = ""
    debounce_seconds: float = 0.8


@dataclass(frozen=True)
class ScreenshotConfig:
    monitor_index: int = 1


@dataclass(frozen=True)
class ContextConfig:
    max_history_messages: int = 16


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    hotkey: HotkeyConfig
    screenshot: ScreenshotConfig
    context: ContextConfig
    models: ModelsConfig
    config_path: Path


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    data: dict[str, Any] = {}

    if config_path.exists():
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)

    global_api = _table(data, "api")
    models = _table(data, "models")
    vlm_api = _table(data, "vlm_api")
    llm_api = _table(data, "llm_api")

    server = _table(data, "server")
    hotkey = _table(data, "hotkey")
    screenshot = _table(data, "screenshot")
    context = _table(data, "context")

    vlm = _model_config(
        vlm_api,
        legacy_table=_table(models, "vlm"),
        global_api=global_api,
        default_model="MiMo-V2.5",
        model_alias="vlm_model",
    )
    llm = _model_config(
        llm_api,
        legacy_table=_table(models, "llm"),
        global_api=global_api,
        default_model="MiMo-V2.5-Pro",
        model_alias="llm_model",
    )

    return AppConfig(
        server=ServerConfig(
            host=str(server.get("host", "127.0.0.1")),
            port=int(server.get("port", 8765)),
            log_level=str(server.get("log_level", "info")),
        ),
        hotkey=HotkeyConfig(
            enabled=bool(hotkey.get("enabled", True)),
            sequence=_required_str(hotkey, "sequence", "[hotkey].sequence"),
            debounce_seconds=float(hotkey.get("debounce_seconds", 0.8)),
        ),
        screenshot=ScreenshotConfig(
            monitor_index=int(screenshot.get("monitor_index", 1)),
        ),
        context=ContextConfig(
            max_history_messages=max(2, int(context.get("max_history_messages", 16))),
        ),
        models=ModelsConfig(vlm=vlm, llm=llm),
        config_path=config_path,
    )


def _model_config(
    table: dict[str, Any],
    *,
    legacy_table: dict[str, Any],
    global_api: dict[str, Any],
    default_model: str,
    model_alias: str,
) -> ModelConfig:
    merged = {**global_api, **legacy_table, **table}
    return ModelConfig(
        api_key=str(merged.get("api_key") or ""),
        base_url=str(merged.get("base_url") or ""),
        model=str(merged.get("model") or global_api.get(model_alias) or default_model),
        timeout_seconds=float(
            merged.get("timeout_seconds") or 120.0
        ),
        temperature=_optional_float(merged.get("temperature")),
        max_tokens=_optional_int(merged.get("max_tokens")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _required_str(table: dict[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if value is None or str(value).strip() == "":
        raise ConfigError(f"Missing required config: {label}")
    return str(value).strip()


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"`{key}` must be a TOML table")
    return value
