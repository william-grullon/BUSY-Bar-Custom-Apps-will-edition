# Ping Monitor

Ping Monitor checks the reachability and latency of a host, then shows the
result on the BUSY Bar front display. It runs one check immediately and then
checks again every minute.

The default target is `1.1.1.1`, which tests internet connectivity. You can
instead monitor your router, a server, or a game host with `--target`.

## What you need

- A BUSY Bar with current release firmware
- Windows, macOS, or Linux
- Python 3.10 or newer
- A USB connection to the BUSY Bar, or its IP address on your Wi-Fi network

USB normally uses `10.0.4.20`. For Wi-Fi, the computer and BUSY Bar must be on
the same network and HTTP API access must be enabled on the BUSY Bar.
If you do not create a `.env` file, the app automatically uses the USB address
`10.0.4.20` and does not use a password.

## Start with the launcher

Open the `Start Here` folder and double-click the launcher for your computer:

- Windows: `Windows - Double-click to Start.bat`
- macOS: `macOS - Double-click to Start.command`

The launcher creates a private Python environment and installs the required
package the first time it runs. Enter the BUSY Bar IP address when prompted, or
press Enter to use the USB default. Enter the host you want to monitor, or
press Enter to use `1.1.1.1`.

On macOS, you may need to right-click the launcher and choose **Open** the
first time.

For a permanent setup, copy `.env.example` to `.env` in this app folder and
edit the values. The `.env` file is ignored by git, so your Wi-Fi password will
not be committed:

```text
BUSYBAR_IP=192.168.1.123
BUSYBAR_PASSWORD=your-wifi-http-password
PING_TARGET=192.168.1.1
PING_INTERVAL=60
PING_TIMEOUT=5
```

After that, start the app normally. Command-line options take precedence over
`.env` values, and environment variables take precedence over `.env` values.

## Start manually

From this folder:

```bash
python3 -m pip install -r requirements.txt
python3 ping_monitor.py
```

For Wi-Fi BUSY Bar connections:

```bash
python3 ping_monitor.py --host 192.168.1.123
```

If the BUSY Bar's Wi-Fi HTTP API is password-protected, the app asks for the
Wi-Fi access password. You can also provide it through an environment variable:

```bash
BUSYBAR_PASSWORD="your-password" python3 ping_monitor.py
```

On Windows PowerShell:

```powershell
$env:BUSYBAR_PASSWORD = "your-password"
python ping_monitor.py
```

The same settings can be stored in `.env`, as described above.

To monitor your router instead:

```bash
python3 ping_monitor.py --target 192.168.1.1
```

The interval is one minute by default. For testing, use a shorter interval:

```bash
python3 ping_monitor.py --interval 10
```

The interval is measured in seconds. For example, to check every 30 seconds:

```bash
python3 ping_monitor.py --interval 30
```

You can combine options:

```bash
python3 ping_monitor.py --host 192.168.1.123 --target 192.168.1.1 --interval 60
```

## Display

- Green / good: 50 ms or less
- Yellow / acceptable: 51–100 ms
- Red / bad: above 100 ms
- Red `OFFLINE`: no response or timeout

The app uses the computer's system `ping` command and does not require an API
key for the ping target.

## How it works

The app sends one ping from the computer running the app. It does not measure
the BUSY Bar's own Wi-Fi speed, and it is not a speed test. The result remains
on the display until the next check. The default target `1.1.1.1` checks
general internet reachability; a router address such as `192.168.1.1` checks
the local network connection instead.

## Stopping

Press `Ctrl+C` in the terminal. If using a launcher, close its terminal window
after the app stops. The app clears its content from the BUSY Bar when it stops.

## Troubleshooting

### The BUSY Bar cannot be reached

- Check the USB cable or Wi-Fi connection.
- Confirm the BUSY Bar IP address.
- For Wi-Fi, enable HTTP API access on the BUSY Bar.
- Try the USB address `10.0.4.20`.

### The display says `OFFLINE`

- Try pinging a different target.
- Check whether the target blocks ICMP ping requests.
- Try your router address to separate local-network problems from internet
  connectivity problems.

### The Wi-Fi password is rejected

Use the BUSY Bar's local HTTP API access password. It is different from a BUSY
cloud API token. The password is sent to the BUSY Bar and is not saved by this
app.

### `ping` is not found

Install or enable the operating system's standard `ping` command, then restart
the app.

## Files

- `ping_monitor.py` — the complete app
- `requirements.txt` — Python dependency
- `Start Here` — macOS and Windows launchers
