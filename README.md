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

### [Ping Monitor](apps/ping-monitor/)

Check a host's connectivity and latency every minute, with good, acceptable,
bad, and offline status colors.

## Additions in this fork

This fork includes the following custom host-side widgets:

- **Network** — displays this computer's live download and upload speeds.
- **Ping Monitor** — checks a configurable host every minute and displays its
  latency with good, acceptable, bad, and offline colors.
- **External configuration** — Ping Monitor can read the BUSY Bar IP address,
  Wi-Fi password, ping target, interval, and timeout from an optional local
  `apps/ping-monitor/.env` file. If no `.env` file exists, it defaults to the
  USB address `10.0.4.20` with no password.

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
