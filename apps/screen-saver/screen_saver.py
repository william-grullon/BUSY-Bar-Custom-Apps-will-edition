#!/usr/bin/env python3
"""Screen Saver for BUSY Bar release firmware.

Displays various scenes from a local folder, cycling through them on a timer
or on hardware dial turns, with support for static images, animated sequences,
and pause/resume on button press.
"""

from __future__ import annotations

import argparse
import getpass
import os
import random
import re
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageEnhance
from websocket import WebSocketTimeoutException, create_connection

APP_ID = "screen_saver"
DEFAULT_HOST = "10.0.4.20"
DEFAULT_INTERVAL = 10.0
DEFAULT_FPS = 4.0
DRAW_PRIORITY = 60
API_VERSION_HEADER = "X-Busy-Api-Version"
WIDTH = 72
HEIGHT = 16

BTN_OK, BTN_BACK, BTN_START = 0, 1, 2
ACT_RELEASE = 1

APP_DIR = Path(__file__).resolve().parent
DEFAULT_SCENES_DIR = APP_DIR / "scenes"
CACHE_DIR = APP_DIR / ".cache"


def load_dotenv() -> None:
    """Load simple KEY=VALUE settings from .env without extra dependencies."""
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


class BusyBarClient:
    """HTTP client for BUSY Bar release firmware."""

    def __init__(self, host: str, app_id: str = APP_ID, password: str | None = None) -> None:
        clean_host = (
            host.strip()
            .replace("http://", "")
            .replace("https://", "")
            .rstrip("/")
        )
        self.host = clean_host
        self.api = f"http://{clean_host}/api"
        self.app_id = app_id
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

    @property
    def ws_url(self) -> str:
        url = f"ws://{self.host}/api/status/ws"
        password = self.session.headers.get("X-API-Token")
        if password:
            url += f"?x-api-token={password}"
        return url

    def upload_asset(self, path: Path, remote_name: str | None = None) -> None:
        response = self.session.post(
            f"{self.api}/assets/upload",
            params={
                "application_name": self.app_id,
                "file": remote_name or path.name,
            },
            data=path.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
            timeout=15,
        )
        response.raise_for_status()

    def draw_image(self, filename: str) -> None:
        response = self.session.post(
            f"{self.api}/display/draw",
            json={
                "application_name": self.app_id,
                "priority": DRAW_PRIORITY,
                "elements": [
                    {
                        "id": "screensaver_scene",
                        "type": "image",
                        "path": filename,
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

    def clear(self) -> None:
        try:
            response = self.session.delete(
                f"{self.api}/display/draw",
                params={"application_name": self.app_id},
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException:
            pass

    def delete_assets(self) -> None:
        try:
            response = self.session.delete(
                f"{self.api}/assets/upload",
                params={"application_name": self.app_id},
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException:
            pass


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


# ============================================================================
# Protobuf Status / Hardware Input Decoding
# ============================================================================

def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 70:
            break
    raise ValueError("Invalid protobuf varint")


def _fields(data: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    offset = 0
    while offset < len(data):
        key, offset = _read_varint(data, offset)
        number, wire_type = key >> 3, key & 7
        if wire_type == 0:
            value, offset = _read_varint(data, offset)
        elif wire_type == 1:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            length, offset = _read_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == 5:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")
        yield number, wire_type, value


def _zigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def _input_event(data: bytes) -> tuple | None:
    for number, wire_type, value in _fields(data):
        if wire_type != 2 or not isinstance(value, bytes):
            continue
        if number == 1:
            button = action = 0
            for field, _, item in _fields(value):
                if field == 1 and isinstance(item, int):
                    button = item
                elif field == 2 and isinstance(item, int):
                    action = item
            return "button", button, action
        if number == 2:
            position = 0
            for field, _, item in _fields(value):
                if field == 1 and isinstance(item, int):
                    position = item
            return "switch", position
        if number == 3:
            delta = 0
            for field, _, item in _fields(value):
                if field == 1 and isinstance(item, int):
                    delta = _zigzag(item)
            return "encoder", delta
    return None


def events_from_state(data: bytes) -> Iterator[tuple]:
    for number, wire_type, update in _fields(data):
        if number != 2 or wire_type != 2 or not isinstance(update, bytes):
            continue
        for field, update_wire_type, value in _fields(update):
            if field == 11 and update_wire_type == 2 and isinstance(value, bytes):
                event = _input_event(value)
                if event:
                    yield event


# ============================================================================
# Scene Models & Smart Image Normalization
# ============================================================================

@dataclass
class Scene:
    name: str
    is_animated: bool
    frames: list[tuple[Path, str]]  # list of (local_path, remote_filename)


def normalize_image_to_72x16(src: Path, dst: Path) -> Path:
    """Normalize any image to 72x16 RGB PNG with center-crop and contrast pop."""
    with Image.open(src) as orig:
        if orig.size == (WIDTH, HEIGHT) and src.suffix.lower() == ".png":
            return src
        img = orig.convert("RGBA")

    w, h = img.size
    scale = max(WIDTH / w, HEIGHT / h)
    nw, nh = max(WIDTH, int(w * scale)), max(HEIGHT, int(h * scale))
    scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - WIDTH) // 2
    top = (nh - HEIGHT) // 2
    cropped = scaled.crop((left, top, left + WIDTH, top + HEIGHT))

    rgb = cropped.convert("RGB")
    enh = ImageEnhance.Contrast(rgb).enhance(1.15)
    final_img = ImageEnhance.Color(enh).enhance(1.2).convert("RGBA")

    dst.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(dst, format="PNG")
    return dst


def load_scenes(scenes_dir: Path) -> list[Scene]:
    """Discover all static and animated scenes from scenes directory."""
    if not scenes_dir.is_dir():
        return []

    scenes: list[Scene] = []
    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    items = sorted(scenes_dir.iterdir(), key=lambda p: p.name.lower())

    # First pass: load all animated directories
    for item in items:
        if item.is_dir() and not item.name.startswith("."):
            frame_files = sorted(
                [f for f in item.iterdir() if f.suffix.lower() in valid_exts],
                key=lambda f: f.name.lower(),
            )
            if frame_files:
                norm_frames: list[tuple[Path, str]] = []
                for idx, ff in enumerate(frame_files):
                    cache_frame = CACHE_DIR / f"{item.name}_{idx:03d}.png"
                    norm_path = normalize_image_to_72x16(ff, cache_frame)
                    remote_name = f"sc_{_sanitize_name(item.name)}_{idx:03d}.png"
                    norm_frames.append((norm_path, remote_name))
                scenes.append(Scene(name=item.name, is_animated=True, frames=norm_frames))

    seen_names = {s.name for s in scenes}

    # Second pass: load standalone image files and GIFs not already loaded as folders
    for item in items:
        if item.name.startswith(".") or not item.is_file():
            continue

        if item.stem in seen_names:
            continue

        if item.suffix.lower() == ".gif":
            with Image.open(item) as gif:
                total_frames = getattr(gif, "n_frames", 1)
                if total_frames > 1:
                    norm_frames = []
                    max_frames = min(24, total_frames)
                    step = max(1, total_frames // max_frames)
                    idx = 0
                    for f in range(0, total_frames, step):
                        if idx >= max_frames:
                            break
                        gif.seek(f)
                        frame_img = gif.convert("RGBA")
                        cache_frame = CACHE_DIR / f"{item.stem}_{idx:03d}.png"
                        w, h = frame_img.size
                        scale = max(WIDTH / w, HEIGHT / h)
                        nw, nh = max(WIDTH, int(w * scale)), max(HEIGHT, int(h * scale))
                        scaled = frame_img.resize((nw, nh), Image.Resampling.LANCZOS)
                        left = (nw - WIDTH) // 2
                        top = (nh - HEIGHT) // 2
                        cropped = scaled.crop((left, top, left + WIDTH, top + HEIGHT))
                        cropped.save(cache_frame, format="PNG")
                        remote_name = f"sc_{_sanitize_name(item.stem)}_{idx:03d}.png"
                        norm_frames.append((cache_frame, remote_name))
                        idx += 1
                    scenes.append(Scene(name=item.stem, is_animated=True, frames=norm_frames))
                    seen_names.add(item.stem)
                else:
                    cache_img = CACHE_DIR / f"{item.stem}.png"
                    norm_path = normalize_image_to_72x16(item, cache_img)
                    remote_name = f"sc_{_sanitize_name(item.stem)}.png"
                    scenes.append(Scene(name=item.stem, is_animated=False, frames=[(norm_path, remote_name)]))
                    seen_names.add(item.stem)

        elif item.suffix.lower() in valid_exts:
            cache_img = CACHE_DIR / f"{item.stem}.png"
            norm_path = normalize_image_to_72x16(item, cache_img)
            remote_name = f"sc_{_sanitize_name(item.stem)}.png"
            scenes.append(Scene(name=item.stem, is_animated=False, frames=[(norm_path, remote_name)]))
            seen_names.add(item.stem)

    # Sort scenes alphabetically by name for predictable sequential ordering
    scenes.sort(key=lambda s: s.name.lower())
    return scenes


def _sanitize_name(name: str) -> str:
    """Sanitize string for safe remote asset naming."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())
    return clean[:20]


# ============================================================================
# Screen Saver Engine
# ============================================================================

class ScreenSaver:
    def __init__(
        self,
        bar: BusyBarClient,
        scenes_dir: Path,
        interval: float = DEFAULT_INTERVAL,
        shuffle: bool = True,
        fps: float = DEFAULT_FPS,
    ) -> None:
        self.bar = bar
        self.scenes_dir = scenes_dir
        self.interval = interval
        self.shuffle = shuffle
        self.fps = fps

        self.scenes = load_scenes(self.scenes_dir)
        if not self.scenes:
            print(f"No scenes found in '{self.scenes_dir.name}'. Generating default starter scenes…")
            self.scenes_dir.mkdir(parents=True, exist_ok=True)
            try:
                from generate_scenes import generate_preset
                default_presets = [
                    "aquarium", "aurora", "cyberpunk_city", "fireplace",
                    "lava_lamp", "matrix", "pacman", "rainbow_wave", "synthwave"
                ]
                for name in default_presets:
                    generate_preset(name, self.scenes_dir, animated=True, frames=16)
                self.scenes = load_scenes(self.scenes_dir)
            except Exception as err:
                raise ValueError(
                    f"No valid scenes found in {scenes_dir.resolve()}, and auto-generation failed: {err}"
                ) from err

        self.order: list[int] = list(range(len(self.scenes)))
        if self.shuffle:
            random.shuffle(self.order)

        self.current_order_idx = 0
        self.is_paused = False
        self.skip_event = threading.Event()
        self.stop_event = threading.Event()
        self.condition = threading.Condition()
        self.pending_steps: deque[int] = deque()

        self.uploaded_assets: set[str] = set()
        self.initial_switch_pos: int | None = None

    def on_input_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "encoder":
            delta = int(event[1])
            if delta != 0:
                with self.condition:
                    # Encoder delta: positive is clockwise -> next scene
                    self.pending_steps.append(1 if delta > 0 else -1)
                    self.skip_event.set()
        elif kind == "button":
            btn, act = event[1], event[2]
            if btn == BTN_OK and act == ACT_RELEASE:
                self.is_paused = not self.is_paused
                if self.is_paused:
                    print("\n[OK Button] Loop locked: continuing current scene/animation indefinitely. (Press OK again to resume cycling)")
                else:
                    print("\n[OK Button] Loop unlocked: resumed scene cycling.")
        elif kind == "switch":
            pos = int(event[1])
            if self.initial_switch_pos is None:
                self.initial_switch_pos = pos
            elif pos != self.initial_switch_pos:
                print(f"\n[Switch] Mode switch moved to {pos}. Stopping Screen Saver…")
                self.stop_event.set()
                self.skip_event.set()

    def stream_controls(self) -> None:
        """Background listener for BUSY Bar rotary dial and buttons."""
        while not self.stop_event.is_set():
            socket = None
            try:
                socket = create_connection(self.bar.ws_url, timeout=5, enable_multithread=True)
                socket.settimeout(1)
                socket.send('{"enable":true}')
                while not self.stop_event.is_set():
                    try:
                        opcode, data = socket.recv_data(control_frame=False)
                    except WebSocketTimeoutException:
                        continue
                    if opcode != 2 or not data:
                        continue
                    for event in events_from_state(data):
                        self.on_input_event(event)
            except Exception:
                if self.stop_event.is_set():
                    return
                time.sleep(2)
            finally:
                if socket is not None:
                    try:
                        socket.close()
                    except Exception:
                        pass

    def _ensure_uploaded(self, local_path: Path, remote_name: str) -> None:
        if remote_name not in self.uploaded_assets:
            self.bar.upload_asset(local_path, remote_name)
            self.uploaded_assets.add(remote_name)

    def next_scene_index(self, step: int = 1) -> int:
        self.current_order_idx = (self.current_order_idx + step) % len(self.order)
        # If wrapped around in shuffle mode, reshuffle
        if self.shuffle and self.current_order_idx == 0 and step > 0:
            last_scene = self.order[-1]
            random.shuffle(self.order)
            # Ensure no immediate repeat of previous scene
            if len(self.order) > 1 and self.order[0] == last_scene:
                self.order[0], self.order[1] = self.order[1], self.order[0]
        return self.order[self.current_order_idx]

    def run(self) -> None:
        print(f"Loaded {len(self.scenes)} scenes from '{self.scenes_dir.name}':")
        for sc in self.scenes:
            mode_str = f"animated ({len(sc.frames)} frames)" if sc.is_animated else "static"
            print(f"  • {sc.name} ({mode_str})")

        print("\nScreen Saver starting:")
        print(f"  • Interval: {self.interval:g}s per scene")
        print(f"  • Playback: {'Shuffled' if self.shuffle else 'Sequential'}")
        print("  • Controls: Turn dial to skip / go back, press OK to lock/loop current scene")
        print("Press Ctrl+C to stop.\n")

        # Start background input thread
        control_thread = threading.Thread(target=self.stream_controls, daemon=True)
        control_thread.start()

        display_confirmed = False

        while not self.stop_event.is_set():
            scene_idx = self.order[self.current_order_idx]
            scene = self.scenes[scene_idx]

            # Check if pending dial step requested
            if self.pending_steps:
                with self.condition:
                    step = self.pending_steps.popleft()
                    self.pending_steps.clear()
                scene_idx = self.next_scene_index(step)
                scene = self.scenes[scene_idx]
                print(f"[Dial] Jumped to: {scene.name}")

            # Upload assets for current scene
            for local_path, remote_name in scene.frames:
                self._ensure_uploaded(local_path, remote_name)

            scene_num = self.current_order_idx + 1
            anim_info = f" ({len(scene.frames)} frames)" if scene.is_animated else ""
            print(f"[{scene_num}/{len(self.scenes)}] Displaying: {scene.name}{anim_info}")

            # Play the scene
            start_time = time.monotonic()
            frame_idx = 0
            frame_delay = 1.0 / max(0.5, self.fps) if scene.is_animated else 0.5
            has_drawn_static = False
            was_paused = self.is_paused

            self.skip_event.clear()

            while not self.stop_event.is_set():
                # Reset start_time when transitioning from locked to unlocked for a fresh full interval
                if was_paused and not self.is_paused:
                    start_time = time.monotonic()
                was_paused = self.is_paused

                # For static scenes, only draw once; for animated scenes, keep playing each frame in loop
                should_draw = scene.is_animated or not has_drawn_static

                if should_draw:
                    current_frame = scene.frames[frame_idx]
                    try:
                        self.bar.draw_image(current_frame[1])
                        has_drawn_static = True
                        if not display_confirmed:
                            print("Screen Saver is active on the BUSY Bar.")
                            display_confirmed = True
                    except requests.HTTPError as error:
                        if error.response is not None and error.response.status_code == 409:
                            print("BUSY Bar display is busy. Retrying in 10s...")
                            time.sleep(10)
                            continue
                        else:
                            print(f"Display error: {error}")
                    except requests.RequestException as error:
                        print(f"Connection issue: {error}")

                    if scene.is_animated:
                        frame_idx = (frame_idx + 1) % len(scene.frames)

                # Wait for frame_delay or skip signal
                self.skip_event.wait(timeout=frame_delay)

                if self.skip_event.is_set():
                    self.skip_event.clear()
                    break

                # Advance scene only if not locked / looping and interval has elapsed
                if not self.is_paused:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= self.interval:
                        self.next_scene_index(1)
                        break


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="BUSY Bar Screen Saver",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BUSYBAR_IP", DEFAULT_HOST),
        help="BUSY Bar IP address or USB default (10.0.4.20)",
    )
    parser.add_argument(
        "--scenes",
        type=Path,
        default=Path(os.environ.get("SCREENSAVER_SCENES_DIR", str(DEFAULT_SCENES_DIR))),
        help="Path to folder containing scenes",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("SCREENSAVER_INTERVAL", DEFAULT_INTERVAL)),
        help="Seconds to display each scene",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        default=os.environ.get("SCREENSAVER_SHUFFLE", "true").lower() in ("true", "1", "yes"),
        help="Shuffle playback order",
    )
    parser.add_argument(
        "--no-shuffle",
        dest="shuffle",
        action="store_false",
        help="Play scenes in alphabetical / folder order",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=float(os.environ.get("SCREENSAVER_FPS", DEFAULT_FPS)),
        help="Frames per second for animated scenes",
    )
    parser.add_argument(
        "--password",
        default=(
            os.environ.get("BUSYBAR_PASSWORD")
            or os.environ.get("BUSYBAR_TOKEN")
            or os.environ.get("BUSYBAR_API_KEY")
        ),
        help="Wi-Fi access password when connecting over LAN",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    bar = BusyBarClient(args.host, APP_ID, args.password)
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
        raise SystemExit(f"Could not connect to BUSY Bar at {args.host}: {error}") from error

    print(f"Connected to BUSY Bar at {bar.host} (API {version})")

    screensaver = ScreenSaver(
        bar=bar,
        scenes_dir=args.scenes,
        interval=args.interval,
        shuffle=args.shuffle,
        fps=args.fps,
    )

    try:
        screensaver.run()
    except KeyboardInterrupt:
        print("\nStopping Screen Saver…")
    finally:
        screensaver.stop_event.set()
        screensaver.skip_event.set()
        print("Cleaning up BUSY Bar display and assets…")
        bar.clear()
        bar.delete_assets()
        print("Done. Goodbye!")


if __name__ == "__main__":
    main()
