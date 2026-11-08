#pragma once

#include <atomic>
#include "systems/phone/esp_brookesia_phone_app.hpp"

namespace esp_brookesia::apps
{

    // Analog + digital clock with current weather (Open-Meteo over Wi-Fi).
    class WeatherClock : public systems::phone::App
    {
    public:
        static WeatherClock *requestInstance(bool use_status_bar = false, bool use_navigation_bar = false);
        ~WeatherClock();

        using systems::phone::App::endRecordResource;
        using systems::phone::App::startRecordResource;

    protected:
        WeatherClock(bool use_status_bar, bool use_navigation_bar);

        bool run(void) override;
        bool back(void) override;
        bool close(void) override;
        bool init(void) override;
        bool deinit(void) override;

    private:
        static WeatherClock *_instance;
    };

} // namespace esp_brookesia::apps
