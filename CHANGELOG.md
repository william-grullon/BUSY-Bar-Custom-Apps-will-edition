# Changelog

## 2026-09-04

- Added `apps/screen-saver/`, a customizable screen saver cycling through static
  and animated pixel art scenes on the front 72×16 RGB LED matrix with dial
  navigation, OK button pause/freeze, and smart image fitting.
- Added `apps/screen-saver/generate_scenes.py`, a scene generator and image/GIF
  converter with 12 procedural pixel-art presets, multi-frame animation support,
  Floyd-Steinberg dithering, and Windows/macOS double-click launchers.
- Added `apps/ping-monitor/`, a configurable connectivity and latency monitor
  with five-minute checks and Windows/macOS launchers.

## 2026-08-10

- Social Battery can start in Off mode, and closes only when the physical mode
  switch moves to a different position (not merely because the bar is not in
  Apps).

## 2026-08-09

- Kept `apps/spotify/` local-only (gitignored) until it is ready for community
  release.
- Added `apps/network/`: host app with UP/DOWN label artwork, live interface
  speeds, right-aligned values, Wi‑Fi password support, and Start Here
  launchers.
- Added `ai-lessons/` and `ai-skills/` (including pasteable `BUSY-BAR-CORE.md`)
  covering getting started, Wi‑Fi password vs cloud API token, HTTP API, fonts,
  and draw/assets for any AI assistant.
- Clarified that Apps mode is not required to start host widgets (Off mode is
  fine), including Social Battery setup docs.
