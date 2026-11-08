# P4 Clock Installer

A Windows program that installs the clock and weather display on a Waveshare
ESP32-P4-WIFI6-Touch-LCD-3.5. You give it a location (a U.S. street address, or a
latitude and longitude anywhere in the world), a Wi-Fi network name and its password;
it does the rest.

## Using it (for the person receiving the .exe)

1. Plug the board into the PC with a USB-C cable, using the **UART-C** port (the
   board's other USB-C port will not program it). If no port appears,
   install the "CH343" USB serial driver from WCH (wch-ic.com).
2. Run `P4ClockInstaller.exe`. Windows may warn about an unknown publisher because the
   program is not code-signed: choose "More info", then "Run anyway".
3. Enter the location, the Wi-Fi name and password, check the board in the list, and
   click **Install**. The location can be:
   - a U.S. street address, for example `123 Main St, Springfield, IL 62701`, or
   - a latitude and longitude, **latitude first**, for example `51.5074, -0.1278`.
     South and west are negative (`-33.8688, 151.2093`), or add letters
     (`33.8688 S, 151.2093 E`). Any place on Earth works; the coordinates of a town
     can be copied from an online map.
4. Check the summary it shows (place, name on the clock, time zone) and confirm.
   Writing takes about 30 seconds; the clock restarts by itself and shows the time in about 15.

To change the Wi-Fi or the location later, run it again and tick "Only change the settings".

Good to know:
- The board uses **2.4 GHz** Wi-Fi only, with a WPA2/WPA3 password (8 to 63 characters).
- A street address is sent once to the U.S. Census geocoder. The coordinates (either typed
  or found that way) are sent to Open-Meteo to find the time zone. The clock stores only the
  coordinates, a short place name and the time zone, never a street address. For a coordinate
  entry the clock shows the coordinates (for example `51.51 N, 0.13 W`) as the place name.
  The Wi-Fi password is stored in the board's flash in plain text.
- **The clock shows temperatures in degrees Fahrenheit and wind in mph everywhere.** There is
  no metric option yet.
- The clock starts by itself every time the board is reset or powered up.

## How it works

`p4clock` reads its settings from a 4 KB `config` flash partition (a JSON block at 0x187000);
the compile-time values in `p4clock/main/user_config.h` are only the fallback. The installer
writes the program (bootloader, partition table, app) and that settings block with `esptool`.

The time zone's daylight-saving rule is read from the IANA time zone database (the `tzdata`
Python package, bundled in the `.exe`): each zone's file ends with its rule in the POSIX
format the clock uses. All 598 zones in tzdata 2026f were run through the board's C library
and compared with Python's own time zone engine at four dates in 2027; 596 agree. Two
differences remain: both names of Cuba's zone, where the clock follows the rule that tzdata
publishes but Python's transition table differs in January 2027. Greenland's rule contains a
negative time that the board's C library cannot parse, so the installer rewrites it (a
one-hour shift of the March changeover on a single night).

## Building the installer (maintainer)

Needs ESP-IDF 5.5.6 at `C:\Espressif`, the `p4clock` project with its `font_data.c`
(generated from Segoe UI on a Windows PC), and a Python 3 with tkinter:

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    powershell -ExecutionPolicy Bypass -File package.ps1

`package.ps1` builds the firmware in its own folder with **placeholder** settings
(`installer_defaults.h`), copies the three binaries to `firmware\`, runs
`check_no_secrets.py` (it fails if your real Wi-Fi name or password from `user_config.h`
is inside the binaries) and then makes `dist\P4ClockInstaller.exe` with PyInstaller.
PyInstaller cannot overwrite an `.exe` that is running; close it first.

The window can also be skipped for testing:

    set P4_PASS=your-wifi-password
    python installer.py --location "123 Main St, City, ST 12345" --ssid MyNetwork --password-env P4_PASS [--settings-only] [--port COM12]
    python installer.py --location "51.5074, -0.1278" --ssid MyNetwork --password-env P4_PASS

(`--address` is accepted as another name for `--location`.)

## Limits

- Street addresses work for the U.S. only (Census geocoder). Elsewhere, enter coordinates.
- Fahrenheit and mph only (see above).
- The `.exe` and `firmware\` contain the Segoe UI font data from the clock's generated
  `font_data.c`. Keep them private; do not post them publicly.
