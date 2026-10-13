#!/usr/bin/env python3
"""Unified Interactive Terminal Launcher for BUSY Bar Custom Apps.

Allows the user to select and launch any of the custom BUSY Bar applications
from a clean, interactive terminal menu.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
APPS_DIR = ROOT_DIR / "apps"

APPS = [
    {
        "name": "Screen Saver",
        "description": "Cycle & display animated pixel art scenes on your BUSY Bar",
        "script": APPS_DIR / "screen-saver" / "screen_saver.py",
        "cwd": APPS_DIR / "screen-saver",
    },
    {
        "name": "Scene Generator",
        "description": "Create procedural pixel art presets or convert photos and GIFs",
        "script": APPS_DIR / "screen-saver" / "generate_scenes.py",
        "cwd": APPS_DIR / "screen-saver",
    },
    {
        "name": "Network Monitor",
        "description": "Show live download/upload speeds and ping latency",
        "script": APPS_DIR / "network" / "network.py",
        "cwd": APPS_DIR / "network",
    },
    {
        "name": "Social Battery",
        "description": "Turn the rotary dial to set and display your social energy level",
        "script": APPS_DIR / "social-battery" / "social_battery.py",
        "cwd": APPS_DIR / "social-battery",
    },
]


def venv_python(app_cwd: Path) -> Path:
    """Return the path to the Python interpreter inside the app's virtualenv."""
    if os.name == "nt":
        return app_cwd / ".venv" / "Scripts" / "python.exe"
    return app_cwd / ".venv" / "bin" / "python"


def prepare_app_env(app_info: dict) -> str | None:
    """Create the app's virtualenv and install its requirements when needed.

    Returns the interpreter to use, or None if setup failed.
    """
    cwd: Path = app_info["cwd"]
    venv_py = venv_python(cwd)
    requirements = cwd / "requirements.txt"

    if not venv_py.is_file():
        print(f"Preparing {app_info['name']} for first use...")
        result = subprocess.run([sys.executable, "-m", "venv", str(cwd / ".venv")], cwd=str(cwd))
        if result.returncode != 0 or not venv_py.is_file():
            print(f"\n[!] Could not create a virtual environment in {cwd / '.venv'}")
            return None

    if requirements.is_file():
        # Only reinstall when requirements.txt changes, so launches stay fast.
        digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
        stamp = cwd / ".venv" / ".requirements.sha256"
        if not stamp.is_file() or stamp.read_text().strip() != digest:
            print(f"Installing dependencies for {app_info['name']}...")
            result = subprocess.run(
                [str(venv_py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                 "-r", str(requirements)],
                cwd=str(cwd),
            )
            if result.returncode != 0:
                print(f"\n[!] Failed to install dependencies from {requirements}")
                return None
            stamp.write_text(digest)

    return str(venv_py)


def run_app(app_info: dict) -> None:
    """Launch the chosen app in a subprocess with its own virtualenv and working directory."""
    script_path: Path = app_info["script"]
    cwd: Path = app_info["cwd"]

    if not script_path.is_file():
        print(f"\n[!] Error: Script not found: {script_path}")
        return

    python_bin = prepare_app_env(app_info)
    if python_bin is None:
        return

    print("\n" + "=" * 62)
    print(f" Starting {app_info['name']}...")
    print(f" Working Directory: {cwd}")
    print(f" Interpreter:       {python_bin}")
    print("=" * 62 + "\n")

    try:
        subprocess.run([python_bin, str(script_path)], cwd=str(cwd))
    except KeyboardInterrupt:
        print(f"\nStopped {app_info['name']}.")
    except Exception as err:
        print(f"\n[!] Error launching {app_info['name']}: {err}")


def main() -> None:
    """Main interactive terminal loop."""
    while True:
        print("\n" + "=" * 62)
        print("          BUSY Bar Custom Apps - Terminal Launcher")
        print("=" * 62)
        print("Select an application to run:\n")
        for i, app in enumerate(APPS, 1):
            print(f"  {i}. {app['name']:<24} {app['description']}")
        print("  0. Exit")
        print("-" * 62)

        try:
            choice = input(f"Enter choice (0-{len(APPS)}) [1]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if choice in ("", "1"):
            run_app(APPS[0])
        elif choice.isdigit() and 1 <= int(choice) <= len(APPS):
            run_app(APPS[int(choice) - 1])
        elif choice in ("0", "q", "exit"):
            print("\nGoodbye!")
            break
        else:
            print(f"\n[!] Invalid choice '{choice}'. Please pick a number from 0 to {len(APPS)}.")


if __name__ == "__main__":
    main()
