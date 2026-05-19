from __future__ import annotations

import argparse
from dataclasses import replace

import uvicorn

from .app import create_app
from .config import load_config
from .network import print_access_info


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SnapSolve.")
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config TOML file. Defaults to config.toml.",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Listen on 0.0.0.0 so other computers on the same LAN can open the page.",
    )
    parser.add_argument(
        "--host",
        help="Override the configured listen host.",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override the configured listen port.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    server = config.server
    if args.lan:
        server = replace(server, host="0.0.0.0")
    if args.host:
        server = replace(server, host=args.host)
    if args.port is not None:
        server = replace(server, port=args.port)
    config = replace(config, server=server)

    print_access_info(config.server)
    app = create_app(config)
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
    )


if __name__ == "__main__":
    main()
