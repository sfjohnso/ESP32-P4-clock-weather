// Voice launcher for the Waveshare ESP32-P4 3.5" board (a launcher app).
//
// Say the wake word "Hi ESP", then "open <app name>" (for example "open life" or "open music"). The board then returns
// to the launcher and starts that app. Recognition runs on the board with Espressif's ESP-SR (WakeNet wake word,
// MultiNet command recognition); the models are read from the SD card (/sdcard/srmodels).
//
// Audio: ES8311 codec, analog microphone, 16 kHz mono (left slot).  Display, touch: as in the other apps.
#include <dirent.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/i2s_std.h"
#include "driver/ledc.h"
#include "driver/sdmmc_host.h"
#include "driver/spi_master.h"
#include "esp_afe_config.h"
#include "esp_afe_sr_models.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_log.h"
#include "esp_mn_iface.h"
#include "esp_mn_models.h"
#include "esp_mn_speech_commands.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_vfs_fat.h"
#include "esp_wn_iface.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "model_path.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sd_pwr_ctrl_by_on_chip_ldo.h"
#include "sdmmc_cmd.h"
#include "font_8x16.h"

static const char *TAG = "voice";

#define LCD_W 480
#define LCD_H 320
#define FB_H 320
#define PIN_MOSI 20
#define PIN_SCLK 21
#define PIN_LCD_CS 23
#define PIN_LCD_DC 26
#define PIN_LCD_RST 27
#define PIN_LCD_BL 28
#define PIN_TP_RST 29
#define PIN_SDA 7
#define PIN_SCL 8
#define PIN_PA 53                           // speaker amplifier enable (kept off: this app only listens)
#define SPI_MHZ 80
#define CHUNK_PX 12800                      // 25,600 bytes per SPI transfer (a multiple of the cache line)
#define BACKLIGHT_PCT 80

#define FS 16000
#define APPS_DIR "/sdcard/apps"
#define MODEL_DIR "/sdcard/srmodels"
#define MAX_APPS 40
#define CMD_TIMEOUT_MS 6000

// RGB565 byte-swapped for the SPI wire
static inline uint16_t rgb565(int r, int g, int b)
{
    uint16_t v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
    return (v << 8) | (v >> 8);
}

// ===========================================================================
// Display (same as the Life app's)
// ===========================================================================
static esp_lcd_panel_io_handle_t lcd_io;
static SemaphoreHandle_t lcd_done;
static uint16_t *fb;                        // LCD_W x LCD_H, byte-swapped RGB565

static bool on_done(esp_lcd_panel_io_handle_t io, esp_lcd_panel_io_event_data_t *e, void *u)
{
    BaseType_t w = pdFALSE;
    xSemaphoreGiveFromISR(lcd_done, &w);
    return w == pdTRUE;
}

static void cmd(uint8_t c, const uint8_t *p, size_t n) { ESP_ERROR_CHECK(esp_lcd_panel_io_tx_param(lcd_io, c, p, n)); }

// Send screen rows y0 .. y1-1 from the frame buffer.
static void flush_rows(int y0, int y1)
{
    cmd(0x2A, (uint8_t[]){ 0, 0, (LCD_W - 1) >> 8, (LCD_W - 1) & 0xFF }, 4);
    cmd(0x2B, (uint8_t[]){ y0 >> 8, y0 & 0xFF, (y1 - 1) >> 8, (y1 - 1) & 0xFF }, 4);
    int total = (y1 - y0) * LCD_W, sent = 0, chunks = 0;
    uint16_t *p = fb + y0 * LCD_W;
    while (sent < total) {
        int n = total - sent < CHUNK_PX ? total - sent : CHUNK_PX;
        ESP_ERROR_CHECK(esp_lcd_panel_io_tx_color(lcd_io, sent ? 0x3C : 0x2C, p + sent, n * 2));
        sent += n;
        chunks++;
    }
    while (chunks--) xSemaphoreTake(lcd_done, portMAX_DELAY);
}

static void display_init(void)
{
    gpio_config_t o = { .pin_bit_mask = 1ULL << PIN_LCD_RST, .mode = GPIO_MODE_OUTPUT };
    gpio_config(&o);
    ledc_timer_config_t t = { .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_10_BIT, .timer_num = LEDC_TIMER_0,
                              .freq_hz = 5000, .clk_cfg = LEDC_AUTO_CLK };
    ESP_ERROR_CHECK(ledc_timer_config(&t));
    ledc_channel_config_t c = { .gpio_num = PIN_LCD_BL, .speed_mode = LEDC_LOW_SPEED_MODE, .channel = LEDC_CHANNEL_0,
                                .timer_sel = LEDC_TIMER_0, .duty = 0 };
    ESP_ERROR_CHECK(ledc_channel_config(&c));
    gpio_set_level(PIN_LCD_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(PIN_LCD_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(120));

    spi_bus_config_t bc = { .mosi_io_num = PIN_MOSI, .miso_io_num = -1, .sclk_io_num = PIN_SCLK,
                            .quadwp_io_num = -1, .quadhd_io_num = -1, .max_transfer_sz = CHUNK_PX * 2 };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bc, SPI_DMA_CH_AUTO));
    lcd_done = xSemaphoreCreateCounting(32, 0);
    esp_lcd_panel_io_spi_config_t ic = {
        .dc_gpio_num = PIN_LCD_DC, .cs_gpio_num = PIN_LCD_CS, .pclk_hz = SPI_MHZ * 1000 * 1000,
        .lcd_cmd_bits = 8, .lcd_param_bits = 8, .spi_mode = 0, .trans_queue_depth = 4, .on_color_trans_done = on_done,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &ic, &lcd_io));
    fb = heap_caps_aligned_alloc(128, LCD_W * FB_H * 2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);   // PSRAM: the speech models need the internal RAM
    assert(fb);
    memset(fb, 0, LCD_W * FB_H * 2);

    cmd(0x01, NULL, 0); vTaskDelay(pdMS_TO_TICKS(150));
    cmd(0x11, NULL, 0); vTaskDelay(pdMS_TO_TICKS(120));
    cmd(0xF0, (uint8_t[]){ 0xC3 }, 1); cmd(0xF0, (uint8_t[]){ 0x96 }, 1);
    cmd(0x36, (uint8_t[]){ 0x28 }, 1);             // landscape, BGR
    cmd(0x3A, (uint8_t[]){ 0x55 }, 1);             // 16 bits/pixel
    cmd(0xB4, (uint8_t[]){ 0x01 }, 1);
    cmd(0xF0, (uint8_t[]){ 0x3C }, 1); cmd(0xF0, (uint8_t[]){ 0x69 }, 1);
    cmd(0x21, NULL, 0);                            // inversion on (IPS panel)
    cmd(0x29, NULL, 0); vTaskDelay(pdMS_TO_TICKS(50));
    flush_rows(0, FB_H);                           // black before the backlight comes on
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 1023 * BACKLIGHT_PCT / 100);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

// ===========================================================================
// Touch (same as the Life app's); the I2C bus is shared with the codec
// ===========================================================================
static i2c_master_bus_handle_t i2c_bus;
static i2c_master_dev_handle_t touch_dev, es_dev;

static void touch_init(void)
{
    gpio_config_t o = { .pin_bit_mask = 1ULL << PIN_TP_RST, .mode = GPIO_MODE_OUTPUT };
    gpio_config(&o);
    gpio_set_level(PIN_TP_RST, 0);                 // reset is held low by a resistor until driven
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(PIN_TP_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(300));
    i2c_master_bus_config_t bc = { .i2c_port = I2C_NUM_0, .sda_io_num = PIN_SDA, .scl_io_num = PIN_SCL,
                                   .clk_source = I2C_CLK_SRC_DEFAULT, .glitch_ignore_cnt = 7, .flags.enable_internal_pullup = true };
    ESP_ERROR_CHECK(i2c_new_master_bus(&bc, &i2c_bus));
    i2c_device_config_t dc = { .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = 0x38, .scl_speed_hz = 400000 };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(i2c_bus, &dc, &touch_dev));
}

static bool touch_read(int *sx, int *sy)
{
    uint8_t reg = 0x02, b[5];
    if (i2c_master_transmit_receive(touch_dev, &reg, 1, b, sizeof b, 50) != ESP_OK) return false;
    int n = b[0] & 0x0F;
    if (n < 1 || n > 2) return false;
    int rx = ((b[1] & 0x0F) << 8) | b[2], ry = ((b[3] & 0x0F) << 8) | b[4];
    if (rx > 3000 || ry > 3000) return false;      // the chip reports 4095,4095 for a phantom point
    *sx = ry; *sy = LCD_H - 1 - rx;                // portrait controller -> landscape panel
    return true;
}

// ===========================================================================
// Drawing helpers on the frame buffer
// ===========================================================================
static void fill_rect(int x, int y, int w, int h, uint16_t c)
{
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > LCD_W) w = LCD_W - x;
    if (y + h > FB_H) h = FB_H - y;
    for (int j = y; j < y + h; j++)
        for (int i = x; i < x + w; i++) fb[j * LCD_W + i] = c;
}

static int text_width(const char *s, int k) { return (int)strlen(s) * 8 * k; }

static void draw_text(int x0, int y0, const char *s, int k, uint16_t col)
{
    for (int c = 0; s[c]; c++)
        for (int r = 0; r < 16; r++) {
            uint8_t bits = fontdata_8x16[(unsigned char)s[c] * 16 + r];
            for (int b = 0; b < 8; b++)
                if (bits & (0x80 >> b)) fill_rect(x0 + (c * 8 + b) * k, y0 + r * k, k, k, col);
        }
}

static void draw_text_c(int cx, int y0, const char *s, int k, uint16_t col) { draw_text(cx - text_width(s, k) / 2, y0, s, k, col); }

// ===========================================================================
// SD card (the speech models and the list of apps live there)
// ===========================================================================
static bool sd_mount(void)
{
    sd_pwr_ctrl_handle_t pwr = NULL;
    sd_pwr_ctrl_ldo_config_t ldo = { .ldo_chan_id = 4 };
    if (sd_pwr_ctrl_new_on_chip_ldo(&ldo, &pwr) != ESP_OK) return false;
    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_0;
    host.max_freq_khz = SDMMC_FREQ_HIGHSPEED;
    host.pwr_ctrl_handle = pwr;
    sdmmc_slot_config_t slot = SDMMC_SLOT_CONFIG_DEFAULT();
    slot.width = 4;
    slot.flags |= SDMMC_SLOT_FLAG_INTERNAL_PULLUP;
    slot.clk = 43; slot.cmd = 44; slot.d0 = 39; slot.d1 = 40; slot.d2 = 41; slot.d3 = 42;
    esp_vfs_fat_sdmmc_mount_config_t mc = { .format_if_mount_failed = false, .max_files = 6, .allocation_unit_size = 16 * 1024 };
    sdmmc_card_t *card;
    esp_err_t r = esp_vfs_fat_sdmmc_mount("/sdcard", &host, &slot, &mc, &card);
    if (r != ESP_OK) { ESP_LOGW(TAG, "SD mount failed: %s", esp_err_to_name(r)); return false; }
    return true;
}

// ===========================================================================
// Audio hardware: ES8311 microphone input, 16 kHz
// ===========================================================================
static i2s_chan_handle_t rx;
static int pga = 6;                         // microphone preamp, 0..10 in 3 dB steps

static void es_w(uint8_t reg, uint8_t val)
{
    uint8_t b[2] = { reg, val };
    esp_err_t r = i2c_master_transmit(es_dev, b, 2, 100);
    if (r != ESP_OK) ESP_LOGW(TAG, "codec write %02x failed: %s", reg, esp_err_to_name(r));
}

static void audio_init(void)
{
    i2c_device_config_t dc = { .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = 0x18, .scl_speed_hz = 100000 };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(i2c_bus, &dc, &es_dev));

    i2s_chan_config_t cc = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    cc.dma_desc_num = 8;
    cc.dma_frame_num = 512;
    ESP_ERROR_CHECK(i2s_new_channel(&cc, NULL, &rx));
    i2s_std_config_t sc = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(FS),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = { .mclk = 13, .bclk = 12, .ws = 10, .dout = I2S_GPIO_UNUSED, .din = 11 },
    };
    sc.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx, &sc));
    ESP_ERROR_CHECK(i2s_channel_enable(rx));
    vTaskDelay(pdMS_TO_TICKS(50));

    // ES8311 init for 256*fs MCLK (same sequence as the Sound Meter app; the dividers scale with fs)
    es_w(0x44, 0x08); es_w(0x44, 0x08);
    es_w(0x01, 0x30); es_w(0x02, 0x00); es_w(0x03, 0x10); es_w(0x16, 0x24);
    es_w(0x04, 0x10); es_w(0x05, 0x00); es_w(0x0B, 0x00); es_w(0x0C, 0x00);
    es_w(0x10, 0x1F); es_w(0x11, 0x7F);
    es_w(0x00, 0x80);
    es_w(0x01, 0x3F);
    es_w(0x02, 0x00); es_w(0x05, 0x00);
    es_w(0x03, 0x10); es_w(0x04, 0x10);
    es_w(0x07, 0x00); es_w(0x08, 0xFF);
    es_w(0x06, 0x03);
    es_w(0x09, 0x0C); es_w(0x0A, 0x0C);
    es_w(0x0D, 0x01); es_w(0x0E, 0x02); es_w(0x12, 0x00); es_w(0x13, 0x10);
    es_w(0x1C, 0x6A); es_w(0x37, 0x08);
    es_w(0x17, 0xBF);                 // ADC volume 0 dB
    es_w(0x31, 0x60);                 // mute the DAC
    es_w(0x14, 0x10 | pga);           // analog microphone, preamp gain

    gpio_config_t g = { .pin_bit_mask = 1ULL << PIN_PA, .mode = GPIO_MODE_OUTPUT };
    ESP_ERROR_CHECK(gpio_config(&g));
    gpio_set_level(PIN_PA, 0);        // speaker amp off
}

// ===========================================================================
// Speech recognition
// ===========================================================================
typedef enum { ST_LOADING, ST_LISTEN, ST_COMMAND, ST_OPENING, ST_ERROR } state_t;

static volatile state_t state = ST_LOADING;
static volatile float level_db = -90;                 // microphone level, for the screen
static char heard[96];                                // last recognised phrase
static char note[96];                                 // status / error line
static volatile int64_t cmd_deadline_us;
static volatile int64_t shown_until_us;

static char app_name[MAX_APPS][48];
static int napps;                                     // entry 0 is the built-in clock

static esp_afe_sr_iface_t *afe;
static esp_afe_sr_data_t *afe_data;
static esp_mn_iface_t *mn;
static model_iface_data_t *mn_data;

static int by_name(const void *a, const void *b) { return strcasecmp((const char *)a, (const char *)b); }

static void scan_apps(void)
{
    snprintf(app_name[0], sizeof app_name[0], "Clock");
    napps = 1;
    DIR *d = opendir(APPS_DIR);
    if (!d) return;
    int first = napps;
    struct dirent *de;
    while ((de = readdir(d)) && napps < MAX_APPS) {
        const char *n = de->d_name;
        size_t len = strlen(n);
        if (len < 5 || strcasecmp(n + len - 4, ".bin") || len - 4 >= sizeof app_name[0]) continue;
        if (!strncasecmp(n, "Voice", len - 4) && len == 9) continue;       // not this app
        memcpy(app_name[napps], n, len - 4);
        app_name[napps][len - 4] = 0;
        napps++;
    }
    closedir(d);
    qsort(app_name[first], napps - first, sizeof app_name[0], by_name);
}

static void lower(char *s) { for (; *s; s++) if (*s >= 'A' && *s <= 'Z') *s += 32; }

static bool sr_init(void)
{
    srmodel_list_t *models = esp_srmodel_init(MODEL_DIR);
    if (!models || models->num == 0) { snprintf(note, sizeof note, "No speech models in %s", MODEL_DIR); return false; }
    char *wn = esp_srmodel_filter(models, ESP_WN_PREFIX, NULL);
    char *mnn = esp_srmodel_filter(models, ESP_MN_PREFIX, ESP_MN_ENGLISH);
    ESP_LOGI(TAG, "models: wake word %s, commands %s", wn ? wn : "-", mnn ? mnn : "-");
    if (!wn || !mnn) { snprintf(note, sizeof note, "Missing %s model on the SD card", wn ? "command" : "wake word"); return false; }

    afe_config_t *cfg = afe_config_init("M", models, AFE_TYPE_SR, AFE_MODE_HIGH_PERF);
    cfg->wakenet_model_name = wn;
    cfg->aec_init = false;
    cfg->memory_alloc_mode = AFE_MEMORY_ALLOC_MORE_PSRAM;
    cfg = afe_config_check(cfg);
    afe = (esp_afe_sr_iface_t *)esp_afe_handle_from_config(cfg);
    afe_data = afe->create_from_config(cfg);
    if (!afe_data) { snprintf(note, sizeof note, "Cannot start the audio front end"); return false; }
    afe_config_free(cfg);

    mn = esp_mn_handle_from_name(mnn);
    mn_data = mn->create(mnn, CMD_TIMEOUT_MS);
    if (!mn_data) { snprintf(note, sizeof note, "Cannot start the command model"); return false; }
    if (mn->get_samp_chunksize(mn_data) != afe->get_fetch_chunksize(afe_data))
        ESP_LOGW(TAG, "chunk sizes differ: mn %d, afe %d", mn->get_samp_chunksize(mn_data), afe->get_fetch_chunksize(afe_data));

    esp_mn_commands_alloc(mn, mn_data);
    for (int i = 0; i < napps; i++) {
        char p[80];
        snprintf(p, sizeof p, "open %.47s", app_name[i]); lower(p);
        esp_mn_commands_add(i + 1, p);
        snprintf(p, sizeof p, "%.47s", app_name[i]); lower(p);
        esp_mn_commands_add(i + 1, p);
    }
    esp_mn_error_t *err = esp_mn_commands_update();
    if (err) for (int i = 0; i < err->num; i++) ESP_LOGW(TAG, "command rejected: %s", err->phrases[i]->string);
    mn->print_active_speech_commands(mn_data);
    return true;
}

// Reads the microphone and feeds the front end.
static void feed_task(void *arg)
{
    int chunk = afe->get_feed_chunksize(afe_data);
    int16_t *st = heap_caps_malloc(chunk * 2 * sizeof(int16_t), MALLOC_CAP_INTERNAL);
    int16_t *mono = heap_caps_malloc(chunk * sizeof(int16_t), MALLOC_CAP_INTERNAL);
    assert(st && mono);
    while (1) {
        size_t got = 0;
        if (i2s_channel_read(rx, st, chunk * 2 * sizeof(int16_t), &got, 1000) != ESP_OK || got < chunk * 4) continue;
        double e = 0;
        for (int i = 0; i < chunk; i++) { mono[i] = st[2 * i]; e += (double)mono[i] * mono[i]; }
        float db = 10 * log10f((float)(e / chunk) + 1.0f) - 90.3f;     // dBFS of 16-bit samples
        level_db = db;
        afe->feed(afe_data, mono);
    }
}

static void handoff(const char *name)
{
    nvs_handle_t h;
    if (nvs_open("voice", NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_str(h, "next", name);
        nvs_commit(h);
        nvs_close(h);
    }
    ESP_LOGI(TAG, "handing over to the launcher: %s", name);
    vTaskDelay(pdMS_TO_TICKS(600));
    esp_restart();
}

static void detect_task(void *arg)
{
    while (1) {
        afe_fetch_result_t *res = afe->fetch_with_delay(afe_data, portMAX_DELAY);
        if (!res || res->ret_value == ESP_FAIL) continue;
        if (state == ST_LISTEN) {
            if (res->wakeup_state == WAKENET_DETECTED) {
                ESP_LOGI(TAG, "wake word");
                afe->disable_wakenet(afe_data);
                mn->clean(mn_data);
                cmd_deadline_us = esp_timer_get_time() + CMD_TIMEOUT_MS * 1000LL;
                state = ST_COMMAND;
            }
        } else if (state == ST_COMMAND) {
            esp_mn_state_t s = mn->detect(mn_data, res->data);
            if (s == ESP_MN_STATE_DETECTED) {
                esp_mn_results_t *r = mn->get_results(mn_data);
                int id = r->num > 0 ? r->command_id[0] : 0;
                snprintf(heard, sizeof heard, "%.70s (%.0f%%)", r->string, r->prob[0] * 100);
                ESP_LOGI(TAG, "heard \"%s\" id %d prob %.2f", r->string, id, r->prob[0]);
                if (id >= 1 && id <= napps) {
                    state = ST_OPENING;
                    snprintf(note, sizeof note, "%.47s", app_name[id - 1]);
                    handoff(app_name[id - 1]);
                }
                afe->enable_wakenet(afe_data);
                state = ST_LISTEN;
            } else if (s == ESP_MN_STATE_TIMEOUT) {
                ESP_LOGI(TAG, "command timeout");
                snprintf(heard, sizeof heard, "(nothing recognised)");
                afe->enable_wakenet(afe_data);
                state = ST_LISTEN;
            }
        }
    }
}

// ===========================================================================
// Screen
// ===========================================================================
#define C_BG rgb565(12, 12, 16)
#define C_BAR rgb565(30, 30, 38)
#define C_TEXT rgb565(225, 225, 225)
#define C_DIM rgb565(140, 140, 152)
#define C_ACC rgb565(255, 140, 0)
#define C_OK rgb565(60, 200, 90)
#define C_ERR rgb565(255, 90, 90)
#define QUIT_X 360
#define QUIT_Y 262
#define QUIT_W 112
#define QUIT_H 48

static void draw_all(void)
{
    fill_rect(0, 0, LCD_W, FB_H, C_BG);
    fill_rect(0, 0, LCD_W, 36, C_BAR);
    draw_text(10, 10, "Voice launcher", 1, C_TEXT);
    draw_text(LCD_W - 10 - text_width("wake word: Hi ESP", 1), 10, "wake word: Hi ESP", 1, C_DIM);

    const char *big = ""; uint16_t bc = C_TEXT;
    switch (state) {
    case ST_LOADING: big = "Loading..."; bc = C_DIM; break;
    case ST_LISTEN: big = "Say \"Hi ESP\""; bc = C_TEXT; break;
    case ST_COMMAND: big = "Say a command"; bc = C_ACC; break;
    case ST_OPENING: big = "Opening..."; bc = C_OK; break;
    case ST_ERROR: big = "Problem"; bc = C_ERR; break;
    }
    draw_text_c(LCD_W / 2, 56, big, 3, bc);
    if (state == ST_OPENING || state == ST_ERROR) draw_text_c(LCD_W / 2, 112, note, 2, bc);

    if (state == ST_COMMAND) {                                    // time left
        int64_t left = cmd_deadline_us - esp_timer_get_time();
        if (left < 0) left = 0;
        fill_rect(40, 110, LCD_W - 80, 10, C_BAR);
        fill_rect(40, 110, (int)((LCD_W - 80) * left / (CMD_TIMEOUT_MS * 1000LL)), 10, C_ACC);
        draw_text_c(LCD_W / 2, 132, "for example: open life", 1, C_DIM);
    }

    // microphone level, -60 .. 0 dBFS
    float v = (level_db + 60.0f) / 60.0f;
    if (v < 0) v = 0;
    if (v > 1) v = 1;
    draw_text(40, 168, "mic", 1, C_DIM);
    fill_rect(80, 170, LCD_W - 120, 12, C_BAR);
    fill_rect(80, 170, (int)((LCD_W - 120) * v), 12, v > 0.9f ? C_ERR : C_OK);

    if (heard[0]) {
        draw_text(40, 200, "heard:", 1, C_DIM);
        draw_text(104, 200, heard, 1, C_TEXT);
    }

    // the apps that can be opened
    draw_text(40, 230, "apps:", 1, C_DIM);
    int x = 40 + 6 * 8, y = 230;
    for (int i = 0; i < napps; i++) {
        int w = text_width(app_name[i], 1) + 16;
        if (x + w > QUIT_X - 8) { x = 40; y += 20; if (y > 262) break; }
        draw_text(x, y, app_name[i], 1, C_TEXT);
        x += w;
    }

    fill_rect(QUIT_X, QUIT_Y, QUIT_W, QUIT_H, C_BAR);
    draw_text_c(QUIT_X + QUIT_W / 2, QUIT_Y + 16, "BACK", 1, C_TEXT);
}

void app_main(void)
{
    ESP_LOGI(TAG, "internal free %u, largest DMA block %u", (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
             (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL));
    esp_err_t nr = nvs_flash_init();
    if (nr == ESP_ERR_NVS_NO_FREE_PAGES || nr == ESP_ERR_NVS_NEW_VERSION_FOUND) { nvs_flash_erase(); nvs_flash_init(); }
    display_init();
    touch_init();
    draw_all();
    flush_rows(0, FB_H);

    bool ok = sd_mount();
    if (!ok) { snprintf(note, sizeof note, "No SD card"); state = ST_ERROR; }
    else {
        scan_apps();
        audio_init();
        ok = sr_init();
        if (!ok) state = ST_ERROR;
    }
    if (ok) {
        xTaskCreatePinnedToCore(feed_task, "feed", 4096, NULL, 5, NULL, 1);
        xTaskCreatePinnedToCore(detect_task, "detect", 8192, NULL, 5, NULL, 0);
        state = ST_LISTEN;
    }

    state_t shown = (state_t)-1;
    bool was_down = false;
    int64_t last = 0;
    while (1) {
        int x, y;
        bool down = touch_read(&x, &y);
        if (!down && was_down) esp_restart();                    // BACK: touch released anywhere on the button is checked below
        was_down = false;
        if (down && x >= QUIT_X && y >= QUIT_Y && y < QUIT_Y + QUIT_H) was_down = true;
        int64_t now = esp_timer_get_time();
        if (state != shown || now - last > 100000) {
            shown = state; last = now;
            draw_all();
            flush_rows(0, FB_H);
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
