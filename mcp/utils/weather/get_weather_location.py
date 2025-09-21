import requests
import json
from collections import defaultdict

# Example: call the weather forecast endpoint
url = "https://api.data.gov.my/weather/forecast"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()

    # Dictionary of categories -> dict of unique locations
    categories = defaultdict(dict)

    for entry in data:
        loc = entry.get("location", {})
        loc_id = loc.get("location_id")
        loc_name = loc.get("location_name")

        if not (loc_id and loc_name):
            continue

        # Detect category based on prefix
        if loc_id.startswith("St"):
            cat = "State"
        elif loc_id.startswith("Rc"):
            cat = "Recreation Centre"
        elif loc_id.startswith("Ds"):
            cat = "District"
        elif loc_id.startswith("Tn"):
            cat = "Town"
        elif loc_id.startswith("Dv"):
            cat = "Division"
        else:
            cat = "Other"

        # Deduplicate: use loc_id+name as unique key
        categories[cat][loc_id + "_" + loc_name] = {
            "location_id": loc_id,
            "location_name": loc_name
        }

    # Convert to JSON-serializable dict (list of dicts for each category)
    grouped_locations = {
        cat: list(locations.values())
        for cat, locations in categories.items()
    }

    # Save into JSON file
    with open("weather_api_locations.json", "w", encoding="utf-8") as f:
        json.dump(grouped_locations, f, ensure_ascii=False, indent=4)

    print("✅ locations.json file has been created with distinct locations.")
else:
    print("❌ Failed to fetch API:", response.status_code)
