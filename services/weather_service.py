"""
weather_service.py
------------------
Weather data from the Open-Meteo API (free, no API key needed).
Uses the geocoding API to convert city names to coordinates,
then fetches current weather conditions and multi-day forecasts.
"""

import requests
from functools import lru_cache

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes → human-readable descriptions
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@lru_cache(maxsize=32)
def geocode_city(city: str) -> tuple | None:
    """
    Convert a city name to (latitude, longitude, display_name).
    Returns None if the city is not found.
    Cached to avoid repeated API calls for the same city.
    """
    try:
        resp = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        if "results" in data and len(data["results"]) > 0:
            r = data["results"][0]
            display = f"{r.get('name', city)}, {r.get('country', '')}"
            return (r["latitude"], r["longitude"], display)
    except Exception:
        pass
    return None


def get_weather(city: str, forecast_days: int = 1) -> dict | None:
    """
    Fetch weather for a city. Supports current conditions and multi-day forecasts.

    Args:
        city: City name (e.g. 'Barcelona', 'Paris', 'New York')
        forecast_days: Number of days to forecast (1-16). Default 1 = today only.

    Returns a dict with:
        - city, temperature, feels_like, description, precipitation_probability,
          wind_speed, humidity (current conditions)
        - daily_forecast: list of {date, temp_max, temp_min, description,
          precipitation_probability} for each forecast day
    Returns None on failure.
    """
    geo = geocode_city(city)
    if geo is None:
        return None

    lat, lon, display_name = geo
    forecast_days = max(1, min(forecast_days, 16))

    try:
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": forecast_days,
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        weather_code = current.get("weather_code", 0)
        description = WMO_CODES.get(weather_code, "Unknown")

        precip_probs = daily.get("precipitation_probability_max", [0])
        precip_prob = precip_probs[0] if precip_probs else 0

        # Build daily forecast list
        daily_forecast = []
        dates = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        weather_codes = daily.get("weather_code", [])
        precip_probs_daily = daily.get("precipitation_probability_max", [])

        for i in range(len(dates)):
            day_code = weather_codes[i] if i < len(weather_codes) else 0
            daily_forecast.append({
                "date": dates[i],
                "temp_max": temps_max[i] if i < len(temps_max) else None,
                "temp_min": temps_min[i] if i < len(temps_min) else None,
                "description": WMO_CODES.get(day_code, "Unknown"),
                "precipitation_probability": precip_probs_daily[i] if i < len(precip_probs_daily) else 0,
            })

        result = {
            "city": display_name,
            "temperature": current.get("temperature_2m", 0),
            "feels_like": current.get("apparent_temperature", 0),
            "description": description,
            "weather_code": weather_code,
            "precipitation_probability": precip_prob,
            "wind_speed": current.get("wind_speed_10m", 0),
            "humidity": current.get("relative_humidity_2m", 0),
        }

        if forecast_days > 1:
            result["daily_forecast"] = daily_forecast

        return result
    except Exception as e:
        print(f"Weather API error: {e}")
        return None


def get_weather_summary(city: str) -> str:
    """Return a short one-line weather summary for display in the UI."""
    w = get_weather(city)
    if w is None:
        return f"{city} · Weather unavailable"
    return f"{w['city']} · {w['temperature']}°C · {w['description']}"


if __name__ == "__main__":
    print(get_weather_summary("Barcelona"))
    w = get_weather("Barcelona")
    if w:
        import json
        print(json.dumps(w, indent=2))
    print("\n--- 7-day forecast for Paris ---")
    w7 = get_weather("Paris", forecast_days=7)
    if w7:
        for day in w7.get("daily_forecast", []):
            print(f"  {day['date']}: {day['temp_min']}–{day['temp_max']}°C, {day['description']}, rain {day['precipitation_probability']}%")
