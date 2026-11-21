/*
 * Clock app for the ESP-Brookesia launcher: analog dial, digital time, date and
 * current weather. Ported from the standalone p4clock project to LVGL.
 */
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <sys/time.h>

#ifdef ESP_UTILS_LOG_TAG
#   undef ESP_UTILS_LOG_TAG
#endif
#define ESP_UTILS_LOG_TAG "BS:App:Clock"
#include "esp_lib_utils.h"

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_crt_bundle.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "cJSON.h"

#include "board_wifi.h"
#include "clock_config.h"
#include "ClockApp.hpp"

using namespace esp_brookesia::systems;

LV_IMG_DECLARE(img_app_clock);
LV_FONT_DECLARE(lv_font_montserrat_36);

#define APP_NAME "Clock"

// Palette (matches the p4clock project)
#define C_BG        lv_color_hex(0x121826)
#define C_FACE      lv_color_hex(0x0e1422)
#define C_RING      lv_color_hex(0x8fa3c4)
#define C_TICK_HR   lv_color_hex(0xc8d4e8)
#define C_TICK_MIN  lv_color_hex(0x4a5870)
#define C_HAND      lv_color_hex(0xe8eefc)
#define C_SECOND    lv_color_hex(0xff6b6b)
#define C_TIME      lv_color_hex(0xe8eefc)
#define C_DATE      lv_color_hex(0x9fb0cc)
#define C_LOC       lv_color_hex(0x8fa3c4)
#define C_COND      lv_color_hex(0xffd166)
#define C_TEMP      lv_color_hex(0xff9f68)
#define C_DETAIL    lv_color_hex(0xb8c4d8)
#define C_UPDATED   lv_color_hex(0x8fa3c4)

namespace {

// ---------------------------------------------------------------------------
// Weather (fetched by one background task that is started with the first run())
// ---------------------------------------------------------------------------
struct Weather {
    bool valid = false;
    double temp = 0, feels = 0, wind = 0;
    int hum = 0, code = 0, wdir = 0;
    time_t stamp = 0;               // wall-clock time of the fetch
};

Weather s_wx;
int s_wx_version = 0;               // bumped on every successful fetch
SemaphoreHandle_t s_wx_lock = nullptr;
bool s_task_started = false;

const struct { int code; const char *txt; } WMO[] = {
    {0, "Clear sky"}, {1, "Mainly clear"}, {2, "Partly cloudy"}, {3, "Overcast"}, {45, "Fog"},
    {48, "Rime fog"}, {51, "Light drizzle"}, {53, "Drizzle"}, {55, "Heavy drizzle"},
    {56, "Freezing drizzle"}, {57, "Freezing drizzle"}, {61, "Light rain"}, {63, "Rain"},
    {65, "Heavy rain"}, {66, "Freezing rain"}, {67, "Freezing rain"}, {71, "Light snow"},
    {73, "Snow"}, {75, "Heavy snow"}, {77, "Snow grains"}, {80, "Light showers"}, {81, "Showers"},
    {82, "Violent showers"}, {85, "Snow showers"}, {86, "Snow showers"}, {95, "Thunderstorm"},
    {96, "Thunderstorm + hail"}, {99, "Thunderstorm + hail"},
};

const char *wmo_text(int code)
{
    static char buf[16];
    for (const auto &w : WMO) {
        if (w.code == code) {
            return w.txt;
        }
    }
    snprintf(buf, sizeof(buf), "code %d", code);
    return buf;
}

const char *compass(int deg)
{
    static const char *n[] = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"};
    return n[((deg + 22) / 45) % 8];
}

char s_http_buf[2048];
int s_http_len;

esp_err_t http_event(esp_http_client_event_t *e)
{
    if (e->event_id == HTTP_EVENT_ON_DATA && s_http_len + e->data_len < (int)sizeof(s_http_buf) - 1) {
        memcpy(s_http_buf + s_http_len, e->data, e->data_len);
        s_http_len += e->data_len;
    }
    return ESP_OK;
}

bool json_number(cJSON *obj, const char *key, double *out)
{
    cJSON *item = cJSON_GetObjectItem(obj, key);
    if (!cJSON_IsNumber(item)) {
        return false;
    }
    *out = item->valuedouble;
    return true;
}

bool fetch_weather()
{
    static const char url[] =
        "https://api.open-meteo.com/v1/forecast?latitude=" CLOCK_LAT "&longitude=" CLOCK_LON
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,"
        "wind_speed_10m,wind_direction_10m,is_day"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto";
    s_http_len = 0;
    esp_http_client_config_t cfg = {};
    cfg.url = url;
    cfg.event_handler = http_event;
    cfg.timeout_ms = 15000;
    cfg.crt_bundle_attach = esp_crt_bundle_attach;
    esp_http_client_handle_t client = esp_http_client_init(&cfg);
    esp_err_t err = esp_http_client_perform(client);
    int status = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
    if (err != ESP_OK || status != 200) {
        ESP_UTILS_LOGW("weather request failed: %s, HTTP %d", esp_err_to_name(err), status);
        return false;
    }
    s_http_buf[s_http_len] = 0;

    cJSON *root = cJSON_Parse(s_http_buf);
    cJSON *cur = root ? cJSON_GetObjectItem(root, "current") : nullptr;
    double temp, feels, hum, code, wind, wdir;
    if (!cur || !json_number(cur, "temperature_2m", &temp) || !json_number(cur, "apparent_temperature", &feels) ||
            !json_number(cur, "relative_humidity_2m", &hum) || !json_number(cur, "weather_code", &code) ||
            !json_number(cur, "wind_speed_10m", &wind) || !json_number(cur, "wind_direction_10m", &wdir)) {
        ESP_UTILS_LOGW("weather JSON unusable");
        cJSON_Delete(root);
        return false;
    }
    cJSON_Delete(root);

    Weather n;
    n.valid = true;
    n.temp = temp;
    n.feels = feels;
    n.hum = (int)hum;
    n.code = (int)code;
    n.wind = wind;
    n.wdir = (int)wdir;
    n.stamp = time(nullptr);
    xSemaphoreTake(s_wx_lock, portMAX_DELAY);
    s_wx = n;
    s_wx_version++;
    xSemaphoreGive(s_wx_lock);
    ESP_UTILS_LOGI("weather: %.0fF feels %.0fF hum %d%% wind %.0f mph code %d (%s)",
                   n.temp, n.feels, n.hum, n.wind, n.code, wmo_text(n.code));
    return true;
}

void weather_task(void *)
{
    while (true) {
        while (!board_wifi_service_is_connected()) {
            vTaskDelay(pdMS_TO_TICKS(2000));
        }
        bool ok = fetch_weather();
        vTaskDelay(pdMS_TO_TICKS((ok ? CLOCK_WEATHER_EVERY_S : 60) * 1000));
    }
}

// ---------------------------------------------------------------------------
// UI state (single instance; created in run(), dropped with the screen in close())
// ---------------------------------------------------------------------------
constexpr int TICKS = 60;

struct Ui {
    int dial = 0;                                   // dial diameter
    lv_obj_t *hour = nullptr, *minute = nullptr, *second = nullptr;
    lv_obj_t *time_lbl = nullptr, *zone_lbl = nullptr, *date_lbl = nullptr;
    lv_obj_t *cond_lbl = nullptr, *temp_lbl = nullptr, *detail1 = nullptr, *detail2 = nullptr, *updated = nullptr;
    lv_point_precise_t hour_pts[2], minute_pts[2], second_pts[2];
    lv_point_precise_t tick_pts[TICKS][2];
    int last_sec = -1;
    int last_wx_version = -1;
    lv_timer_t *timer = nullptr;
};

Ui s_ui;

lv_obj_t *make_label(lv_obj_t *parent, const lv_font_t *font, lv_color_t color)
{
    lv_obj_t *l = lv_label_create(parent);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, color, 0);
    return l;
}

lv_obj_t *make_line(lv_obj_t *parent, lv_point_precise_t *pts, int width, lv_color_t color)
{
    lv_obj_t *line = lv_line_create(parent);
    lv_line_set_points(line, pts, 2);
    lv_obj_set_style_line_width(line, width, 0);
    lv_obj_set_style_line_color(line, color, 0);
    lv_obj_set_style_line_rounded(line, true, 0);
    return line;
}

// Point at `angle` (radians, clockwise from 12 o'clock) and distance r from the dial centre.
void polar(lv_point_precise_t *p, int centre, double angle, double r)
{
    p->x = (lv_value_precise_t)lround(centre + r * sin(angle));
    p->y = (lv_value_precise_t)lround(centre - r * cos(angle));
}

void set_hand(lv_obj_t *line, lv_point_precise_t *pts, int centre, double angle, double length, double tail)
{
    polar(&pts[0], centre, angle + M_PI, tail);
    polar(&pts[1], centre, angle, length);
    lv_line_set_points(line, pts, 2);
}

void update_weather_labels()
{
    Weather w;
    int ver;
    xSemaphoreTake(s_wx_lock, portMAX_DELAY);
    w = s_wx;
    ver = s_wx_version;
    xSemaphoreGive(s_wx_lock);
    if (ver == s_ui.last_wx_version) {
        return;
    }
    s_ui.last_wx_version = ver;
    if (!w.valid) {
        return;
    }
    lv_label_set_text(s_ui.cond_lbl, wmo_text(w.code));
    lv_label_set_text_fmt(s_ui.temp_lbl, "%.0f F", w.temp);
    lv_label_set_text_fmt(s_ui.detail1, "Feels %.0f F    Humidity %d%%", w.feels, w.hum);
    lv_label_set_text_fmt(s_ui.detail2, "Wind %.0f mph %s", w.wind, compass(w.wdir));
    struct tm tm;
    localtime_r(&w.stamp, &tm);
    if (tm.tm_year + 1900 >= 2024) {                // only once SNTP has set the clock
        char t[16];
        strftime(t, sizeof(t), "%I:%M %p", &tm);
        lv_label_set_text_fmt(s_ui.updated, "Weather updated %s", t[0] == '0' ? t + 1 : t);
    } else {
        lv_label_set_text(s_ui.updated, "Weather updated");
    }
}

void tick_cb(lv_timer_t *)
{
    struct timeval tv;
    gettimeofday(&tv, nullptr);
    struct tm tm;
    localtime_r(&tv.tv_sec, &tm);
    double sec = tm.tm_sec + tv.tv_usec / 1e6;
    double min = tm.tm_min + sec / 60.0;
    double hr = (tm.tm_hour % 12) + min / 60.0;
    const int c = s_ui.dial / 2;
    const double R = c - 4;

    set_hand(s_ui.hour, s_ui.hour_pts, c, hr / 12.0 * 2 * M_PI, R * 0.50, R * 0.10);
    set_hand(s_ui.minute, s_ui.minute_pts, c, min / 60.0 * 2 * M_PI, R * 0.74, R * 0.10);
    set_hand(s_ui.second, s_ui.second_pts, c, sec / 60.0 * 2 * M_PI, R * 0.86, R * 0.18);

    if (tm.tm_sec != s_ui.last_sec) {               // text only changes once a second
        s_ui.last_sec = tm.tm_sec;
        int h12 = tm.tm_hour % 12 ? tm.tm_hour % 12 : 12;
        char zone[16], date[40];
        lv_label_set_text_fmt(s_ui.time_lbl, "%d:%02d:%02d", h12, tm.tm_min, tm.tm_sec);
        strftime(zone, sizeof(zone), "%Z", &tm);
        lv_label_set_text_fmt(s_ui.zone_lbl, "%s %s", tm.tm_hour < 12 ? "AM" : "PM", zone);
        strftime(date, sizeof(date), "%A, %B ", &tm);
        lv_label_set_text_fmt(s_ui.date_lbl, "%s%d", date, tm.tm_mday);
    }
    update_weather_labels();
}

} // namespace

namespace esp_brookesia::apps {

WeatherClock *WeatherClock::_instance = nullptr;

WeatherClock *WeatherClock::requestInstance(bool use_status_bar, bool use_navigation_bar)
{
    if (_instance == nullptr) {
        _instance = new WeatherClock(use_status_bar, use_navigation_bar);
    }
    return _instance;
}

WeatherClock::WeatherClock(bool use_status_bar, bool use_navigation_bar) :
    App(APP_NAME, &img_app_clock, true, use_status_bar, use_navigation_bar)
{
}

WeatherClock::~WeatherClock()
{
    ESP_UTILS_LOGD("Destroy(@0x%p)", this);
}

bool WeatherClock::init(void)
{
    return true;
}

bool WeatherClock::deinit(void)
{
    return true;
}

bool WeatherClock::run(void)
{
    ESP_UTILS_LOGD("Run(@0x%p)", this);

    if (s_wx_lock == nullptr) {
        s_wx_lock = xSemaphoreCreateMutex();
        ESP_UTILS_CHECK_NULL_RETURN(s_wx_lock, false, "Create weather lock failed");
    }
    if (!s_task_started) {
        BaseType_t ok = xTaskCreate(weather_task, "clock_wx", 10 * 1024, nullptr, 3, nullptr);
        ESP_UTILS_CHECK_FALSE_RETURN(ok == pdPASS, false, "Create weather task failed");
        s_task_started = true;
    }

    auto area = getVisualArea();
    int width = lv_area_get_width(&area);
    int height = lv_area_get_height(&area);
    if (width == 0 || height == 0) {
        width = 320;
        height = 480;
    }

    s_ui = Ui();
    s_ui.dial = std::min(width - 24, 216);
    const int D = s_ui.dial, C = D / 2;

    lv_obj_t *scr = lv_screen_active();
    lv_obj_clean(scr);
    lv_obj_set_style_bg_color(scr, C_BG, 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *loc = make_label(scr, &lv_font_montserrat_14, C_LOC);
    lv_label_set_text(loc, CLOCK_LOCATION_LABEL);
    lv_obj_align(loc, LV_ALIGN_TOP_MID, 0, 10);

    // Dial: transparent container so line coordinates are relative to its top-left corner.
    lv_obj_t *dial = lv_obj_create(scr);
    lv_obj_remove_style_all(dial);
    lv_obj_set_size(dial, D, D);
    lv_obj_align(dial, LV_ALIGN_TOP_MID, 0, 34);
    lv_obj_remove_flag(dial, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *face = lv_obj_create(dial);
    lv_obj_remove_style_all(face);
    lv_obj_set_size(face, D, D);
    lv_obj_set_style_radius(face, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(face, C_FACE, 0);
    lv_obj_set_style_bg_opa(face, LV_OPA_COVER, 0);
    lv_obj_set_style_border_color(face, C_RING, 0);
    lv_obj_set_style_border_width(face, 4, 0);
    lv_obj_set_style_border_opa(face, LV_OPA_COVER, 0);

    const double R = C - 4;
    for (int i = 0; i < TICKS; i++) {
        bool hour_tick = (i % 5 == 0);
        double a = i * 2 * M_PI / TICKS;
        polar(&s_ui.tick_pts[i][0], C, a, R - (hour_tick ? 13 : 7));
        polar(&s_ui.tick_pts[i][1], C, a, R - 3);
        make_line(dial, s_ui.tick_pts[i], hour_tick ? 3 : 1, hour_tick ? C_TICK_HR : C_TICK_MIN);
    }
    s_ui.hour = make_line(dial, s_ui.hour_pts, 6, C_HAND);
    s_ui.minute = make_line(dial, s_ui.minute_pts, 4, C_HAND);
    s_ui.second = make_line(dial, s_ui.second_pts, 2, C_SECOND);

    lv_obj_t *hub = lv_obj_create(dial);
    lv_obj_remove_style_all(hub);
    lv_obj_set_size(hub, 10, 10);
    lv_obj_set_style_radius(hub, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(hub, C_SECOND, 0);
    lv_obj_set_style_bg_opa(hub, LV_OPA_COVER, 0);
    lv_obj_align(hub, LV_ALIGN_CENTER, 0, 0);

    // Digital time: "h:mm:ss" large, "AM PST" small, on one baseline.
    lv_obj_t *row = lv_obj_create(scr);
    lv_obj_remove_style_all(row);
    lv_obj_set_size(row, LV_SIZE_CONTENT, LV_SIZE_CONTENT);
    lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(row, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_END, LV_FLEX_ALIGN_END);
    lv_obj_set_style_pad_column(row, 6, 0);
    lv_obj_align(row, LV_ALIGN_TOP_MID, 0, 34 + D + 10);
    s_ui.time_lbl = make_label(row, &lv_font_montserrat_36, C_TIME);
    s_ui.zone_lbl = make_label(row, &lv_font_montserrat_20, C_DATE);
    lv_label_set_text(s_ui.time_lbl, "-:--:--");
    lv_label_set_text(s_ui.zone_lbl, "");

    s_ui.date_lbl = make_label(scr, &lv_font_montserrat_20, C_DATE);
    lv_label_set_text(s_ui.date_lbl, "");
    lv_obj_align(s_ui.date_lbl, LV_ALIGN_TOP_MID, 0, 34 + D + 10 + 44);

    lv_obj_t *rule = lv_obj_create(scr);
    lv_obj_remove_style_all(rule);
    lv_obj_set_size(rule, width - 40, 1);
    lv_obj_set_style_bg_color(rule, C_TICK_MIN, 0);
    lv_obj_set_style_bg_opa(rule, LV_OPA_COVER, 0);
    lv_obj_align(rule, LV_ALIGN_TOP_MID, 0, 34 + D + 10 + 44 + 34);

    const int wy = 34 + D + 10 + 44 + 34 + 8;
    s_ui.cond_lbl = make_label(scr, &lv_font_montserrat_20, C_COND);
    lv_label_set_text(s_ui.cond_lbl, "Waiting for weather...");
    lv_obj_align(s_ui.cond_lbl, LV_ALIGN_TOP_MID, 0, wy);
    s_ui.temp_lbl = make_label(scr, &lv_font_montserrat_36, C_TEMP);
    lv_label_set_text(s_ui.temp_lbl, "");
    lv_obj_align(s_ui.temp_lbl, LV_ALIGN_TOP_MID, 0, wy + 26);
    s_ui.detail1 = make_label(scr, &lv_font_montserrat_14, C_DETAIL);
    lv_label_set_text(s_ui.detail1, "");
    lv_obj_align(s_ui.detail1, LV_ALIGN_TOP_MID, 0, wy + 26 + 44);
    s_ui.detail2 = make_label(scr, &lv_font_montserrat_14, C_DETAIL);
    lv_label_set_text(s_ui.detail2, "");
    lv_obj_align(s_ui.detail2, LV_ALIGN_TOP_MID, 0, wy + 26 + 44 + 20);
    s_ui.updated = make_label(scr, &lv_font_montserrat_12, C_UPDATED);
    lv_label_set_text(s_ui.updated, "");
    lv_obj_align(s_ui.updated, LV_ALIGN_TOP_MID, 0, wy + 26 + 44 + 20 + 22);

    s_ui.timer = lv_timer_create(tick_cb, 100, nullptr);
    ESP_UTILS_CHECK_NULL_RETURN(s_ui.timer, false, "Create clock timer failed");
    tick_cb(s_ui.timer);                            // draw immediately instead of after 100 ms
    return true;
}

bool WeatherClock::back(void)
{
    ESP_UTILS_CHECK_FALSE_RETURN(notifyCoreClosed(), false, "Notify core closed failed");
    return true;
}

bool WeatherClock::close(void)
{
    ESP_UTILS_LOGD("Close(@0x%p)", this);
    if (s_ui.timer) {
        lv_timer_delete(s_ui.timer);
        s_ui.timer = nullptr;
    }
    return true;
}

// The app is a singleton owned by itself; the registry must not delete it.
ESP_UTILS_REGISTER_PLUGIN_WITH_CONSTRUCTOR(systems::base::App, WeatherClock, APP_NAME, []()
{
    return std::shared_ptr<WeatherClock>(WeatherClock::requestInstance(), [](WeatherClock *) {});
})

} // namespace esp_brookesia::apps
