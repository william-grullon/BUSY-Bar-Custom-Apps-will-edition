# BUSY Bar Custom Apps

Community apps for the [BUSY Bar](https://busy.bar/) running official release
firmware.

Each app has its own folder with everything needed to install and run it. No
custom or modified firmware is required.

## Quick start

Double-click the launcher in the root folder to open the interactive terminal launcher:

- **Windows**: `Start.bat`
- **macOS / Linux**: `Start.command` (or run `python launcher.py`)

From here, you can select and launch any app directly from your terminal.

## Available apps

### [Social Battery](apps/social-battery/)

Turn the BUSY Bar dial to show your current social-energy level, from critical
to full.

### [Network](apps/network/)

Show live download/upload speeds on the BUSY Bar with UP/DOWN label artwork.

### [Ping Monitor](apps/ping-monitor/) — Added in this fork

Check a host's connectivity and latency every minute, with good, acceptable,
bad, and offline status colors.

### [Screen Saver](apps/screen-saver/) — Added in this fork

Cycles through animated and static pixel art scenes on your BUSY Bar front
display with rotary dial navigation, button pause/freeze, smart image fitting,
and an included Scene Generator tool to create custom presets or convert photos.

## Additions in this fork

This fork adds the following custom host-side widget and configuration support:

- **Unified Terminal Launcher — Added in this fork** — run `Start.bat` (or `python launcher.py`)
  at the repository root to pick and launch any app (Screen Saver, Scene Generator, Ping Monitor, Network,
  or Social Battery) directly from an interactive terminal menu.
- **Screen Saver & Scene Generator — Added in this fork** — cycles through
  scenes on a configurable interval or via dial turns, with support for animated
  frames and GIFs, loop-locking on the OK button, an interactive terminal menu
  (pick scenes, subsets, or settings), real-time terminal keyboard controls (Arrow keys: Up/Down arrows adjust FPS
  from 1 to 16, Left/Right arrows navigate scenes; `[Space]` lock/unlock loop, `[M]` menu, `[A]` all scenes, `[1-9]`, `[Q]`),
  and an interactive procedural pixel art generator and image converter. Comes pre-packaged with 9 default
  animated scenes (aquarium, aurora, cyberpunk city, fireplace, lava lamp, matrix,
  pacman, rainbow wave, synthwave) that users can keep, delete, or customize.
- **Ping Monitor — Added in this fork** — checks a configurable host every
  minute and displays its latency with good, acceptable, bad, and offline
  colors.
- After its first successful display update, Ping Monitor confirms in the
  terminal that it is working. If the display is busy, it explains how to stop
  the other app and retries every 10 seconds.
- **Wi-Fi configuration** — Social Battery, Network, Ping Monitor, and Screen
  Saver can read the BUSY Bar IP address and Wi-Fi HTTP access password from an
  optional local `.env` file in each app folder. Ping Monitor also stores its ping
  target and timing settings there; Network stores its interface and display
  settings; Screen Saver stores its interval and playback settings.
  If no `.env` file exists, every app defaults to the USB address `10.0.4.20`
  with no password.

Copy an app's `.env.example` to `.env`, edit the values, and start the app with
its launcher. The `.env` files are ignored by Git so passwords stay local.

See [apps/screen-saver/README.md](apps/screen-saver/README.md) and
[apps/ping-monitor/README.md](apps/ping-monitor/README.md) for setup and usage
instructions.

## AI lessons and skills

Plain Markdown for any AI assistant:

- Paste this into a chat: [ai-skills/BUSY-BAR-CORE.md](ai-skills/BUSY-BAR-CORE.md)
- Skills: [ai-skills/](ai-skills/)
- Longer lessons: [ai-lessons/](ai-lessons/)
- How to use: [ai-lessons/00-use-with-any-ai.md](ai-lessons/00-use-with-any-ai.md)

## Before you start

You need:

- a BUSY Bar with current release firmware;
- a Windows, macOS, or Linux computer;
- Python 3.10 or newer;
- either a USB connection or the BUSY Bar's Wi-Fi IP address.

Open an app's folder and follow its README. Each app includes beginner-friendly
instructions.

## Safety and privacy

- Apps communicate directly with your BUSY Bar over your local network.
- A protected Wi-Fi access password is sent directly to the BUSY Bar when
  needed. It is not saved by the app.
- These are community projects and are not official BUSY Bar applications.

## License

Code and included artwork are released under the [MIT License](LICENSE).
