#!/usr/bin/env python3
"""
Database initialization script for Hotel Voice AI Concierge.

This script:
1. Creates all database tables
2. Seeds the database with initial categories and sample menu items
3. Sets up the initial data structure

Run this script to initialize your database from scratch.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine, create_tables
from app.models import Base, Category, MenuItem
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

def seed_database():
    """Seed the database with initial data"""
    print("Creating database tables...")
    create_tables()
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Add sample categories
        print("Adding categories...")
        categories_data = [
            {"name": "Breakfast", "description": "Morning meals and beverages", "display_order": 1},
            {"name": "Appetizers", "description": "Light bites and starters", "display_order": 2},
            {"name": "Main Courses", "description": "Hearty entrees and main dishes", "display_order": 3},
            {"name": "Desserts", "description": "Sweet treats and desserts", "display_order": 4},
            {"name": "Beverages", "description": "Hot and cold drinks", "display_order": 5},
        ]
        
        category_objects = {}
        for cat_data in categories_data:
            if not session.query(Category).filter_by(name=cat_data["name"]).first():
                category = Category(**cat_data)
                session.add(category)
                session.flush()  # Flush to get the ID
                category_objects[cat_data["name"]] = category
                print(f"  ✓ Added category: {cat_data['name']}")
            else:
                existing_category = session.query(Category).filter_by(name=cat_data["name"]).first()
                category_objects[cat_data["name"]] = existing_category
                print(f"  → Category already exists: {cat_data['name']}")
        
        # Add sample menu items
        print("Adding sample menu items...")
        menu_items_data = [
            # Breakfast
            {
                "name": "Continental Breakfast",
                "description": "Fresh pastries, fruit, yogurt, and coffee",
                "price": 18.50,
                "category": "Breakfast",
                "preparation_time": 10,
                "dietary": "vegetarian"
            },
            {
                "name": "Full English Breakfast",
                "description": "Eggs, bacon, sausages, beans, toast, and hash browns",
                "price": 24.00,
                "category": "Breakfast",
                "preparation_time": 15
            },
            # Appetizers
            {
                "name": "Caesar Salad",
                "description": "Crisp romaine lettuce with parmesan and croutons",
                "price": 14.00,
                "category": "Appetizers",
                "preparation_time": 8,
                "dietary": "vegetarian"
            },
            {
                "name": "Chicken Wings",
                "description": "Spicy buffalo wings with blue cheese dip",
                "price": 16.50,
                "category": "Appetizers",
                "preparation_time": 12
            },
            # Main Courses
            {
                "name": "Grilled Salmon",
                "description": "Fresh Atlantic salmon with vegetables and rice",
                "price": 28.00,
                "category": "Main Courses",
                "preparation_time": 20,
                "dietary": "gluten-free"
            },
            {
                "name": "Beef Tenderloin",
                "description": "Prime beef with mashed potatoes and seasonal vegetables",
                "price": 35.00,
                "category": "Main Courses",
                "preparation_time": 25
            },
            # Desserts
            {
                "name": "Chocolate Lava Cake",
                "description": "Warm chocolate cake with molten center and vanilla ice cream",
                "price": 12.00,
                "category": "Desserts",
                "preparation_time": 8,
                "dietary": "vegetarian"
            },
            {
                "name": "Tiramisu",
                "description": "Classic Italian dessert with coffee and mascarpone",
                "price": 10.50,
                "category": "Desserts",
                "preparation_time": 5,
                "dietary": "vegetarian"
            },
            # Beverages
            {
                "name": "Fresh Orange Juice",
                "description": "Freshly squeezed orange juice",
                "price": 6.00,
                "category": "Beverages",
                "preparation_time": 2,
                "dietary": "vegan,gluten-free"
            },
            {
                "name": "Premium Coffee",
                "description": "Freshly brewed coffee from premium beans",
                "price": 4.50,
                "category": "Beverages",
                "preparation_time": 3,
                "dietary": "vegan,gluten-free"
            }
        ]
        
        for item_data in menu_items_data:
            category_name = item_data.pop("category")
            category = category_objects.get(category_name)
            
            if category and not session.query(MenuItem).filter_by(name=item_data["name"]).first():
                menu_item = MenuItem(
                    category_id=category.id,
                    **item_data
                )
                session.add(menu_item)
                print(f"  ✓ Added menu item: {item_data['name']}")
            elif not category:
                print(f"  ✗ Category not found for: {item_data['name']}")
            else:
                print(f"  → Menu item already exists: {item_data['name']}")
        
        session.commit()
        print("\n🎉 Database initialized successfully!")
        
        # Print summary
        category_count = session.query(Category).count()
        menu_item_count = session.query(MenuItem).count()
        print(f"📊 Summary:")
        print(f"   - Categories: {category_count}")
        print(f"   - Menu Items: {menu_item_count}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Initializing Hotel Voice AI Concierge Database...")
    seed_database()
