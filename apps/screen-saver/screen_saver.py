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
SHARED_ENV = APP_DIR.parent.parent / ".env"
DEFAULT_SCENES_DIR = APP_DIR / "scenes"
CACHE_DIR = APP_DIR / ".cache"


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
        selected_scenes: list[Scene] | None = None,
        initial_pause: bool = False,
    ) -> None:
        self.bar = bar
        self.scenes_dir = scenes_dir
        self.interval = interval
        self.shuffle = shuffle
        self.fps = fps

        self.all_scenes = load_scenes(self.scenes_dir)
        if not self.all_scenes:
            print(f"No scenes found in '{self.scenes_dir.name}'. Generating default starter scenes...")
            self.scenes_dir.mkdir(parents=True, exist_ok=True)
            try:
                from generate_scenes import generate_preset
                default_presets = [
                    "aquarium", "aurora", "cyberpunk_city", "fireplace",
                    "lava_lamp", "matrix", "pacman", "rainbow_wave", "synthwave"
                ]
                for name in default_presets:
                    generate_preset(name, self.scenes_dir, animated=True, frames=16)
                self.all_scenes = load_scenes(self.scenes_dir)
            except Exception as err:
                raise ValueError(
                    f"No valid scenes found in {scenes_dir.resolve()}, and auto-generation failed: {err}"
                ) from err

        self.is_single_scene = bool(selected_scenes is not None and len(selected_scenes) == 1)

        if selected_scenes is not None and len(selected_scenes) > 0:
            self.scenes = list(selected_scenes)
        else:
            self.scenes = list(self.all_scenes)

        self.order: list[int] = list(range(len(self.scenes)))
        if self.shuffle and len(self.scenes) > 1:
            random.shuffle(self.order)

        self.current_order_idx = 0
        self.is_paused = initial_pause
        self.return_to_menu = False
        self.skip_event = threading.Event()
        self.stop_event = threading.Event()
        self.condition = threading.Condition()
        self.pending_steps: deque[int] = deque()

        self.uploaded_assets: set[str] = set()
        self.initial_switch_pos: int | None = None

    def switch_to_all_scenes(self) -> None:
        """Switch from single-scene mode back to full rotation cycling of all scenes."""
        if self.is_single_scene or len(self.scenes) < len(self.all_scenes):
            print(f"\n[Mode Switch] Resumed full cycling rotation across all {len(self.all_scenes)} scenes!")
            self.scenes = list(self.all_scenes)
            self.order = list(range(len(self.scenes)))
            if self.shuffle and len(self.scenes) > 1:
                random.shuffle(self.order)
            self.current_order_idx = 0
            self.is_single_scene = False
            self.is_paused = False
            self.skip_event.set()
        else:
            print("\n[Mode] Already cycling all scenes.")

    def trigger_step(self, step: int) -> None:
        if self.is_single_scene and len(self.all_scenes) > 1:
            current_name = self.scenes[self.order[self.current_order_idx]].name
            names = [s.name for s in self.all_scenes]
            try:
                curr_i = names.index(current_name)
            except ValueError:
                curr_i = 0
            next_i = (curr_i + step) % len(self.all_scenes)
            target_sc = self.all_scenes[next_i]
            self.scenes = [target_sc]
            self.order = [0]
            self.current_order_idx = 0
            print(f"\n[Browse] Switched to single scene: {target_sc.name} (Press Space or A to cycle all scenes, M for menu)")
            self.skip_event.set()
            return

        with self.condition:
            self.pending_steps.append(step)
            self.skip_event.set()

    def toggle_pause(self) -> None:
        if self.is_single_scene:
            self.switch_to_all_scenes()
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("\n[Terminal] Loop locked on current scene. (Press Space or L to resume cycling)")
        else:
            print("\n[Terminal] Loop unlocked: resumed scene cycling.")

    def toggle_shuffle(self) -> None:
        self.shuffle = not self.shuffle
        mode = "ON (Randomized)" if self.shuffle else "OFF (Sequential)"
        print(f"\n[Terminal] Shuffle mode: {mode}")

    def jump_to_scene(self, scene_idx: int) -> None:
        if 0 <= scene_idx < len(self.scenes):
            target_scene = self.scenes[scene_idx]
            for pos, s_idx in enumerate(self.order):
                if s_idx == scene_idx:
                    self.current_order_idx = pos
                    break
            print(f"\n[Terminal] Jumped to scene #{scene_idx + 1}: {target_scene.name}")
            self.skip_event.set()

    def adjust_fps(self, delta: int) -> None:
        """Adjust animation frame rate between 1 and 16 FPS."""
        new_fps = max(1.0, min(16.0, round(self.fps + delta)))
        if new_fps != self.fps:
            self.fps = new_fps
            print(f"\n[FPS] Animation speed: {int(self.fps)} FPS (Range: 1-16, default: 4)")
        else:
            limit = "16 (maximum)" if delta > 0 else "1 (minimum)"
            print(f"\n[FPS] Already at {limit} FPS.")

    def _handle_terminal_key(self, char: str) -> None:
        if char in (" ", "l"):
            self.toggle_pause()
        elif char in ("u", "up", "+", "="):
            self.adjust_fps(1)
        elif char in ("d", "down", "-", "_"):
            self.adjust_fps(-1)
        elif char == "a":
            self.switch_to_all_scenes()
        elif char in ("m", "b") or char == "\x1b":
            print("\n[Terminal] Returning to menu...")
            self.return_to_menu = True
            self.stop_event.set()
            self.skip_event.set()
        elif char in ("n", "\r", "\n"):
            self.trigger_step(1)
        elif char == "p":
            self.trigger_step(-1)
        elif char == "s":
            self.toggle_shuffle()
        elif char == "q":
            print("\n[Terminal] Stop requested. Cleaning up...")
            self.return_to_menu = False
            self.stop_event.set()
            self.skip_event.set()
        elif char.isdigit():
            digit = int(char)
            if 1 <= digit <= len(self.all_scenes):
                if self.is_single_scene:
                    target_sc = self.all_scenes[digit - 1]
                    self.scenes = [target_sc]
                    self.order = [0]
                    self.current_order_idx = 0
                    print(f"\n[Terminal] Jumped to scene #{digit}: {target_sc.name}")
                    self.skip_event.set()
                elif 1 <= digit <= len(self.scenes):
                    self.jump_to_scene(digit - 1)

    def stream_terminal_controls(self) -> None:
        """Listen for live keyboard commands from the terminal during playback."""
        if os.name == "nt" and sys.stdin.isatty():
            import msvcrt
            while not self.stop_event.is_set():
                try:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        if ch in (b"\x00", b"\xe0"):
                            ext = msvcrt.getch()
                            if ext == b"H":  # Up arrow
                                self._handle_terminal_key("u")
                            elif ext == b"P":  # Down arrow
                                self._handle_terminal_key("d")
                            elif ext == b"M":  # Right arrow
                                self.trigger_step(1)
                            elif ext == b"K":  # Left arrow
                                self.trigger_step(-1)
                            continue
                        try:
                            char = ch.decode("utf-8", errors="ignore").lower()
                        except Exception:
                            continue
                        self._handle_terminal_key(char)
                except Exception:
                    pass
                time.sleep(0.05)
        elif not sys.stdin.isatty():
            while not self.stop_event.is_set():
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    for char in line.strip().lower():
                        self._handle_terminal_key(char)
                except Exception:
                    break
                time.sleep(0.05)
        else:
            try:
                import termios
                import tty
                import select
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    while not self.stop_event.is_set():
                        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if rlist:
                            char = sys.stdin.read(1)
                            if char == "\x1b":
                                sub_rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                                if sub_rlist:
                                    seq1 = sys.stdin.read(1)
                                    if seq1 == "[":
                                        seq2 = sys.stdin.read(1)
                                        if seq2 == "A":  # Up arrow
                                            self._handle_terminal_key("u")
                                            continue
                                        elif seq2 == "B":  # Down arrow
                                            self._handle_terminal_key("d")
                                            continue
                                        elif seq2 == "C":  # Right arrow
                                            self.trigger_step(1)
                                            continue
                                        elif seq2 == "D":  # Left arrow
                                            self.trigger_step(-1)
                                            continue
                            self._handle_terminal_key(char.lower())
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

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
                if self.is_single_scene:
                    self.switch_to_all_scenes()
                else:
                    self.is_paused = not self.is_paused
                    if self.is_paused:
                        print("\n[OK Button] Loop locked: continuing current scene/animation indefinitely. (Press OK again to resume cycling)")
                    else:
                        print("\n[OK Button] Loop unlocked: resumed scene cycling.")
            elif btn == BTN_BACK and act == ACT_RELEASE:
                print("\n[Back Button] Returning to menu...")
                self.return_to_menu = True
                self.stop_event.set()
                self.skip_event.set()
        elif kind == "switch":
            pos = int(event[1])
            if self.initial_switch_pos is None:
                self.initial_switch_pos = pos
            elif pos != self.initial_switch_pos:
                print(f"\n[Switch] Mode switch moved to {pos}. Stopping Screen Saver...")
                self.return_to_menu = False
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
        print(f"Loaded {len(self.scenes)} scene{'s' if len(self.scenes) != 1 else ''} from '{self.scenes_dir.name}':")
        for sc in self.scenes:
            mode_str = f"animated ({len(sc.frames)} frames)" if sc.is_animated else "static"
            print(f"  • {sc.name} ({mode_str})")

        print("\nScreen Saver starting:")
        print(f"  • Interval: {self.interval:g}s per scene")
        print(f"  • Playback: {'Shuffled' if self.shuffle else 'Sequential'}")
        print(f"  • FPS:      {int(self.fps)} frames/sec (Range: 1-16, adjust with Up/Down arrows)")

        print("\n" + "=" * 62)
        if self.is_single_scene:
            print(" Single Scene Controls:")
            print("   Terminal: [Up Arrow] FPS +1      | [Down Arrow] FPS -1 (1-16)")
            print("             [Right/Left Arrows] Next / Previous scene")
            print("             [Space] Unlock loop    | [A] Switch to all scenes")
            print("             [M]/[B]/[Esc] Menu     | [1-9] Jump to scene")
            print("             [Q] Stop & exit")
            print("   Hardware: Press OK to unlock & cycle all scenes | Press Back for menu")
            print("             Turn dial to browse scenes")
        else:
            print(" Live Controls:")
            print("   Terminal: [Up Arrow] FPS +1      | [Down Arrow] FPS -1 (1-16)")
            print("             [Right/Left Arrows] Next / Previous scene")
            print("             [Space]/[L] Keep loop / Lock | [S] Toggle shuffle")
            print("             [M]/[B]/[Esc] Menu     | [1-9] Jump to scene")
            print("             [Q] Stop & exit")
            print("   Hardware: Turn dial to skip/back | Press OK to lock loop")
            print("             Press Back button to return to menu")
        print("=" * 62 + "\n")

        # Start background input threads
        control_thread = threading.Thread(target=self.stream_controls, daemon=True)
        control_thread.start()

        terminal_thread = threading.Thread(target=self.stream_terminal_controls, daemon=True)
        terminal_thread.start()

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

                # Wait for dynamically updated frame delay (1-16 FPS) or skip signal
                current_delay = 1.0 / max(1.0, min(16.0, self.fps)) if scene.is_animated else 0.5
                self.skip_event.wait(timeout=current_delay)

                if self.skip_event.is_set():
                    self.skip_event.clear()
                    break

                # Advance scene only if not locked / looping and interval has elapsed
                if not self.is_paused:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= self.interval:
                        self.next_scene_index(1)
                        break


def interactive_startup_menu(
    bar: BusyBarClient,
    scenes_dir: Path,
    interval: float,
    shuffle: bool,
    fps: float,
) -> tuple[list[Scene], float, bool, float, bool] | None:
    """Interactive terminal menu allowing the user to pick scenes, change settings, etc.

    Returns:
        (scenes_to_play, interval, shuffle, fps, initial_pause) or None to exit.
    """
    cur_interval = interval
    cur_shuffle = shuffle
    cur_fps = fps

    while True:
        all_scenes = load_scenes(scenes_dir)
        print("\n" + "=" * 62)
        print("           BUSY Bar Screen Saver - Terminal Menu")
        print("=" * 62)
        print(f" BUSY Bar:       {bar.host}")
        print(f" Scenes Folder:  {scenes_dir.resolve()} ({len(all_scenes)} scenes found)")
        shuffle_str = "ON (Randomized)" if cur_shuffle else "OFF (Sequential)"
        print(f" Current Config: Interval: {cur_interval:g}s | Shuffle: {shuffle_str} | FPS: {cur_fps:g}")
        print("-" * 62)
        print(" Select an option:")
        print("   1. Start Screen Saver (Cycle all scenes) [Default: Press Enter]")
        print("   2. Pick a single scene to loop indefinitely")
        print("   3. Select custom scenes to cycle")
        print("   4. Change playback settings (Interval, Shuffle, FPS)")
        print("   5. Launch Scene Generator (Create presets, convert images/GIFs)")
        print("   0. Exit")
        print("-" * 62)

        try:
            choice = input("Enter choice (0-5) [1]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return None

        if choice in ("", "1"):
            return (all_scenes, cur_interval, cur_shuffle, cur_fps, False)

        elif choice == "2":
            if not all_scenes:
                print("\n[!] No scenes available in folder.")
                continue
            print("\nAvailable Scenes:")
            for i, sc in enumerate(all_scenes, 1):
                mode = f"animated, {len(sc.frames)} frames" if sc.is_animated else "static"
                print(f"  {i:2d}. {sc.name} ({mode})")
            print("-" * 40)
            try:
                pick = input(f"Select scene (1-{len(all_scenes)}) or name ['b' to go back]: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if pick.lower() in ("b", "back", ""):
                continue

            chosen: Scene | None = None
            if pick.isdigit() and 1 <= int(pick) <= len(all_scenes):
                chosen = all_scenes[int(pick) - 1]
            else:
                for sc in all_scenes:
                    if sc.name.lower() == pick.lower():
                        chosen = sc
                        break

            if chosen is not None:
                print(f"\n[+] Selected '{chosen.name}'. Starting in single-scene loop mode...")
                return ([chosen], cur_interval, False, cur_fps, True)
            else:
                print(f"\n[!] Invalid selection '{pick}'.")

        elif choice == "3":
            if not all_scenes:
                print("\n[!] No scenes available in folder.")
                continue
            print("\nAvailable Scenes:")
            for i, sc in enumerate(all_scenes, 1):
                mode = f"animated, {len(sc.frames)} frames" if sc.is_animated else "static"
                print(f"  {i:2d}. {sc.name} ({mode})")
            print("-" * 40)
            try:
                pick = input("Enter scene numbers to include (comma-separated, e.g. 1, 3, 5) ['b' for back]: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if pick.lower() in ("b", "back", ""):
                continue

            selected_list: list[Scene] = []
            parts = [p.strip() for p in pick.replace(";", ",").split(",") if p.strip()]
            for p in parts:
                if p.isdigit() and 1 <= int(p) <= len(all_scenes):
                    sc = all_scenes[int(p) - 1]
                    if sc not in selected_list:
                        selected_list.append(sc)
                else:
                    for sc in all_scenes:
                        if sc.name.lower() == p.lower() and sc not in selected_list:
                            selected_list.append(sc)

            if selected_list:
                print(f"\n[+] Selected {len(selected_list)} scenes for rotation:")
                for s in selected_list:
                    print(f"    • {s.name}")
                return (selected_list, cur_interval, cur_shuffle, cur_fps, False)
            else:
                print(f"\n[!] No matching scenes found from '{pick}'.")

        elif choice == "4":
            while True:
                print("\nPlayback Settings:")
                print(f"  1. Scene Interval:    {cur_interval:g} seconds")
                sh_status = "ON (Randomized)" if cur_shuffle else "OFF (Sequential)"
                print(f"  2. Shuffle Mode:       {sh_status}")
                print(f"  3. Animation FPS:      {cur_fps:g} frames/second")
                print("  4. Return to Main Menu")
                print("-" * 40)
                try:
                    s_choice = input("Select setting to adjust (1-4) [4]: ").strip()
                except (KeyboardInterrupt, EOFError):
                    break
                if s_choice == "1":
                    try:
                        val = input(f"Enter interval in seconds [{cur_interval:g}]: ").strip()
                        if val:
                            cur_interval = max(1.0, float(val))
                    except ValueError:
                        print("[!] Invalid number.")
                elif s_choice == "2":
                    cur_shuffle = not cur_shuffle
                    print(f"[+] Shuffle is now {'ON' if cur_shuffle else 'OFF'}.")
                elif s_choice == "3":
                    try:
                        val = input(f"Enter animation FPS [{cur_fps:g}]: ").strip()
                        if val:
                            cur_fps = max(0.5, float(val))
                    except ValueError:
                        print("[!] Invalid number.")
                else:
                    break

        elif choice == "5":
            try:
                from generate_scenes import interactive_menu as gen_menu
                gen_menu(scenes_dir)
            except Exception as err:
                print(f"\n[!] Could not run Scene Generator: {err}")

        elif choice in ("0", "q", "exit"):
            print("\nGoodbye!")
            return None

        else:
            print(f"\n[!] Unknown choice '{choice}'. Please pick 0-5.")


def parse_args() -> argparse.Namespace:
    load_dotenv()
    scenes_env = os.environ.get("SCREENSAVER_SCENES_DIR")
    if scenes_env:
        raw_path = Path(scenes_env)
        default_scenes = raw_path if raw_path.is_absolute() else (APP_DIR / raw_path).resolve()
    else:
        default_scenes = DEFAULT_SCENES_DIR

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
        default=default_scenes,
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
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Play only a specific scene by name and loop indefinitely",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scenes in the scenes folder and exit",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip terminal interactive menu and start immediately",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Force interactive terminal menu",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Handle --list flag
    if args.list:
        all_scenes = load_scenes(args.scenes)
        print(f"\nAvailable scenes in '{args.scenes.resolve()}' ({len(all_scenes)} total):")
        for i, sc in enumerate(all_scenes, 1):
            mode_str = f"animated ({len(sc.frames)} frames)" if sc.is_animated else "static"
            print(f"  {i:2d}. {sc.name:<20} [{mode_str}]")
        return

    host = args.host
    while True:
        bar = BusyBarClient(host, APP_ID, args.password)
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

    selected_scenes: list[Scene] | None = None
    interval = args.interval
    shuffle = args.shuffle
    fps = args.fps
    initial_pause = False

    while True:
        # If --scene was provided via CLI, filter directly (first iteration)
        if args.scene and selected_scenes is None:
            all_scenes = load_scenes(args.scenes)
            target = args.scene.strip().lower()
            matched = [s for s in all_scenes if s.name.lower() == target]
            if not matched:
                matched = [s for s in all_scenes if target in s.name.lower()]
            if not matched:
                raise SystemExit(f"Error: Scene '{args.scene}' not found in {args.scenes.resolve()}")
            selected_scenes = [matched[0]]
            initial_pause = True
            print(f"Playing single scene: {matched[0].name} (loop locked)")
        elif not args.non_interactive and (args.interactive or sys.stdin.isatty()):
            # Show interactive terminal menu
            menu_result = interactive_startup_menu(bar, args.scenes, interval, shuffle, fps)
            if menu_result is None:
                break
            selected_scenes, interval, shuffle, fps, initial_pause = menu_result

        screensaver = ScreenSaver(
            bar=bar,
            scenes_dir=args.scenes,
            interval=interval,
            shuffle=shuffle,
            fps=fps,
            selected_scenes=selected_scenes,
            initial_pause=initial_pause,
        )

        try:
            screensaver.run()
        except KeyboardInterrupt:
            print("\nStopping Screen Saver...")
            break
        finally:
            screensaver.stop_event.set()
            screensaver.skip_event.set()

        if screensaver.return_to_menu and not args.non_interactive:
            # Clear previous single scene selection and clear display before showing menu
            selected_scenes = None
            args.scene = None
            bar.clear()
            continue
        else:
            break

    print("Cleaning up BUSY Bar display and assets...")
    bar.clear()
    bar.delete_assets()
    print("Done. Goodbye!")


if __name__ == "__main__":
    main()
