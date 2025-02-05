
import aiohttp
import math

OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

async def get_city_temperature(city: str) -> float:
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(OPENWEATHER_URL, params=params) as resp:
            data = await resp.json()
            if data.get("cod") != 200:
                return None
            return data["main"]["temp"]

async def get_food_info(product_name: str) -> dict:
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, ssl=False) as resp:
            data = await resp.json()
            products = data.get("products")
            if products:
                product = products[0]
                nutriments = product.get("nutriments", {})
                calories = nutriments.get("energy-kcal_100g") or nutriments.get("energy_100g")
                if calories:
                    return {
                        "product_name": product.get("product_name", product_name),
                        "calories_per_100g": float(calories)
                    }
            return None

def calculate_water_goal(weight: float, activity_minutes: int, temperature: float = None) -> int:
    base = weight * 30  # 30 мл на кг
    activity_bonus = (activity_minutes // 30) * 500  # +500 мл за каждые 30 минут активности
    extra = 0
    if temperature is not None and temperature > 25:
        extra = 500  # +500 мл при жаркой погоде
    return int(base + activity_bonus + extra)

def calculate_calorie_goal(weight: float, height: float, age: int, activity_minutes: int, manual_goal: int = None) -> int:
    if manual_goal is not None:
        return manual_goal
    bmr = 10 * weight + 6.25 * height - 5 * age
    bonus = (activity_minutes / 30) * 300
    return int(bmr + bonus)

def calculate_food_calories(calories_per_100g: float, grams: float) -> float:
    return (calories_per_100g / 100) * grams

def calculate_workout_stats(workout_type: str, minutes: int) -> dict:
    burned = minutes * 10
    water_recommendation = (minutes // 30 + (1 if minutes % 30 > 0 else 0)) * 200
    return {"burned_calories": burned, "water_recommendation": water_recommendation}
