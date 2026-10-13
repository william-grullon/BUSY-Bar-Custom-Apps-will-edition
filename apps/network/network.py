#!/usr/bin/env python3
"""Network for BUSY Bar release firmware.

Shows this computer's live download/upload speeds and the latency to a ping
target on one screen. Official release firmware only.
"""

from __future__ import annotations

import argparse
import getpass
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import requests

APP_NAME = "network"
DEFAULT_HOST = "10.0.4.20"
DEFAULT_REFRESH = 0.25
MEASURE_SECONDS = 0.1
DEFAULT_TARGET = "1.1.1.1"
DEFAULT_PING_INTERVAL = 10.0
DEFAULT_PING_TIMEOUT = 5.0
API_VERSION_HEADER = "X-Busy-Api-Version"
DRAW_PRIORITY = 50
WHITE = "#FFFFFFFF"
# The 72px front display splits 54px (75%) speeds / 18px (25%) ping.
PING_CENTER_X = 63

LATENCY_RE = re.compile(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)

APP_DIR = Path(__file__).resolve().parent
SHARED_ENV = APP_DIR.parent.parent / ".env"


def load_dotenv() -> None:
    """Load simple KEY=VALUE settings from .env files without extra dependencies.

    The shared .env in the repository root is read first, so its settings
    (such as BUSYBAR_IP) apply to every app and win over this app's own .env.
    """
    for config_path in (SHARED_ENV, APP_DIR / ".env"):
        if not config_path.is_file():
            continue
        for raw_line in config_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            # Blank values (like an empty BUSYBAR_PASSWORD) count as unset.
            if key and value:
                os.environ.setdefault(key, value)


def ask_for_new_host(host: str, error: Exception) -> str | None:
    """Offer to enter a new BUSY Bar IP after a failed connection.

    Returns the new host, or None when the user declines or no terminal is attached.
    """
    print(f"Could not connect to BUSY Bar at {host}: {error}")
    if not sys.stdin.isatty():
        return None
    print("\nIf your BUSY Bar has a new IP address (for example after joining a different Wi-Fi),")
    print("enter it below. Check the bar's network settings or your router's device list.")
    try:
        new_host = input("New BUSY Bar IP (press Enter to quit): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    return new_host or None


def save_host(host: str) -> None:
    """Store BUSYBAR_IP in the shared .env so every app uses the new address."""
    config_path = SHARED_ENV
    lines: list[str] = []
    if config_path.is_file():
        lines = config_path.read_text(encoding="utf-8").splitlines()
    elif config_path.with_name(".env.example").is_file():
        lines = config_path.with_name(".env.example").read_text(encoding="utf-8").splitlines()

    for i, line in enumerate(lines):
        if line.strip().split("=", 1)[0].strip() == "BUSYBAR_IP":
            lines[i] = f"BUSYBAR_IP={host}"
            break
    else:
        lines.append(f"BUSYBAR_IP={host}")

    try:
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"Could not save the new IP to {config_path}: {error}")
        return
    print(f"Saved BUSYBAR_IP={host} to {config_path}")


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

    def draw(
        self,
        down_mbps: int,
        up_mbps: int,
        ping_value: str,
        ping_color: str,
        display_timeout: int,
    ) -> None:
        def text(element_id: str, value: str, x: int, y: int, align: str, color: str) -> dict:
            return {
                "id": element_id,
                "type": "text",
                "text": value,
                "x": x,
                "y": y,
                "align": align,
                "font": "small",
                "color": color,
                "display": "front",
                "timeout": display_timeout,
            }

        # Speeds fill the left 75% of the screen; ping is centered in the right 25%.
        response = self.session.post(
            f"{self.api}/display/draw",
            json={
                "application_name": APP_NAME,
                "priority": DRAW_PRIORITY,
                "elements": [
                    text("down_speed", f"D {down_mbps} Mb/s", 0, -1, "top_left", WHITE),
                    text("up_speed", f"U {up_mbps} Mb/s", 0, 7, "top_left", WHITE),
                    text("ping_label", "PING", PING_CENTER_X, -1, "top_mid", WHITE),
                    text("ping_value", ping_value, PING_CENTER_X, 7, "top_mid", ping_color),
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


def list_interfaces() -> list[str]:
    try:
        return list(psutil.net_io_counters(pernic=True).keys())
    except Exception:
        return []


def is_usable_interface(name: str) -> bool:
    lowered = name.lower()
    if lowered.startswith("lo"):
        return False
    blocked = ("loopback", "awdl", "llw", "utun", "bridge", "veth", "docker")
    return not any(part in lowered for part in blocked)


def pick_interface(preferred: str | None) -> str:
    counters = psutil.net_io_counters(pernic=True)
    if preferred and preferred != "auto":
        if preferred not in counters:
            available = ", ".join(list_interfaces()) or "(none)"
            raise SystemExit(
                f"Network interface '{preferred}' was not found.\n"
                f"Available interfaces: {available}"
            )
        return preferred

    candidates = [name for name in counters if is_usable_interface(name)]
    if not candidates:
        raise SystemExit("No usable network interface was found.")

    # Prefer the interface that has already moved the most traffic.
    ranked = sorted(
        candidates,
        key=lambda name: counters[name].bytes_recv + counters[name].bytes_sent,
        reverse=True,
    )
    return ranked[0]


def measure_speeds(interface: str, interval: float) -> tuple[int, int]:
    first = psutil.net_io_counters(pernic=True)[interface]
    time.sleep(interval)
    second = psutil.net_io_counters(pernic=True)[interface]

    down_mbps = (second.bytes_recv - first.bytes_recv) * 8 / 1_000_000 / interval
    up_mbps = (second.bytes_sent - first.bytes_sent) * 8 / 1_000_000 / interval
    return max(int(down_mbps), 0), max(int(up_mbps), 0)


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


class PingWorker(threading.Thread):
    """Pings the target in the background so speed updates never wait on it."""

    def __init__(self, target: str, interval: float, timeout: float) -> None:
        super().__init__(daemon=True)
        self.target = target
        self.interval = interval
        self.timeout = timeout
        self.checked = False
        self.latency: float | None = None

    def run(self) -> None:
        next_check = time.monotonic()
        while True:
            self.latency = ping(self.target, self.timeout)
            self.checked = True
            next_check += self.interval
            time.sleep(max(0, next_check - time.monotonic()))

    def display(self) -> tuple[str, str, str]:
        """Return (display text, color, terminal text) for the latest result."""
        if not self.checked:
            return "...", WHITE, "..."
        latency = self.latency
        if latency is None:
            return "OFF", color_for_latency(None), "offline"
        # Milliseconds without the unit, so it fits the narrow ping column.
        return str(round(latency)), color_for_latency(latency), f"{round(latency)} ms"


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


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Show live network speeds and ping latency on a BUSY Bar."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BUSYBAR_IP", DEFAULT_HOST),
        help=f"BUSY Bar IP address (default: {DEFAULT_HOST})",
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
    parser.add_argument(
        "--token",
        dest="password",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interface",
        default=os.environ.get("NETWORK_INTERFACE", "auto"),
        help="Network interface to monitor (default: auto)",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=float(os.environ.get("NETWORK_REFRESH_INTERVAL", DEFAULT_REFRESH)),
        help=f"Seconds between display updates (default: {DEFAULT_REFRESH})",
    )
    parser.add_argument(
        "--display-timeout",
        type=int,
        default=int(os.environ.get("NETWORK_DISPLAY_TIMEOUT", 1)),
        help="How long text stays on screen before refresh (default: 1)",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("PING_TARGET", DEFAULT_TARGET),
        help=f"Host or IP address to ping (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--ping-interval",
        type=float,
        default=float(os.environ.get("PING_INTERVAL", DEFAULT_PING_INTERVAL)),
        help=f"Seconds between pings (default: {DEFAULT_PING_INTERVAL:g})",
    )
    parser.add_argument(
        "--ping-timeout",
        type=float,
        default=float(os.environ.get("PING_TIMEOUT", DEFAULT_PING_TIMEOUT)),
        help=f"Seconds to wait for each ping (default: {DEFAULT_PING_TIMEOUT:g})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh_interval <= 0:
        raise SystemExit("--refresh-interval must be greater than 0")
    if args.ping_interval <= 0 or args.ping_timeout <= 0:
        raise SystemExit("--ping-interval and --ping-timeout must be greater than 0")

    interface = pick_interface(args.interface)

    host = args.host
    while True:
        bar = BusyBarClient(host, args.password)
        try:
            version = bar.connect()
            prepare_access(bar)
            break
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
            new_host = ask_for_new_host(host, error)
            if new_host is None:
                raise SystemExit(1) from error
            host = new_host
            print()

    if host != args.host:
        save_host(host)
    print(f"Connected to BUSY Bar at {bar.host} (API {version})")
    print(f"Monitoring interface '{interface}'.")
    print(f"Pinging {args.target} every {args.ping_interval:g} seconds.")
    print("Press Ctrl+C to stop.")

    pinger = PingWorker(args.target, args.ping_interval, args.ping_timeout)
    pinger.start()

    try:
        display_confirmed = False
        while True:
            down_mbps, up_mbps = measure_speeds(interface, MEASURE_SECONDS)
            ping_value, ping_color, ping_text = pinger.display()
            print(
                f"DOWN {down_mbps} Mb/s  |  UP {up_mbps} Mb/s  |  PING {ping_text}    ",
                end="\r",
                flush=True,
            )
            try:
                bar.draw(down_mbps, up_mbps, ping_value, ping_color, args.display_timeout)
                if not display_confirmed:
                    print("\nNetwork is working; the result is on the BUSY Bar.")
                    display_confirmed = True
            except requests.HTTPError as error:
                status = error.response.status_code if error.response is not None else None
                if status in (401, 403):
                    raise SystemExit(
                        "The BUSY Bar rejected the Wi-Fi access password. "
                        "Check the HTTP API settings and try again."
                    ) from error
                if status == 409:
                    print(
                        "\nBUSY Bar display is busy. Stop the other app "
                        "with Ctrl+C, Back, or the mode switch; retrying "
                        "in 10 seconds."
                    )
                    time.sleep(10)
                    continue
                print(f"\nDisplay update failed: {error}")
                break
            except requests.RequestException as error:
                print(f"\nDisplay update failed: {error}")
                break
            time.sleep(args.refresh_interval)
    except KeyboardInterrupt:
        print("\nStopping Network…")
    finally:
        try:
            bar.clear()
        except requests.RequestException:
            pass
        print("Cleared display.")


if __name__ == "__main__":
    main()
