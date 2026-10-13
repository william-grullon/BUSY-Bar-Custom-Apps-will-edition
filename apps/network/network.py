#!/usr/bin/env python3
"""Network for BUSY Bar release firmware.

Uploads a static UP/DOWN label image, then shows this computer's live
download/upload speeds next to it. Official release firmware only.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import time
from pathlib import Path

import psutil
import requests

APP_NAME = "network"
DEFAULT_HOST = "10.0.4.20"
DEFAULT_REFRESH = 0.25
MEASURE_SECONDS = 0.1
API_VERSION_HEADER = "X-Busy-Api-Version"
DRAW_PRIORITY = 50
APP_DIR = Path(__file__).resolve().parent
LABELS_PNG = APP_DIR / "Speed_down-up.png"
DEVICE_LABEL_NAME = "speed_labels.png"


def load_dotenv() -> None:
    """Load simple KEY=VALUE settings without requiring another dependency."""
    config_path = APP_DIR / ".env"
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
    """Store BUSYBAR_IP in .env so the new address is used next time."""
    config_path = APP_DIR / ".env"
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

    def upload_asset(self, path: Path, remote_name: str) -> None:
        response = self.session.post(
            f"{self.api}/assets/upload",
            params={
                "application_name": APP_NAME,
                "file": remote_name,
            },
            data=path.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
            timeout=15,
        )
        response.raise_for_status()

    def draw_labels(self, remote_name: str) -> None:
        response = self.session.post(
            f"{self.api}/display/draw",
            json={
                "application_name": APP_NAME,
                "priority": DRAW_PRIORITY,
                "elements": [
                    {
                        "id": "labels_img",
                        "type": "image",
                        "path": remote_name,
                        "x": 0,
                        "y": 0,
                        "display": "front",
                        "opacity": 100,
                        "timeout": 0,
                    }
                ],
            },
            timeout=5,
        )
        response.raise_for_status()

    def draw_speeds(self, down_mbps: int, up_mbps: int, display_timeout: int) -> None:
        response = self.session.post(
            f"{self.api}/display/draw",
            json={
                "application_name": APP_NAME,
                "priority": DRAW_PRIORITY,
                "elements": [
                    {
                        "id": "down_speed",
                        "type": "text",
                        "text": f"{down_mbps} Mb/s",
                        "x": 71,
                        "y": -1,
                        "align": "top_right",
                        "font": "small",
                        "color": "#FFFFFFFF",
                        "display": "front",
                        "timeout": display_timeout,
                    },
                    {
                        "id": "up_speed",
                        "type": "text",
                        "text": f"{up_mbps} Mb/s",
                        "x": 71,
                        "y": 7,
                        "align": "top_right",
                        "font": "small",
                        "color": "#FFFFFFFF",
                        "display": "front",
                        "timeout": display_timeout,
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
        description="Show live network speeds on a BUSY Bar with UP/DOWN labels."
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
        help="How long speed text stays on screen before refresh (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh_interval <= 0:
        raise SystemExit("--refresh-interval must be greater than 0")
    if not LABELS_PNG.is_file():
        raise SystemExit(f"Label image not found: {LABELS_PNG}")

    interface = pick_interface(args.interface)

    host = args.host
    while True:
        bar = BusyBarClient(host, args.password)
        try:
            version = bar.connect()
            prepare_access(bar)
            print("Uploading label artwork…")
            bar.upload_asset(LABELS_PNG, DEVICE_LABEL_NAME)
            bar.draw_labels(DEVICE_LABEL_NAME)
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
    print("Press Ctrl+C to stop.")

    try:
        while True:
            down_mbps, up_mbps = measure_speeds(interface, MEASURE_SECONDS)
            print(
                f"DOWN {down_mbps} Mb/s  |  UP {up_mbps} Mb/s    ",
                end="\r",
                flush=True,
            )
            try:
                bar.draw_speeds(down_mbps, up_mbps, args.display_timeout)
            except requests.HTTPError as error:
                if error.response is not None and error.response.status_code in (
                    401,
                    403,
                ):
                    raise SystemExit(
                        "The BUSY Bar rejected the Wi-Fi access password. "
                        "Check the HTTP API settings and try again."
                    ) from error
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
