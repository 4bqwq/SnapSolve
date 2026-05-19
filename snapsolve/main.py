from __future__ import annotations

import argparse

import uvicorn

from .app import create_app
from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SnapSolve.")
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config TOML file. Defaults to config.toml.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    app = create_app(config)
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
    )


if __name__ == "__main__":
    main()
