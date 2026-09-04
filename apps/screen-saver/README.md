# Screen Saver for BUSY Bar

Screen Saver cycles through various pixel art scenes on your BUSY Bar front
display (72×16 RGB LED matrix). It includes a built-in collection of retro
pixel-art scenes and a powerful **Scene Generator** to create new scenes or
convert your own photos and GIFs.

## Features

- **Scene cycling**: Automatically rotates through static images and animated
  scenes from the `scenes/` folder.
- **Dial controls**: Turn the BUSY Bar rotary dial clockwise to jump to the next
  scene or counter-clockwise to go back.
- **Pause & freeze**: Press the **OK** button on the BUSY Bar to pause on your
  favorite scene; press again to resume cycling.
- **Smart image fitting**: Drop any image (JPG, PNG, WebP) of any size into
  `scenes/` — the app automatically fits, crops, and optimizes it for the 72×16
  display.
- **Animated scenes support**: Plays animated frame folders or looping GIFs at a
  smooth frame rate.
- **Scene Generator tool**: Create new procedural pixel art scenes (synthwave,
  matrix rain, cozy fireplace, aquarium, starfield, cyberpunk city, and more) or
  convert desktop images with contrast optimization and dithering.

## What you need

- A BUSY Bar with current release firmware
- Windows, macOS, or Linux
- Python 3.10 or newer
- A USB connection (`10.0.4.20`) or the BUSY Bar's Wi-Fi IP address

## Quick start with launchers

Open the `Start Here` folder and double-click:

- **To start the screen saver**:
  - Windows: `Windows - Double-click to Start.bat`
  - macOS: `macOS - Double-click to Start.command`
- **To generate or convert new scenes**:
  - Windows: `Windows - Double-click to Generate Scenes.bat`
  - macOS: `macOS - Double-click to Generate Scenes.command`

The launcher creates a private Python environment and installs required
dependencies automatically the first time it runs.

## Hardware controls on your BUSY Bar

| Control | Action |
|---------|--------|
| **Turn Dial Clockwise** | Skip immediately to the next scene |
| **Turn Dial Counter-Clockwise** | Go back to the previous scene |
| **Press OK Button** | Lock on the current scene (animation loops continue playing indefinitely; press again to resume cycling) |
| **Flip Mode Switch** | Exit the screen saver cleanly |

## Configuration (`.env`)

To customize settings permanently, copy `.env.example` to `.env` in this folder:

```text
BUSYBAR_IP=10.0.4.20
BUSYBAR_PASSWORD=
SCREENSAVER_INTERVAL=10
SCREENSAVER_SHUFFLE=true
SCREENSAVER_FPS=4
```

- `BUSYBAR_IP`: Defaults to `10.0.4.20` for USB. For Wi-Fi, enter your bar's IP
  address.
- `BUSYBAR_PASSWORD`: Set this if your BUSY Bar Wi-Fi HTTP API has password
  protection enabled.
- `SCREENSAVER_INTERVAL`: Number of seconds to show each scene (default: `10`).
- `SCREENSAVER_SHUFFLE`: `true` for random shuffle, `false` for alphabetical
  folder order.
- `SCREENSAVER_FPS`: Frame rate for animated scenes (default: `4` fps).

Command-line flags override `.env` settings.

## Default scenes included

The app comes pre-packaged with 9 ready-to-enjoy animated pixel art scenes in the `scenes/` folder:

- **aquarium** — Swimming tropical clownfish and ascending bubbles
- **aurora** — Shimmering northern lights over snowy pine mountains
- **cyberpunk_city** — Night skyline with lit windows, blinking beacons, and moon
- **fireplace** — Cozy campfire with dancing embers and flickering flames
- **lava_lamp** — Flowing retro metaball liquid blobs
- **matrix** — Cascading green digital rain code
- **pacman** — Classic arcade scene with Pac-Man eating dots chased by ghosts
- **rainbow_wave** — Demoscene plasma wave cycling vibrant RGB hues
- **synthwave** — 80s outrun horizon with neon sunset and perspective grid

*(Additional optional presets like `starfield`, `game_of_life`, and `sunset_beach` can be generated anytime with the Scene Generator tool.)*

## How to delete scenes you don't like

You can freely remove any scenes you don't want to see:

1. **Using File Explorer (Windows) or Finder (macOS)**:
   - Open the `apps/screen-saver/scenes/` folder.
   - Select the folder or image file for any scene you don't want (e.g. `pacman/` or `lava_lamp/`).
   - Press **Delete** or move it to the Recycle Bin / Trash.
2. **Using the terminal**:
   - On Windows (PowerShell):
     ```powershell
     Remove-Item -Recurse -Force "apps/screen-saver/scenes/pacman"
     ```
   - On macOS / Linux:
     ```bash
     rm -rf apps/screen-saver/scenes/pacman
     ```

Next time the Screen Saver starts or cycles, the deleted scenes will simply be skipped.

## Adding your own custom scenes

You can easily add new scenes to the screen saver using any of the following methods.

### Method 1: Drop files directly into `scenes/` (Simplest)

Simply drag and drop your files into the `apps/screen-saver/scenes/` folder:

- **Static Images** (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`):
  - Drop any picture directly into `scenes/`.
  - The app will automatically detect it, center-crop and resize it to 72×16, and optimize contrast for the LED matrix.
  - *Example*: Drop in `my_wallpaper.jpg` -> appears as a scene automatically.
- **Animated GIFs** (`.gif`):
  - Drop any animated GIF directly into `scenes/`.
  - The app will automatically unpack the frames, resize them to 72×16, and loop them smoothly during playback.
  - *Example*: Drop in `dancing_cat.gif` -> loops smoothly as an animated scene.
- **Multi-Frame Folders** (Custom frame sequence):
  - Create a new folder inside `scenes/`, for example `scenes/cool_animation/`.
  - Put numbered PNG frames inside it: `000.png`, `001.png`, `002.png`, etc.
  - The app will play all frames in order as a looping animation.

> [!TIP]
> **Dynamic Discovery**: If you drop a new picture or folder into `scenes/` while the screen saver is already running, it automatically detects and adds it to the rotation on the next cycle—no need to restart the app!

### Method 2: Convert images with the Scene Generator

If you want fine-grained control over how an image is cropped, enhanced, or dithered before adding it to your screen saver:

1. **Using the double-click launcher**:
   - Open `Start Here/` and run `Windows - Double-click to Generate Scenes.bat` (or `macOS - Double-click to Generate Scenes.command`).
   - Select **4. Convert an Image or GIF File** and type/paste the path to your file.
2. **Using the command line**:
   - Standard conversion (smart crop & LED contrast boost):
     ```bash
     python generate_scenes.py --convert "C:\path\to\my_photo.jpg"
     ```
   - Convert with retro Floyd-Steinberg dithering:
     ```bash
     python generate_scenes.py --convert "C:\path\to\my_photo.jpg" --dither
     ```
   - Fit entire image with black letterbox borders instead of cropping:
     ```bash
     python generate_scenes.py --convert "C:\path\to\logo.png" --mode fit
     ```
   - Convert an entire folder of photos at once:
     ```bash
     python generate_scenes.py --convert-folder "C:\Users\username\Pictures\Screensaver"
     ```

### Method 3: Generate the optional extra presets

If you'd like to try the presets that were excluded from the default set (`starfield`, `game_of_life`, `sunset_beach`):

```bash
# Generate as smooth 16-frame animations:
python generate_scenes.py --preset starfield --animated
python generate_scenes.py --preset game_of_life --animated
python generate_scenes.py --preset sunset_beach --animated

# Or generate as single static images:
python generate_scenes.py --preset starfield
```

### Design tips for 72×16 LED displays

- **Native Resolution**: The front display is exactly **72 pixels wide by 16 pixels high** (aspect ratio 4.5 : 1). Very wide panoramic images crop best.
- **Contrast & Brightness**: RGB LEDs look best with high contrast and dark/black backgrounds. High-contrast pixel art, neon colors, and glowing outlines look stunning.
- **Pixel Art Assets**: If you download pixel art from sites like [Lospec](https://lospec.com/) or [OpenGameArt](https://opengameart.org/), 16px-tall sprite sheets and panoramas look exceptionally crisp on the BUSY Bar.


## Scene Generator tool (`generate_scenes.py`)

The included `generate_scenes.py` script lets you generate procedural pixel-art
scenes and convert external images.

### Interactive wizard

Run the interactive wizard via the launcher or command line:

```bash
python generate_scenes.py --interactive
```

Follow the on-screen menu to generate presets or convert pictures.

### Command-line generation

Generate all 12 default presets:

```bash
python generate_scenes.py --all
```

Generate specific presets as smooth multi-frame animations (16 frames):

```bash
python generate_scenes.py --preset synthwave --preset fireplace --animated
```

Available procedural presets:
- `synthwave` — 80s outrun horizon with neon sunset and perspective grid
- `matrix` — Cascading green digital rain code
- `fireplace` — Cozy fireplace with dancing embers and flame particles
- `aquarium` — Deep sea reef with swimming clownfish and rising bubbles
- `starfield` — Deep space stars, twinkling lights, and shooting stars
- `cyberpunk_city` — Skyscraper skyline with lit windows, blinking beacons, and neon signs
- `aurora` — Waving emerald northern lights over snowy pine mountains
- `game_of_life` — Conway's Game of Life evolving colony
- `pacman` — Retro arcade maze with Pac-Man eating dots chased by ghosts
- `lava_lamp` — Flowing retro lava lamp metaball blobs
- `sunset_beach` — Palm tree silhouette against sunset and shimmering waves
- `rainbow_wave` — Demoscene sine plasma wave cycling RGB hues

### Converting your own photos or wallpapers

Convert any image or photo to an optimized 72×16 scene:

```bash
python generate_scenes.py --convert my_picture.jpg
```

Convert with Floyd-Steinberg dithering:

```bash
python generate_scenes.py --convert my_picture.jpg --dither
```

Convert all images in a folder:

```bash
python generate_scenes.py --convert-folder "C:\Users\username\Pictures"
```

## Running manually from command line

```bash
# In the apps/screen-saver directory:
python -m pip install -r requirements.txt
python screen_saver.py

# Custom interval and Wi-Fi host:
python screen_saver.py --host 192.168.1.50 --interval 15 --no-shuffle
```

## Stopping the app

Press `Ctrl+C` in the terminal or flip the BUSY Bar mode switch. The app
automatically clears the display and deletes uploaded temporary assets.

## Troubleshooting

### BUSY Bar cannot be reached
- If connected via USB, make sure the cable is securely plugged in and the USB
  interface `10.0.4.20` is responsive.
- If using Wi-Fi, ensure your computer and BUSY Bar are on the same local
  network and that HTTP API access is enabled in the BUSY Bar web UI.

### Display is busy
If another app (e.g. Social Battery or Ping Monitor) is actively holding the
display, Screen Saver will notify you and retry every 10 seconds. Press `Ctrl+C`
or Back on the other app to release the display.

### Wi-Fi password prompt
If your BUSY Bar requires authentication, set `BUSYBAR_PASSWORD=your_password`
in `.env` or enter it when prompted in the terminal.
