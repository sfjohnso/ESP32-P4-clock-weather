# Adding apps to the Waveshare ESP32-P4 launcher

Notes from adding a Clock app to the phone-style launcher that ships on the
Waveshare **ESP32-P4-WIFI6-Touch-LCD-3.5** (320x480 portrait). Everything here
was done on 2026-11-07 with ESP-IDF 5.5.6 and checked on the real board unless
a line says otherwise.

## Where the launcher comes from

Waveshare publishes the source of the factory firmware (Apache-2.0):

    https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-3.5   ->  firmware/brookesia/

It is an ESP-Brookesia "phone" UI on LVGL 9.5. Each app is a component under
`firmware/brookesia/components/`. Stock apps: Camera, VideoPlayer, MusicPlayer,
SpecAnalyzer, DrawPanel, Calculator, Squareline, Settings, AIChats (Xiaozhi).

## Build and flash

From `firmware/brookesia`, in an ESP-IDF 5.5 shell:

    idf.py set-target esp32p4
    # Without this variable `idf.py bmgr` has no -b option (the extension is not loaded):
    $env:IDF_EXTRA_ACTIONS_PATH = (Resolve-Path managed_components\espressif__esp_board_manager).Path
    idf.py bmgr -b esp32_p4_wifi6_touch_lcd_3_5
    idf.py build
    idf.py -p COM12 flash        # full flash, ~2 min (writes a 6 MB SPIFFS image)

- The first build downloads the managed components (a few hundred MB) and takes
  a long time. Changing `sdkconfig` (for example enabling a font) rebuilds nearly
  everything again, about 10 minutes.
- The app partition is 8 MB. The stock build is 4.8 MB; with the Clock app, 5.0 MB.
- **Console baud rate is 2,000,000**, not 115200. Open the serial port at 2 Mbaud
  to see the log.

## Anatomy of an app

An app is one component directory. Nothing outside it has to change for the app
to be built and registered:

- `main/CMakeLists.txt` globs every `components/*/CMakeLists.txt`, so a new
  directory is picked up automatically.
- The app registers itself with `ESP_UTILS_REGISTER_PLUGIN_WITH_CONSTRUCTOR`;
  `main.cpp` installs everything found in the registry.

Layout (see `ClockApp/` in this repo as a worked example):

    components/MyApp/
        CMakeLists.txt     copy the Calculator/ClockApp one; keep WHOLE_ARCHIVE
        MyApp.hpp / .cpp
        assets/img_app_myapp.c     112x112 icon, LVGL ARGB8888

### CMakeLists.txt

Copy `components/brookesia_app_calculator/CMakeLists.txt` and add whatever
components your code needs under `REQUIRES` (this app used `board`,
`esp_http_client`, `esp-tls`, `mbedtls`, `json`, `esp_timer`).
**Keep `WHOLE_ARCHIVE`.** Without it the linker drops the static registrar and
the app silently never appears.

### The class

Derive from `esp_brookesia::systems::phone::App` and implement
`run() / back() / close() / init() / deinit()`:

- Constructor: `App("Name", &img_app_icon, true, use_status_bar, use_navigation_bar)`.
  The existing apps pass `false, false`, which gives the app the whole 320x480 screen.
- `run()` builds the UI on `lv_screen_active()`. `getVisualArea()` gives the
  usable size. Call `lv_obj_clean(lv_screen_active())` first.
- `back()` should call `notifyCoreClosed()`; that is how the swipe-back gesture
  leaves the app.
- `close()` is where you stop anything you started in `run()`.
- Use the singleton pattern from Calculator (`requestInstance()`), and register
  with a shared_ptr whose deleter does nothing, because the app owns itself:

      ESP_UTILS_REGISTER_PLUGIN_WITH_CONSTRUCTOR(systems::base::App, MyApp, "My App", []()
      {
          return std::shared_ptr<MyApp>(MyApp::requestInstance(), [](MyApp *) {});
      })

### Threading

`run()` and `close()` are called from LVGL's context (the existing apps call
`lv_*` functions in them without taking a lock; the Clock app does the same and
works). That is an observation, not something I found documented. For anything
off the LVGL thread:

- Do network and other slow work in a FreeRTOS task, never in `run()` or in an
  LVGL timer callback.
- Don't touch LVGL objects from that task. Hand results over through a mutex-
  protected struct plus a version counter, and let an `lv_timer` on the LVGL
  side notice the new version and update the labels. The Clock app does this.
- Delete any `lv_timer` you created in `close()`. The screen's objects are
  dropped with the screen.

### Icon

112x112 ARGB8888 as a C file (bytes are B, G, R, A per pixel) plus an
`lv_image_dsc_t` named like the symbol you pass to the constructor, declared in
the `.cpp` with `LV_IMG_DECLARE(img_app_myapp);`.
`ClockApp/assets/gen_icon.py` generates one with Pillow (use a normal Python,
not the ESP-IDF shell's, which has no Pillow).

### Home-screen order

`main/main.cpp` has `BOOT_APP_GROUPS`. Apps listed there are installed in that
order; registered apps that are *not* listed are installed after the last group.
Put your app's name (the string you registered) in the group you want.

## LVGL fonts

Only Montserrat 12, 14, 16, 20 are compiled in. To use another size, enable it
in **both** `sdkconfig.defaults` (`CONFIG_LV_FONT_MONTSERRAT_36=y`) and the
existing `sdkconfig`; editing only the defaults file does nothing once an
`sdkconfig` exists. Then add `LV_FONT_DECLARE(lv_font_montserrat_36);` in your
file.

The Montserrat fonts have no degree sign, so the Clock app prints temperatures
as `84 F`.

## Wi-Fi and the clock

- The board's Wi-Fi is the ESP32-C6 over SDIO. The launcher's Wi-Fi service is
  `board_wifi_service_*` (`board_wifi.h`, component `board`).
  `board_wifi_service_is_connected()` is the check an app should gate network
  work on.
- **The stock Settings app was the only code that started SNTP**, with
  `ntp.aliyun.com` and the time zone `CST-8`. If you remove Settings you must
  start SNTP and set `TZ` yourself. The patch in this repo does both in
  `main.cpp`, using `pool.ntp.org` and a POSIX time zone from `user_config.h`.
- Hard-coded network: `board_wifi_service_request_connect(SSID, PASS, 10, 0)`
  after `board_wifi_service_init()`. Put the credentials in
  `main/user_config.h`, which must never be committed
  (see `user_config.h.example`).

## Removing stock apps

To drop an app, `git mv` its component directory out of `components/` (this
repo's patch uses a `disabled/` folder). Two traps:

- The Settings component also holds `SettingsStorage` (brightness and volume),
  which `main.cpp` uses at boot. Move only `Settings.cpp/.hpp`, `ui/` and
  `assets/` and keep `SettingsStorage.*`.
- `main/CMakeLists.txt` looks up the Xiaozhi fonts component and copies a font
  into the SPIFFS source folder. Remove that block along with the app, or
  CMake fails with "Failed to resolve component '78__xiaozhi-fonts'". Also move
  `spiffs/xiaozhi/` out so it is not packed into the 6 MB image.
- Removing AIChats drops ESP-SR and the Xiaozhi packages from the download.

## Open questions

- The launcher called the Clock app's `run()` once at boot (its weather fetch
  appeared in the log about 13 s after power-up, with nobody touching the
  screen). I did not find out why. It is harmless here because the weather task
  starts once and keeps running.
- The Camera app works unmodified on IDF 5.5.6 (it uses `esp_video` 2.5.0).
  The separate standalone example `09_video_lcd_display` needed three fixes;
  see `patches/camera-example-09.md`.
