# Launcher: Clock app and notes for the Waveshare ESP-Brookesia firmware

The Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5 ships with a phone-style launcher
(ESP-Brookesia on LVGL). Waveshare publishes its source under Apache-2.0:
<https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-3.5> (`firmware/brookesia`).
This folder adds to it; none of Waveshare's code is copied here except as patches.

| Item | What it is |
| --- | --- |
| [`ADDING_APPS.md`](ADDING_APPS.md) | How to add an app to the launcher, plus the build recipe and the traps I hit |
| [`ClockApp/`](ClockApp/) | A Clock app: analog dial, digital time, date and Open-Meteo weather (portrait, LVGL) |
| [`patches/brookesia-launcher.patch`](patches/brookesia-launcher.patch) | Edits to `firmware/brookesia`: Clock first on the home screen, fixed Wi-Fi, Pacific time and SNTP, Xiaozhi font step removed, 36 px font |
| [`user_config.h.example`](user_config.h.example) | Wi-Fi name, password and time zone for the patch (copy, fill in, never commit) |
| [`patches/camera-example-09.md`](patches/camera-example-09.md) | Three fixes for Waveshare's standalone camera example `09_video_lcd_display` on ESP-IDF 5.5.6, with [`camera-example-09-main.patch`](patches/camera-example-09-main.patch) |

Tested on a board with an ESP32-P4 rev v3.2 and ESP-IDF 5.5.6.

## Build the launcher with the Clock app and without Settings/AIChats

1. Clone Waveshare's repo and go to `firmware/brookesia`. Copy this folder's
   `ClockApp/` into its `components/`.
2. Apply the patch from the repo root: `git apply <path>/launcher/patches/brookesia-launcher.patch`.
3. Copy `user_config.h.example` to `firmware/brookesia/main/user_config.h` and
   fill it in. Copy `components/ClockApp/clock_config.h.example` to
   `clock_config.h` in the same folder and set your location (the build fails
   without it). Add both paths to `.git/info/exclude` so they are never committed.
4. Take the Xiaozhi app and the Settings app UI out of the build (the patch
   assumes you did; details and reasons in `ADDING_APPS.md`):

       cd firmware/brookesia
       mkdir -p disabled/Settings
       git mv components/XiaozhiApp disabled/XiaozhiApp
       git mv components/Settings/Settings.cpp components/Settings/Settings.hpp \
              components/Settings/ui components/Settings/assets disabled/Settings/
       mv spiffs/xiaozhi disabled/xiaozhi-spiffs

5. Build and flash as described in `ADDING_APPS.md` (note the
   `IDF_EXTRA_ACTIONS_PATH` step for `idf.py bmgr`).

If you want to keep Settings and AIChats, skip step 4 and the Wi-Fi and SNTP
parts of the patch; the Clock app itself only needs a connected Wi-Fi.

## Clock app notes

- Location for the weather is in `ClockApp/clock_config.h` (made from the `.example`); the time zone comes
  from `TZ_POSIX` in `user_config.h`.
- Not carried over from the standalone clock in `../p4clock`: night palette and
  touch-to-flip. Temperatures print as `84 F` because the built-in Montserrat
  fonts have no degree sign.
- `ClockApp/assets/gen_icon.py` regenerates the 112x112 icon (needs Pillow).
