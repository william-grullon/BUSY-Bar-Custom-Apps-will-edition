#!/usr/bin/env python3
"""Ping Monitor for BUSY Bar release firmware."""

from __future__ import annotations

import argparse
import getpass
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

APP_NAME = "ping_monitor"
DEFAULT_HOST = "10.0.4.20"
DEFAULT_TARGET = "1.1.1.1"
DEFAULT_INTERVAL = 60.0
DEFAULT_TIMEOUT = 5.0
API_VERSION_HEADER = "X-Busy-Api-Version"
DRAW_PRIORITY = 50

LATENCY_RE = re.compile(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)


def load_dotenv() -> None:
    """Load simple KEY=VALUE settings without requiring another dependency."""
    config_path = Path(__file__).resolve().parent / ".env"
    if not config_path.is_file():
        return
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


class BusyBarClient:
    def __init__(self, host: str, password: str | None = None) -> None:
        clean_host = (
            host.strip()
            .replace("http://", "")
            .replace("https://", "")
            .rstrip("/")
        )
        self.host = clean_host
        self.api = f"http://{clean_host}/api"
        self.session = requests.Session()
        if password:
            self.set_password(password)

    def set_password(self, password: str) -> None:
        self.session.headers["X-API-Token"] = password

    @property
    def has_password(self) -> bool:
        return bool(self.session.headers.get("X-API-Token"))

    def connect(self) -> str:
        response = self.session.get(f"{self.api}/version", timeout=5)
        response.raise_for_status()
        version = str(response.json().get("api_semver") or "0.1.0")
        self.session.headers[API_VERSION_HEADER] = version
        return version

    def access_mode(self) -> str:
        response = self.session.get(f"{self.api}/access", timeout=5)
        response.raise_for_status()
        return str(response.json().get("mode") or "").lower()

    def transport_type(self) -> str:
        response = self.session.get(f"{self.api}/transport", timeout=5)
        response.raise_for_status()
        return str(response.json().get("type") or "").lower()

    def draw(self, label: str, value: str, color: str) -> None:
        response = self.session.post(
            f"{self.api}/display/draw",
            json={
                "application_name": APP_NAME,
                "priority": DRAW_PRIORITY,
                "elements": [
                    {
                        "id": "ping_label",
                        "type": "text",
                        "text": label,
                        "x": 1,
                        "y": 0,
                        "font": "small",
                        "color": "#FFFFFFFF",
                        "display": "front",
                        "timeout": 0,
                    },
                    {
                        "id": "ping_value",
                        "type": "text",
                        "text": value,
                        "x": 71,
                        "y": 5,
                        "align": "top_right",
                        "font": "condensed",
                        "color": color,
                        "display": "front",
                        "timeout": 0,
                    },
                ],
            },
            timeout=5,
        )
        response.raise_for_status()

    def clear(self) -> None:
        response = self.session.delete(
            f"{self.api}/display/draw",
            params={"application_name": APP_NAME},
            timeout=5,
        )
        response.raise_for_status()


def prepare_access(bar: BusyBarClient) -> None:
    if bar.transport_type() != "wifi":
        return

    mode = bar.access_mode()
    if mode == "disabled":
        raise PermissionError(
            "Wi-Fi access to the BUSY Bar HTTP API is disabled. "
            "Enable HTTP API access on the BUSY Bar."
        )
    if mode == "key" and not bar.has_password:
        if not sys.stdin.isatty():
            raise PermissionError(
                "This BUSY Bar requires its Wi-Fi access password. "
                "Set BUSYBAR_PASSWORD or run the app in a terminal."
            )
        password = getpass.getpass("BUSY Bar Wi-Fi access password: ").strip()
        if not password:
            raise PermissionError("The Wi-Fi access password is required.")
        bar.set_password(password)


def ping(target: str, timeout: float) -> float | None:
    """Return round-trip milliseconds, or None when the target is unreachable."""
    timeout_ms = max(1, int(timeout * 1000))
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout_ms), target]
    elif platform.system().lower() == "darwin":
        command = ["ping", "-c", "1", "-W", str(timeout_ms), target]
    else:
        command = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), target]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    match = LATENCY_RE.search(result.stdout + result.stderr)
    if result.returncode != 0 or not match:
        return None
    return float(match.group(1))


def color_for_latency(latency: float | None) -> str:
    if latency is None:
        return "#FF4040FF"
    if latency <= 50:
        return "#40FF80FF"
    if latency <= 100:
        return "#FFFF40FF"
    return "#FF4040FF"


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Show current connection latency on a BUSY Bar."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BUSYBAR_IP", DEFAULT_HOST),
        help=f"BUSY Bar IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("PING_TARGET", DEFAULT_TARGET),
        help=f"Host or IP address to ping (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("PING_INTERVAL", DEFAULT_INTERVAL)),
        help="Seconds between checks (default: 60)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("PING_TIMEOUT", DEFAULT_TIMEOUT)),
        help="Seconds to wait for each ping (default: 5)",
    )
    parser.add_argument(
        "--password",
        default=(
            os.environ.get("BUSYBAR_PASSWORD")
            or os.environ.get("BUSYBAR_TOKEN")
            or os.environ.get("BUSYBAR_API_KEY")
        ),
        help="Optional Wi-Fi access password; interactive runs prompt when needed",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.interval <= 0 or args.timeout <= 0:
        raise SystemExit("--interval and --timeout must be greater than 0")

    bar = BusyBarClient(args.host, args.password)
    try:
        version = bar.connect()
        prepare_access(bar)
    except PermissionError as error:
        raise SystemExit(str(error)) from error
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code in (401, 403):
            raise SystemExit(
                "The BUSY Bar rejected the Wi-Fi access password. "
                "Check the HTTP API settings and try again."
            ) from error
        raise SystemExit(f"BUSY Bar request failed: {error}") from error
    except requests.RequestException as error:
        raise SystemExit(
            f"Could not connect to BUSY Bar at {args.host}: {error}"
        ) from error

    print(f"Connected to BUSY Bar at {bar.host} (API {version})")
    print(f"Pinging {args.target} every {args.interval:g} seconds.")
    print("Press Ctrl+C to stop.")

    try:
        next_check = time.monotonic()
        while True:
            latency = ping(args.target, args.timeout)
            if latency is None:
                label, value = "PING", "OFFLINE"
                print(f"{args.target}: offline")
            else:
                rounded_latency = round(latency)
                label, value = "PING", f"{rounded_latency}ms"
                print(f"{args.target}: {rounded_latency} ms")
            try:
                bar.draw(label, value, color_for_latency(latency))
            except requests.RequestException as error:
                print(f"Display update failed: {error}")
                break

            next_check += args.interval
            wait_for = max(0, next_check - time.monotonic())
            time.sleep(wait_for)
    except KeyboardInterrupt:
        print("\nStopping Ping Monitor…")
    finally:
        try:
            bar.clear()
        except requests.RequestException:
            pass
        print("Cleared display.")


if __name__ == "__main__":
    main()
