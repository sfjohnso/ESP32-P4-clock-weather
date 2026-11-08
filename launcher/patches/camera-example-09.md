# Fixes for Waveshare's `09_video_lcd_display` camera example on ESP-IDF 5.5.6

Waveshare's CI only compiles this example (IDF 5.5.5 and 6.0.2); on a real
board with ESP-IDF 5.5.6 and `esp_video` 0.8.0 it needed three fixes. With them
the OV5647 shows a clean, upright, wide-angle live picture (1280x960 binned
mode, the default). This is the standalone example, **not** the launcher's
Camera app, which worked unmodified.

## 1. Stream would not start: `failed to configure format conversion`

Symptom: `CSI: esp_cam_new_csi_ctlr(207): failed to configure format conversion`,
then an abort loop.

Cause: the CSI bridge in IDF 5.5.6 can only convert RGB/YUV formats, never RAW,
but `esp_video` asked it to convert RAW to RGB565. The ISP does that
conversion, so the bridge should just pass the data through, described in the
format the ISP hands it.

Fix, in the managed component
`managed_components/espressif__esp_video/src/device/esp_video_csi_device.c`,
function `csi_video_start`:

    // was: .input_data_color_type = csi_video->state.in_color,
    //      .output_data_color_type = csi_video->state.out_color,
    .input_data_color_type = csi_video->state.bypass_isp ? csi_video->state.in_color : csi_video->state.out_color,
    .output_data_color_type = csi_video->state.out_color,

This file is downloaded by the component manager, so the edit is lost if the
dependencies are fetched again. A cleaner home for it is a local override of the
component. (I tried leaving the input as RAW and passing RAW through, which also
started the stream; I did not establish which variant matters for the picture,
since another bug, below, was hiding it. The version above is the one the final
working picture was taken with.)

## 2. Jittery, repeated bands: the LCD copy loop reused a buffer too early

Cause: `main.c` sends each frame to the LCD in stripes through one shared DMA
buffer and passes `is_last_block` as the `wait` argument of
`esp_lv_adapter_dummy_draw_blit()`. With `wait == false` the call returns as
soon as the transfer is queued, so the next stripe's copy overwrites the buffer
while the previous stripe is still being sent.

Fix: pass `true` for every stripe (`camera-example-09-main.patch`).

## 3. Upside-down picture

The PPA flags appear to act opposite to their names on this setup. With
`mirror_x = 1, mirror_y = 0` the picture was flipped vertically; with
`mirror_x = 0, mirror_y = 0` it is upright (also in `camera-example-09-main.patch`).

## Also in the tested build (probably not required)

- Camera buffers raised from 2 to 3 (in the patch).
- `CONFIG_ESP_VIDEO_DISABLE_MIPI_CSI_DRIVER_BACKUP_BUFFER` turned off in
  `sdkconfig` while debugging. I never re-tested without it, so I cannot say it
  is needed.

## Not fixed / caveats

- Colour is the ISP's default; no tuning was done.
- The first theory for the bands was a CSI DMA size problem. Experiments ruled
  it out, and it is the reason the patch in section 1 went through two
  versions.
