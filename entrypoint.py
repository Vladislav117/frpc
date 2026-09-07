#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CONFIGURATION_FILE_PATH: Path = Path("/app/frpc.json")
GENERATED_CONFIGURATION_FILE_PATH: Path = Path("/tmp/frpc.toml")
ENV_PATTERN: re.Pattern[str] = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def fail(message: str) -> None:
    print(f"[frpc] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"config not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail("top-level config must be a JSON object")
    return value


def expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in os.environ:
                fail(f"environment variable {name} is not set")
            return os.environ[name]

        return ENV_PATTERN.sub(replace, value)

    if isinstance(value, list):
        return [expand_env(item) for item in value]

    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}

    return value


def require(mapping: dict[str, Any], field: str, context: str) -> Any:
    if field not in mapping:
        fail(f"{context}.{field} is required")
    return mapping[field]


def parse_address(value: str, context: str) -> tuple[str, int]:
    if not isinstance(value, str) or not value.strip():
        fail(f"{context} must be a non-empty string")

    parsed = urlsplit(f"//{value}")
    try:
        port = parsed.port
    except ValueError:
        fail(f"{context} must have form host:port, got {value!r}")

    if not parsed.hostname or port is None:
        fail(f"{context} must have form host:port, got {value!r}")
    if not 1 <= port <= 65535:
        fail(f"{context} port must be between 1 and 65535")

    return parsed.hostname, port


def validate_port(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        fail(f"{context} must be an integer")
    if not 1 <= value <= 65535:
        fail(f"{context} must be between 1 and 65535")
    return value


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_frpc_config(config: dict[str, Any]) -> str:
    frp = config.get("frp")
    if not isinstance(frp, dict):
        fail("frp must be an object")

    server_host, server_port = parse_address(require(frp, "server", "frp"), "frp.server")
    token = require(frp, "token", "frp")
    if not isinstance(token, str) or not token:
        fail("frp.token must be a non-empty string")

    routes = config.get("routes")
    if not isinstance(routes, list) or not routes:
        fail("routes must be a non-empty array")

    lines = [f"serverAddr = {toml_string(server_host)}", f"serverPort = {server_port}", "auth.method = \"token\"", f"auth.token = {toml_string(token)}"]
    for index, route in enumerate(routes):
        context = f"routes[{index}]"
        if not isinstance(route, dict):
            fail(f"{context} must be an object")

        route_type = require(route, "type", context)
        if not isinstance(route_type, str):
            fail(f"{context}.type must be a string")
        route_type = route_type.lower()
        if route_type not in {"tcp", "udp", "http"}:
            fail(f"{context}.type must be TCP, UDP or HTTP")

        host, local_port = parse_address(require(route, "target", context), f"{context}.target")
        name = str(uuid.uuid4())

        lines.extend(["", "[[proxies]]", f"name = {toml_string(name)}", f"type = {toml_string(route_type)}", f"localIP = {toml_string(host)}", f"localPort = {local_port}"])

        if route_type in {"tcp", "udp"}:
            remote_port = validate_port(require(route, "port", context), f"{context}.port")
            lines.append(f"remotePort = {remote_port}")
        else:
            domains = require(route, "domains", context)
            if not isinstance(domains, list) or not domains or any(
                    not isinstance(domain, str) or not domain.strip() for domain in domains):
                fail(f"{context}.domains must be a non-empty array of strings")
            values = ", ".join(toml_string(domain) for domain in domains)
            lines.append(f"customDomains = [{values}]")

    return "\n".join(lines) + "\n"


def main() -> None:
    config = expand_env(load_json(CONFIGURATION_FILE_PATH))
    generated = build_frpc_config(config)
    GENERATED_CONFIGURATION_FILE_PATH.write_text(generated, encoding="utf-8")

    print(f"[frpc] config: {CONFIGURATION_FILE_PATH}")

    verify = subprocess.run(["frpc", "verify", "-c", str(GENERATED_CONFIGURATION_FILE_PATH)], check=False)
    if verify.returncode != 0:
        fail("generated FRP config did not pass 'frpc verify'")

    os.execvp("frpc", ["frpc", "-c", str(GENERATED_CONFIGURATION_FILE_PATH)])


if __name__ == "__main__":
    main()
