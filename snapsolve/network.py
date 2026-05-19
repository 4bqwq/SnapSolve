from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket

from .config import ServerConfig


WILDCARD_HOSTS = {"0.0.0.0", "::", ""}


@dataclass(frozen=True)
class AccessInfo:
    listen_host: str
    port: int
    local_url: str
    lan_urls: list[str]
    lan_enabled: bool


def build_access_info(server: ServerConfig) -> AccessInfo:
    listen_host = server.host
    port = server.port
    local_url = f"http://127.0.0.1:{port}/"

    lan_urls: list[str] = []
    if listen_host in WILDCARD_HOSTS:
        lan_urls = [f"http://{address}:{port}/" for address in lan_ipv4_addresses()]
    elif _is_lan_host(listen_host):
        lan_urls = [f"http://{listen_host}:{port}/"]

    return AccessInfo(
        listen_host=listen_host,
        port=port,
        local_url=local_url,
        lan_urls=lan_urls,
        lan_enabled=bool(lan_urls),
    )


def print_access_info(server: ServerConfig) -> None:
    info = build_access_info(server)
    print("SnapSolve access URLs:")
    print(f"  Local: {info.local_url}")
    if info.lan_urls:
        for url in info.lan_urls:
            print(f"  LAN:   {url}")
    else:
        print("  LAN:   disabled; start with --lan to listen on the local network")


def lan_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()

    try:
        hostname = socket.gethostname()
        for address in socket.gethostbyname_ex(hostname)[2]:
            if _is_lan_host(address):
                addresses.add(address)
    except OSError:
        pass

    for probe_host in ("8.8.8.8", "1.1.1.1"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((probe_host, 80))
                address = sock.getsockname()[0]
                if _is_lan_host(address):
                    addresses.add(address)
        except OSError:
            pass

    return sorted(addresses, key=_ipv4_sort_key)


def _is_lan_host(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host not in {"localhost"} and not host.startswith("127.")
    return address.version == 4 and not address.is_loopback and not address.is_unspecified


def _ipv4_sort_key(address: str) -> tuple[int, int, int, int]:
    return tuple(int(part) for part in address.split("."))  # type: ignore[return-value]
