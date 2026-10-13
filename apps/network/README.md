# Network

Network shows this computer’s live **download** and **upload** speeds and the
**ping latency** to a host, all on one BUSY Bar screen. (This app now includes
what used to be the separate Ping Monitor app.)

The app runs on your computer and talks to a BUSY Bar using its official
release-firmware API. No modified firmware is needed.

**Note:** This measures traffic on a network interface on your computer (what
is moving right now). It is not a separate “speed test to a distant server.”
The ping is sent from your computer using its system `ping` command.

## What you need

- BUSY Bar with current release firmware
- Windows, macOS, or Linux computer
- Python 3.10 or newer
- USB or Wi-Fi connection to the BUSY Bar

Download Python from [python.org](https://www.python.org/downloads/) if it is
not already installed. On Windows, select **Add Python to PATH** during setup.

## 1. Download the app

1. Open this repository on GitHub:
   [BUSY-Bar-Custom-Apps](https://github.com/ArthurJamesBarker/BUSY-Bar-Custom-Apps).
2. Select **Code**, then **Download ZIP**.
3. Unzip the download.
4. Open `apps`, then `network`.

## 2. Prepare the BUSY Bar

1. Connect the BUSY Bar to the computer by USB, or connect both devices to the
   same Wi-Fi network.
2. If using Wi-Fi, enable **HTTP API access** on the BUSY Bar.
3. If that access is password-protected, keep the password ready; Network will
   ask for it. USB connections do not need this password.

USB normally uses `10.0.4.20`. For Wi-Fi, use the IP address shown by your BUSY
Bar. The password is sent directly to the BUSY Bar over the local Wi-Fi
connection and is not saved by Network. Only use a trusted Wi-Fi network.

For a permanent Wi-Fi setup, copy `.env.example` to `.env` in the repository
root (the folder with `Start.bat`) and set the bar's address there. Every app
reads this shared file:

```text
BUSYBAR_IP=192.168.1.123
BUSYBAR_PASSWORD=your-wifi-http-password
```

If an app cannot reach the bar, it asks for a new IP and saves it to this
shared file, so the other apps pick it up too.

Network's own settings go in `.env` in this folder (copy `.env.example`):

```text
NETWORK_INTERFACE=auto
NETWORK_REFRESH_INTERVAL=0.25
NETWORK_DISPLAY_TIMEOUT=1
PING_TARGET=1.1.1.1
PING_INTERVAL=10
PING_TIMEOUT=5
```

`PING_TARGET` is the host to ping. The default `1.1.1.1` checks general
internet reachability; a router address such as `192.168.1.1` checks your local
network instead. `PING_INTERVAL` is the number of seconds between pings, and
`PING_TIMEOUT` is how long to wait for each reply. Command-line options take
precedence over environment variables, which take precedence over `.env`.

The `.env` files are ignored by Git. If it is absent, Network defaults to USB at
`10.0.4.20` with no password.

## 3. Start Network

You can launch Network from the repository root using `Start.bat` (or `python launcher.py`), or open the **Start Here** folder in this directory and choose your computer:

### macOS

Double-click **macOS - Double-click to Start.command**.

The first time, macOS may require you to right-click the file and select
**Open**. The launcher uses `.env` when present, or the USB default when it is
absent.

### Windows

Double-click **Windows - Double-click to Start.bat**.

The launcher uses `.env` when present, or the USB default when it is absent.

### Linux or manual start

Open a terminal in this folder and run:

```bash
python3 -m pip install -r requirements.txt
python3 network.py
```

For a Wi-Fi BUSY Bar:

```bash
python3 network.py --host 192.168.1.123
```

Replace `192.168.1.123` with the BUSY Bar's IP address.

Optional Wi-Fi password without a prompt:

```bash
python3 network.py --host 192.168.1.123 --password YOUR_PASSWORD
```

To pick a specific network interface instead of auto:

```bash
python3 network.py --interface en0
```

To ping your router every 30 seconds instead of `1.1.1.1` every 10:

```bash
python3 network.py --target 192.168.1.1 --ping-interval 30
```

## What you will see

```text
D 48 Mb/s      PING
U 12 Mb/s       23
```

- Left 75%: live speeds — `D` is download, `U` is upload
- Right 25%: ping latency in milliseconds, colored by health:
  - Green / good: 50 ms or less
  - Yellow / acceptable: 51–100 ms
  - Red / bad: above 100 ms
  - Red `OFF`: no response or timeout

Speeds refresh several times per second; the ping refreshes every
`PING_INTERVAL` seconds (10 by default) and shows `...` until the first reply.

After the first successful display update, the terminal shows:

```text
Network is working; the result is on the BUSY Bar.
```

If another app owns the display, the terminal explains how to stop it and
retries every 10 seconds.

## Stopping the app

Press `Ctrl+C` in the terminal or close the launcher window. The app clears its
content from the BUSY Bar when it stops.

## Troubleshooting

### The BUSY Bar cannot be reached

- Check the USB cable or Wi-Fi connection.
- Confirm the IP address.
- For Wi-Fi, confirm HTTP API access is enabled.
- Try the USB address `10.0.4.20`.

### The Wi-Fi access password is rejected

Check the BUSY Bar's HTTP API access settings and enter its password when
prompted. This password is only used for protected access over Wi-Fi.

### Speeds stay at 0 Mb/s

That usually means this computer is not sending or receiving much traffic on
the selected interface. Open a download or upload and watch again, or pass
`--interface` with another interface name.

### The ping shows `OFF`

- Try pinging a different target with `--target`.
- Check whether the target blocks ICMP ping requests.
- Try your router address to separate local-network problems from internet
  connectivity problems.

### The app says the display is busy

Stop Social Battery, Screen Saver, or any other BUSY Bar app that is still
running with `Ctrl+C`, **Back**, or the BUSY Bar mode switch. Network retries
every 10 seconds until the display becomes available.

### `ping` is not found

Install or enable the operating system's standard `ping` command, then restart
the app.

### Python is not found

Install Python 3.10 or newer from
[python.org](https://www.python.org/downloads/), then reopen the launcher.

## Files included

- `network.py` — the complete app in one Python file
- `requirements.txt` — Python packages used by the app
- `Start Here` — double-click starters for macOS and Windows
