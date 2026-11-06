# Clock and weather for the Waveshare ESP32-P4-SIFI6-Touch-LCD-3.5

A landscape (480x320) clock and weather display for the Waveshare
ESP32-P4-SIFI6-Touch-LCD-3.5 board, written by Steve Johnson together with Claude,
an AI coding assistant. Steve chose the design and checked everything on the real
board; Claude wrote the code in small steps that were verified on the hardware.

The left half shows an analog dial with a smooth second hand, the digital time and
the date. The right half shows the current weather for your location: condition,
temperature, feels-like, humidity and wind. Between 22:00 and 07:00 local time every
color switches to a muted red so the screen is easy on the eyes at night. It starts
by itself at power-up (about 12 seconds to a full display) and refreshes the weather
every 30 minutes.

| Folder | What it is |
|---|---|
| [p4clock](p4clock) | The ESP-IDF project |

## Before you build: set your network, location and time zone

All personal settings live in one file that is **not** stored in git.

1. In `p4clock/main/`, copy `user_config.h.example` to `user_config.h`.
2. Edit `user_config.h`:

| Setting | What to put there |
|---|---|
| `WIFI_SSID` | The name of your Wi-Fi network, in quotes. |
| `WIFI_PASS` | The network password, in quotes. It is compiled into the firmware, so changing networks means rebuilding and reflashing. |
| `LOCATION_LABEL` | The text shown above the weather, e.g. `"NEWBURY PARK, CA \267 91320"`. Plain text; `\267` is a middle dot. This is only a caption and does not select the weather. |
| `LAT`, `LON` | Latitude and longitude of your location in decimal degrees, as quoted strings (south and west are negative). This **is** what selects the weather. |
| `TZ_POSIX` | Your time zone, including its daylight-saving rule (examples below). |

### Choosing a location (zip code to latitude/longitude)

The weather service (Open-Meteo) takes coordinates, not a zip code. Two ways to get them:

* **Search by postal code.** Open this in a browser, replacing `91320` with your
  code: `https://geocoding-api.open-meteo.com/v1/search?name=91320&count=5`.
  Postal codes are not unique worldwide (91320 is also a town in France), so look
  through the results for the right country and copy its `latitude` and `longitude`.
* **Use a map.** In an online map, right-click your spot and copy the coordinates.

Four decimal places (about 10 m) are plenty. Example: `#define LAT "34.1872"` and
`#define LON "-118.9114"`.

### Time zone

`TZ_POSIX` is a POSIX time-zone string. The US ones:

| Zone | `TZ_POSIX` |
|---|---|
| Pacific | `"PST8PDT,M3.2.0,M11.1.0"` |
| Mountain | `"MST7MDT,M3.2.0,M11.1.0"` |
| Central | `"CST6CDT,M3.2.0,M11.1.0"` |
| Eastern | `"EST5EDT,M3.2.0,M11.1.0"` |
| Arizona (no daylight saving) | `"MST7"` |

For other countries, look your zone up in a POSIX TZ list (for example the table at
https://github.com/nayarsystems/posix_tz_db). The label under the date (PST, PDT, ...)
comes from this string. The night colors begin at 22:00 and end at 07:00 local time;
change `NIGHT_START_HOUR` / `NIGHT_END_HOUR` at the top of `main.c` if you like.
Temperatures are shown in Fahrenheit and wind in mph (set in the request URL in
`fetch_weather()` in `main.c`).

## Build and flash

You need ESP-IDF 5.5 (developed and tested with 5.5.6), Python with Pillow
(`pip install pillow`), and the board connected by USB.

1. **Generate the fonts.** The text is drawn from pre-rendered glyph bitmaps. The
   generated `main/font_data.c` is not stored in git because the original design
   used Microsoft's Segoe UI, which is not redistributable. From `p4clock/`:

       python tools/gen_fonts.py

   On Windows this uses the Segoe UI files already installed. On any other system, or
   to use a different look, pass two TrueType files, a regular and a semibold one:

       python tools/gen_fonts.py --regular /path/Regular.ttf --semibold /path/Semibold.ttf

   The spacing was tuned for Segoe UI; other fonts work but might need small tweaks.
2. **Build and flash** from an ESP-IDF shell, in `p4clock/` (replace `COM12` with the
   board's USB serial port):

       idf.py build
       idf.py -p COM12 flash

   The first build downloads the Wi-Fi components (`esp_wifi_remote`, `esp_hosted`)
   automatically. To watch the log: `idf.py -p COM12 monitor`.

The screen is cleared at power-up, shows "Connecting to Wi-Fi..." and then
"Setting the clock...", and fills in once the network time and the weather arrive.
If the router is down it keeps retrying. If one weather request fails it keeps the
old reading and tries again after a minute. The "weather updated N min ago" line at
the bottom tells you how fresh the data is.

If the picture is upside-down, it should flip by changing the display rotation byte in `lcd_init()`
(`cmd(0x36, ... 0x28 ...)`) from `0x28` to `0xE8`.

## Hardware notes

* **Display:** ST7796, 320x480, SPI at 40 MHz (MOSI 20, SCLK 21, CS 23, DC 26,
  RST 27, backlight 28 as a plain on/off pin). Pixel data is RGB565 and must be
  byte-swapped for SPI. This program rotates it to landscape with MADCTL `0x28`.
* **Wi-Fi:** the ESP32-P4 has no radio of its own; Wi-Fi is the ESP32-C6 on the
  board, reached over SDIO through `esp_hosted` and `esp_wifi_remote`. The default
  SDIO pins are correct for this board (slot 1: CLK 18, CMD 19, D0-D3 14-17, C6 reset 54).
* **The `esp_hosted` version matters.** `idf_component.yml` pins `esp_hosted` to
  `2.0.17`. The newest release (3.1.0) joins the network but fails on real traffic
  (DNS and HTTPS time out with "SDIO RX read exceeds staging target") against the
  older ESP32-C6 firmware that ships on the board. Do not unpin it unless you have
  updated the C6 firmware.
* **Touch** (not used by this program): FT6336-style controller at I2C address 0x38
  (SDA 7, SCL 8). Its reset line (GPIO 29) must be driven high, and its interrupt is GPIO 50.
* **Flash:** `sdkconfig.defaults` sets 16 MB flash and the large single-app partition
  table; the application is about 1 MB.

## License

MIT, see [LICENSE](LICENSE).
