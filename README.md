# BUSY Bar Custom Apps

Community apps for the [BUSY Bar](https://busy.bar/) running official release
firmware.

Each app has its own folder with everything needed to install and run it. No
custom or modified firmware is required.

## Available apps

### [Social Battery](apps/social-battery/)

Turn the BUSY Bar dial to show your current social-energy level, from critical
to full.

### [Network](apps/network/)

Show live download/upload speeds on the BUSY Bar with UP/DOWN label artwork.

### [Ping Monitor](apps/ping-monitor/) — Added in this fork

Check a host's connectivity and latency every minute, with good, acceptable,
bad, and offline status colors.

## Additions in this fork

This fork adds the following custom host-side widget and configuration support:

- **Ping Monitor — Added in this fork** — checks a configurable host every
  minute and displays its latency with good, acceptable, bad, and offline
  colors.
- **Wi-Fi configuration** — Social Battery, Network, and Ping Monitor can read
  the BUSY Bar IP address and Wi-Fi HTTP access password from an optional local
  `.env` file in each app folder. Ping Monitor also stores its ping target and
  timing settings there; Network stores its interface and display settings.
  If no `.env` file exists, every app defaults to the USB address `10.0.4.20`
  with no password.

Copy an app's `.env.example` to `.env`, edit the values, and start the app with
its launcher. The `.env` files are ignored by Git so passwords stay local.

See [apps/ping-monitor/README.md](apps/ping-monitor/README.md) for setup and
usage instructions.

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
