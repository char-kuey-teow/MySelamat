import requests

def get_weather(locations: str):
    """
    Fetch realtime weather for a given location from data.gov.my API.
    
    Args:
        location_name (str): Location name (e.g., "Langkawi") or ID (e.g., "Ds001").
    
    Returns:
        dict: Weather data for the location, or None if not found.
    """
    url = "https://api.data.gov.my/weather/forecast"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("❌ API request failed:", e)
        return None

    data = response.json()
    
    # Try from most specific (town) to broader (state)
    for location_name in locations:
        location_weather = []
        for entry in data:
            loc = entry.get("location", {})
            if (loc.get("location_name", "").lower() == location_name.lower()) or (loc.get("location_id") == location_name):
                location_weather.append(entry)

        if location_weather:  # Found match
            location_weather.sort(key=lambda x: x["date"])  # sort by date
            print(f"✅ Found weather for '{location_name}'")
            return {
                "matched_location": location_name,
                "weather_data": location_weather
            }

    print(f"⚠️ None of the locations {locations} were found in API response.")
    return None


# Example usage
if __name__ == "__main__":
    weather = get_weather("Johor Bahru")  # You can also try "Ds001"
    if weather:
        print("✅ Weather data found:")
        print(weather)
