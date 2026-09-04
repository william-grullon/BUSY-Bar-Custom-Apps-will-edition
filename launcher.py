#!/usr/bin/env python3
"""Unified Interactive Terminal Launcher for BUSY Bar Custom Apps.

Allows the user to select and launch any of the custom BUSY Bar applications
from a clean, interactive terminal menu.
"""

from __future__ import annotations

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
        "name": "Ping Monitor",
        "description": "Monitor network host latency with color status on the display",
        "script": APPS_DIR / "ping-monitor" / "ping_monitor.py",
        "cwd": APPS_DIR / "ping-monitor",
    },
    {
        "name": "Network Speed Monitor",
        "description": "Show real-time download and upload bandwidth speeds",
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


def find_app_python(app_cwd: Path) -> str:
    """Find the virtual environment Python if available, otherwise sys.executable."""
    if os.name == "nt":
        venv_py = app_cwd / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = app_cwd / ".venv" / "bin" / "python"

    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def run_app(app_info: dict) -> None:
    """Launch the chosen app in a subprocess with its own virtualenv and working directory."""
    script_path: Path = app_info["script"]
    cwd: Path = app_info["cwd"]

    if not script_path.is_file():
        print(f"\n[!] Error: Script not found: {script_path}")
        return

    python_bin = find_app_python(cwd)
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
