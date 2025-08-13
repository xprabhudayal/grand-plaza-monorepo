"""
Menu display utility
Pretty print the hotel menu for easy viewing
"""
import sys
from pathlib import Path

# Add the data directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from data.menu_data import HOTEL_MENU_DATA, get_menu_categories, get_all_menu_items, search_menu_items

def display_full_menu():
    """Display the complete menu with categories and items"""
    print("🏨 HOTEL ROOM SERVICE MENU")
    print("=" * 60)
    
    total_items = 0
    
    for category in HOTEL_MENU_DATA["categories"]:
        print(f"\n📂 {category['name'].upper()}")
        print(f"   {category['description']}")
        print("-" * 50)
        
        for item in category["items"]:
            dietary_info = ""
            if item["dietary"]:
                dietary_tags = " | ".join([f"#{tag}" for tag in item["dietary"]])
                dietary_info = f" ({dietary_tags})"
            
            print(f"• {item['name']:<25} ${item['price']:>6.2f}")
            print(f"  {item['description']}")
            print(f"  ⏱️  {item['preparation_time']} min{dietary_info}")
            print()
            
            total_items += 1
    
    print("=" * 60)
    print(f"📊 SUMMARY: {len(HOTEL_MENU_DATA['categories'])} categories, {total_items} items")

def display_menu_summary():
    """Display a condensed menu summary"""
    print("🏨 HOTEL ROOM SERVICE - MENU SUMMARY")
    print("=" * 50)
    
    for category in HOTEL_MENU_DATA["categories"]:
        print(f"\n📂 {category['name']} ({len(category['items'])} items)")
        for item in category["items"]:
            print(f"   • {item['name']:<30} ${item['price']:>6.2f}")

def display_dietary_options():
    """Display items by dietary restrictions"""
    print("🥗 DIETARY OPTIONS")
    print("=" * 40)
    
    dietary_groups = {}
    
    for category in HOTEL_MENU_DATA["categories"]:
        for item in category["items"]:
            for diet in item["dietary"]:
                if diet not in dietary_groups:
                    dietary_groups[diet] = []
                dietary_groups[diet].append({
                    "name": item["name"],
                    "category": category["name"],
                    "price": item["price"]
                })
    
    for diet_type, items in dietary_groups.items():
        print(f"\n🏷️  {diet_type.upper()} OPTIONS ({len(items)} items)")
        print("-" * 30)
        for item in items:
            print(f"   • {item['name']:<25} ${item['price']:>6.2f} ({item['category']})")

def display_price_ranges():
    """Display menu items by price ranges"""
    print("💰 MENU BY PRICE RANGES")
    print("=" * 40)
    
    all_items = get_all_menu_items()
    
    price_ranges = [
        (0, 10, "💲 Under $10"),
        (10, 20, "💲💲 $10 - $20"),
        (20, 30, "💲💲💲 $20 - $30"),
        (30, 50, "💲💲💲💲 $30+")
    ]
    
    for min_price, max_price, label in price_ranges:
        items_in_range = [
            item for item in all_items 
            if min_price <= item["price"] < max_price or (max_price == 50 and item["price"] >= min_price)
        ]
        
        if items_in_range:
            print(f"\n{label} ({len(items_in_range)} items)")
            print("-" * 30)
            for item in sorted(items_in_range, key=lambda x: x["price"]):
                print(f"   • {item['name']:<25} ${item['price']:>6.2f} ({item['category']})")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "summary":
            display_menu_summary()
        elif command == "dietary":
            display_dietary_options()
        elif command == "prices":
            display_price_ranges()
        elif command == "search" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            results = search_menu_items(query)
            print(f"🔍 SEARCH RESULTS for '{query}'")
            print("=" * 40)
            if results:
                for item in results:
                    print(f"• {item['name']} - ${item['price']} ({item['category']})")
                    print(f"  {item['description']}")
                    print()
            else:
                print("No items found matching your search.")
        else:
            print("Available commands:")
            print("  python menu_display.py summary")
            print("  python menu_display.py dietary")
            print("  python menu_display.py prices")
            print("  python menu_display.py search <term>")
    else:
        display_full_menu()