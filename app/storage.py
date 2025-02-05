
users = {}

def get_user(user_id: int):
    return users.get(user_id)

def set_user(user_id: int, user_data: dict):
    users[user_id] = user_data

def update_user(user_id: int, key: str, value):
    if user_id in users:
        users[user_id][key] = value
    else:
        users[user_id] = {key: value}

def add_water(user_id: int, amount: int):
    if user_id in users:
        users[user_id]["logged_water"] = users[user_id].get("logged_water", 0) + amount

def add_food_calories(user_id: int, calories: float):
    if user_id in users:
        users[user_id]["logged_calories"] = users[user_id].get("logged_calories", 0) + calories

def add_burned_calories(user_id: int, calories: float):
    if user_id in users:
        users[user_id]["burned_calories"] = users[user_id].get("burned_calories", 0) + calories

def delete_user(user_id: int):
    """Удаляет данные пользователя из памяти."""
    if user_id in users:
        del users[user_id]

