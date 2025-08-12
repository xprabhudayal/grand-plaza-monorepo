"""
Hotel Room Service Menu Data
Comprehensive menu structure for voice AI concierge system
"""

HOTEL_MENU_DATA = {
    "categories": [
        {
            "name": "Breakfast",
            "description": "Start your day with our fresh breakfast options, available 24/7",
            "display_order": 1,
            "is_active": True,
            "items": [
                {
                    "name": "Continental Breakfast",
                    "description": "Fresh croissants, seasonal fruit, yogurt, orange juice, and coffee",
                    "price": 18.50,
                    "preparation_time": 15,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "American Breakfast",
                    "description": "Two eggs your way, bacon or sausage, hash browns, toast, and coffee",
                    "price": 22.00,
                    "preparation_time": 20,
                    "dietary": None,
                    "is_available": True
                },
                {
                    "name": "Avocado Toast",
                    "description": "Smashed avocado on sourdough bread with cherry tomatoes and feta cheese",
                    "price": 16.00,
                    "preparation_time": 10,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Pancakes",
                    "description": "Three fluffy pancakes with maple syrup and butter",
                    "price": 14.50,
                    "preparation_time": 15,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Oatmeal Bowl",
                    "description": "Steel-cut oats with berries, nuts, and honey",
                    "price": 12.00,
                    "preparation_time": 10,
                    "dietary": "vegetarian,gluten-free",
                    "is_available": True
                }
            ]
        },
        {
            "name": "Appetizers",
            "description": "Light bites and starters to begin your meal",
            "display_order": 2,
            "is_active": True,
            "items": [
                {
                    "name": "Shrimp Cocktail",
                    "description": "Five jumbo shrimp with cocktail sauce and lemon",
                    "price": 19.00,
                    "preparation_time": 10,
                    "dietary": "gluten-free",
                    "is_available": True
                },
                {
                    "name": "Buffalo Wings",
                    "description": "Eight crispy wings with buffalo sauce and blue cheese dip",
                    "price": 16.50,
                    "preparation_time": 20,
                    "dietary": "gluten-free",
                    "is_available": True
                },
                {
                    "name": "Hummus Plate",
                    "description": "House-made hummus with fresh vegetables and pita bread",
                    "price": 13.00,
                    "preparation_time": 5,
                    "dietary": "vegetarian,vegan",
                    "is_available": True
                },
                {
                    "name": "Loaded Nachos",
                    "description": "Tortilla chips with cheese, jalapeños, sour cream, and guacamole",
                    "price": 15.50,
                    "preparation_time": 12,
                    "dietary": "vegetarian",
                    "is_available": True
                }
            ]
        },
        {
            "name": "Salads",
            "description": "Fresh, healthy salads made with premium ingredients",
            "display_order": 3,
            "is_active": True,
            "items": [
                {
                    "name": "Caesar Salad",
                    "description": "Romaine lettuce, parmesan cheese, croutons, and Caesar dressing",
                    "price": 14.00,
                    "preparation_time": 8,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Grilled Chicken Caesar",
                    "description": "Classic Caesar salad topped with grilled chicken breast",
                    "price": 18.50,
                    "preparation_time": 12,
                    "dietary": None,
                    "is_available": True
                },
                {
                    "name": "Mediterranean Salad",
                    "description": "Mixed greens, olives, tomatoes, cucumber, feta cheese, and olive oil",
                    "price": 16.00,
                    "preparation_time": 8,
                    "dietary": "vegetarian,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Quinoa Power Bowl",
                    "description": "Quinoa with roasted vegetables, chickpeas, and tahini dressing",
                    "price": 17.50,
                    "preparation_time": 10,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                }
            ]
        },
        {
            "name": "Main Courses",
            "description": "Hearty entrees to satisfy your appetite",
            "display_order": 4,
            "is_active": True,
            "items": [
                {
                    "name": "Grilled Salmon",
                    "description": "Atlantic salmon with lemon herb butter, rice pilaf, and seasonal vegetables",
                    "price": 28.00,
                    "preparation_time": 25,
                    "dietary": "gluten-free",
                    "is_available": True
                },
                {
                    "name": "Ribeye Steak",
                    "description": "12oz ribeye steak with garlic mashed potatoes and asparagus",
                    "price": 35.00,
                    "preparation_time": 30,
                    "dietary": "gluten-free",
                    "is_available": True
                },
                {
                    "name": "Chicken Parmesan",
                    "description": "Breaded chicken breast with marinara sauce, mozzarella, and pasta",
                    "price": 24.50,
                    "preparation_time": 25,
                    "dietary": None,
                    "is_available": True
                },
                {
                    "name": "Vegetable Curry",
                    "description": "Coconut curry with seasonal vegetables served over jasmine rice",
                    "price": 21.00,
                    "preparation_time": 20,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Fish and Chips",
                    "description": "Beer-battered cod with french fries and coleslaw",
                    "price": 22.50,
                    "preparation_time": 20,
                    "dietary": None,
                    "is_available": True
                }
            ]
        },
        {
            "name": "Sandwiches",
            "description": "Gourmet sandwiches and burgers served with fries",
            "display_order": 5,
            "is_active": True,
            "items": [
                {
                    "name": "Club Sandwich",
                    "description": "Turkey, bacon, lettuce, tomato, and mayo on toasted bread",
                    "price": 16.50,
                    "preparation_time": 12,
                    "dietary": None,
                    "is_available": True
                },
                {
                    "name": "Cheeseburger",
                    "description": "Angus beef patty with cheese, lettuce, tomato, and onion",
                    "price": 18.00,
                    "preparation_time": 15,
                    "dietary": None,
                    "is_available": True
                },
                {
                    "name": "Veggie Burger",
                    "description": "House-made black bean patty with avocado and sprouts",
                    "price": 16.00,
                    "preparation_time": 12,
                    "dietary": "vegetarian,vegan",
                    "is_available": True
                },
                {
                    "name": "Reuben Sandwich",
                    "description": "Corned beef, sauerkraut, swiss cheese, and russian dressing on rye",
                    "price": 17.50,
                    "preparation_time": 12,
                    "dietary": None,
                    "is_available": True
                }
            ]
        },
        {
            "name": "Desserts",
            "description": "Sweet treats to end your meal perfectly",
            "display_order": 6,
            "is_active": True,
            "items": [
                {
                    "name": "Chocolate Cake",
                    "description": "Rich chocolate layer cake with chocolate ganache",
                    "price": 9.50,
                    "preparation_time": 5,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "New York Cheesecake",
                    "description": "Classic cheesecake with graham cracker crust and berry compote",
                    "price": 8.50,
                    "preparation_time": 5,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Ice Cream Sundae",
                    "description": "Three scoops of vanilla ice cream with hot fudge and whipped cream",
                    "price": 7.00,
                    "preparation_time": 5,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Fresh Fruit Bowl",
                    "description": "Seasonal fresh fruit with honey yogurt dip",
                    "price": 8.00,
                    "preparation_time": 5,
                    "dietary": "vegetarian,gluten-free",
                    "is_available": True
                }
            ]
        },
        {
            "name": "Beverages",
            "description": "Hot and cold beverages to complement your meal",
            "display_order": 7,
            "is_active": True,
            "items": [
                {
                    "name": "Coffee",
                    "description": "Freshly brewed premium coffee",
                    "price": 4.50,
                    "preparation_time": 3,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Tea Selection",
                    "description": "Choice of black, green, herbal, or iced tea",
                    "price": 4.00,
                    "preparation_time": 3,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Fresh Orange Juice",
                    "description": "Freshly squeezed orange juice",
                    "price": 5.50,
                    "preparation_time": 2,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Soft Drinks",
                    "description": "Coca-Cola, Sprite, or other soft drinks",
                    "price": 3.50,
                    "preparation_time": 1,
                    "dietary": "vegetarian,vegan,gluten-free",
                    "is_available": True
                },
                {
                    "name": "Wine by the Glass",
                    "description": "Selection of red or white wines",
                    "price": 12.00,
                    "preparation_time": 2,
                    "dietary": "vegetarian",
                    "is_available": True
                },
                {
                    "name": "Beer",
                    "description": "Domestic or imported beer selection",
                    "price": 6.50,
                    "preparation_time": 1,
                    "dietary": None,
                    "is_available": True
                }
            ]
        }
    ]
}

def get_menu_categories():
    """Return list of menu categories"""
    return [
        {
            "name": cat["name"],
            "description": cat["description"],
            "display_order": cat["display_order"],
            "is_active": cat["is_active"]
        }
        for cat in HOTEL_MENU_DATA["categories"]
    ]

def get_menu_items_by_category(category_name):
    """Return menu items for a specific category"""
    for category in HOTEL_MENU_DATA["categories"]:
        if category["name"].lower() == category_name.lower():
            return category["items"]
    return []

def get_all_menu_items():
    """Return all menu items flattened"""
    all_items = []
    for category in HOTEL_MENU_DATA["categories"]:
        for item in category["items"]:
            item_with_category = item.copy()
            item_with_category["category"] = category["name"]
            all_items.append(item_with_category)
    return all_items

def search_menu_items(query):
    """Search menu items by name or description"""
    query = query.lower()
    results = []
    
    for category in HOTEL_MENU_DATA["categories"]:
        for item in category["items"]:
            if (query in item["name"].lower() or 
                query in item["description"].lower() or
                any(query in diet.lower() for diet in item["dietary"])):
                item_with_category = item.copy()
                item_with_category["category"] = category["name"]
                results.append(item_with_category)
    
    return results