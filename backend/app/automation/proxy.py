"""Centralized outbound IP and proxy management.

All IP routing, proxy parsing, and network origin logic lives in this single file:
- When CUSTOM_IP / PROXY_URL in .env is empty: uses host machine's own direct public IP.
- When CUSTOM_IP / PROXY_URL is set: automatically formats and routes Playwright traffic
  through the specified IP/proxy server.
"""

from __future__ import annotations

import base64
import select
import socket
import threading
from urllib.parse import urlparse

import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

_tunnel_lock = threading.Lock()
_active_tunnel_port: int | None = None
_tunnel_server_sock: socket.socket | None = None


def _start_preemptive_auth_tunnel(
    upstream_host: str,
    upstream_port: int,
    username: str,
    password: str,
) -> int:
    """Start an in-process local TCP forwarder on 127.0.0.1.

    Injects preemptive `Proxy-Authorization: Basic ...` on every CONNECT and HTTP
    request, preventing Chromium ERR_CONNECTION_RESET on proxy 407 challenges.
    """
    global _active_tunnel_port, _tunnel_server_sock

    with _tunnel_lock:
        if _active_tunnel_port is not None:
            return _active_tunnel_port

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(100)
        port = server.getsockname()[1]

        auth_b64 = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        auth_header_line = f"Proxy-Authorization: Basic {auth_b64}".encode()

        def _relay(s1: socket.socket, s2: socket.socket) -> None:
            try:
                while True:
                    r, _, _ = select.select([s1, s2], [], [], 30)
                    if not r:
                        break
                    for s in r:
                        data = s.recv(32768)
                        if not data:
                            return
                        if s is s1:
                            s2.sendall(data)
                        else:
                            s1.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    s1.close()
                except Exception:
                    pass
                try:
                    s2.close()
                except Exception:
                    pass

        def _handle_client(client_sock: socket.socket) -> None:
            try:
                initial_req = client_sock.recv(4096)
                if not initial_req:
                    client_sock.close()
                    return

                upstream = socket.create_connection((upstream_host, upstream_port), timeout=15)

                if initial_req.startswith(b"CONNECT"):
                    lines = initial_req.split(b"\r\n")
                    new_lines = [lines[0]]
                    for line in lines[1:]:
                        if not line:
                            break
                        if not line.lower().startswith(b"proxy-authorization"):
                            new_lines.append(line)
                    new_lines.append(auth_header_line)
                    new_lines.append(b"")
                    new_lines.append(b"")
                    upstream.sendall(b"\r\n".join(new_lines))

                    resp = upstream.recv(4096)
                    client_sock.sendall(resp)

                    if b"200" in resp:
                        _relay(client_sock, upstream)
                    else:
                        upstream.close()
                        client_sock.close()
                else:
                    # Non-CONNECT HTTP traffic
                    lines = initial_req.split(b"\r\n")
                    new_lines = [lines[0]]
                    for line in lines[1:]:
                        if not line:
                            break
                        if not line.lower().startswith(b"proxy-authorization"):
                            new_lines.append(line)
                    new_lines.append(auth_header_line)
                    new_lines.append(b"")
                    new_lines.append(b"")
                    upstream.sendall(b"\r\n".join(new_lines))
                    _relay(client_sock, upstream)
            except Exception:
                try:
                    client_sock.close()
                except Exception:
                    pass

        def _server_loop() -> None:
            while True:
                try:
                    client, _ = server.accept()
                    t = threading.Thread(target=_handle_client, args=(client,), daemon=True)
                    t.start()
                except Exception:
                    break

        th = threading.Thread(target=_server_loop, daemon=True, name="proxy-auth-tunnel")
        th.start()

        _active_tunnel_port = port
        _tunnel_server_sock = server
        log.info(
            "proxy.preemptive_tunnel_started",
            local_port=port,
            upstream_host=upstream_host,
            upstream_port=upstream_port,
        )
        return port


def parse_ip_or_proxy(raw: str) -> dict[str, str] | None:
    """Parse an IP address or proxy string into Playwright's expected proxy dictionary.

    Supports formats:
      - '192.168.1.50:8080' -> {'server': 'http://192.168.1.50:8080'}
      - '192.168.1.50:8080:user:pass' -> {'server': 'http://192.168.1.50:8080', 'username': 'user', 'password': 'pass'}
      - 'user:pass@192.168.1.50:8080' -> {'server': 'http://192.168.1.50:8080', 'username': 'user', 'password': 'pass'}
      - 'http://192.168.1.50:8080' -> {'server': 'http://192.168.1.50:8080'}
      - 'http://user:pass@192.168.1.50:8080' -> {'server': 'http://192.168.1.50:8080', 'username': 'user', 'password': 'pass'}
      - 'socks5://user:pass@192.168.1.50:1080' -> {'server': 'socks5://192.168.1.50:1080', 'username': 'user', 'password': 'pass'}
      - 'socks5://192.168.1.50:1080:user:pass' -> {'server': 'socks5://192.168.1.50:1080', 'username': 'user', 'password': 'pass'}
    """
    clean = (raw or "").strip().strip("\"'")
    if not clean:
        return None

    scheme = "http"
    if "://" in clean:
        scheme, clean = clean.split("://", 1)
        scheme = scheme.lower()

    if "@" not in clean and clean.count(":") == 3:
        parts = clean.split(":")
        ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
        return {
            "server": f"{scheme}://{ip}:{port}",
            "username": user,
            "password": pwd,
        }

    full_url = f"{scheme}://{clean}"
    try:
        parsed = urlparse(full_url)
    except Exception:
        log.warning("proxy.invalid_ip_or_proxy_format", raw=raw)
        return None

    if not parsed.hostname:
        log.warning("proxy.invalid_ip_or_proxy_format", raw=raw)
        return None

    try:
        port_part = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        log.warning("proxy.invalid_port", raw=raw)
        return None

    server = f"{scheme}://{parsed.hostname}{port_part}"

    proxy_dict: dict[str, str] = {"server": server}
    if parsed.username:
        proxy_dict["username"] = parsed.username
    if parsed.password:
        proxy_dict["password"] = parsed.password

    return proxy_dict


def get_playwright_proxy_config() -> dict[str, str] | None:
    """Return Playwright proxy dictionary, or None to use host's own direct public IP.

    If the proxy requires username/password authentication, an in-process local
    preemptive auth tunnel is used to prevent Chromium ERR_CONNECTION_RESET
    renegotiation failures on HTTPS CONNECT requests.
    """
    active_ip = settings.active_ip_or_proxy
    if not active_ip:
        return None

    config = parse_ip_or_proxy(active_ip)
    if not config:
        return None

    username = config.get("username")
    password = config.get("password")
    if username and password:
        parsed = urlparse(config["server"])
        upstream_host = parsed.hostname or "127.0.0.1"
        upstream_port = parsed.port or (1080 if "socks" in parsed.scheme else 8080)
        local_port = _start_preemptive_auth_tunnel(
            upstream_host=upstream_host,
            upstream_port=upstream_port,
            username=username,
            password=password,
        )
        return {"server": f"http://127.0.0.1:{local_port}"}

    return config


def log_network_ip_mode() -> None:
    """Log current network origin (Own Direct IP vs Custom Configured IP)."""
    active_ip = settings.active_ip_or_proxy
    if not active_ip:
        log.info("network.mode", status="Using Host Machine's Own Direct IP (No Proxy)")
        return

    config = parse_ip_or_proxy(active_ip)
    if config:
        server = config.get("server", "")
        has_auth = "username" in config
        log.info("network.mode", status="Using Configured Custom IP / Proxy", server=server, authenticated=has_auth)
    else:
        log.warning("network.mode", status="Custom IP configured but invalid; falling back to Host Own IP")
