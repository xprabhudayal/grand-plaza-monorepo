"""
Database seeding script for hotel room service menu
Populates categories and menu items from menu_data.py
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Category, MenuItem
from data.menu_data import HOTEL_MENU_DATA
import os
from dotenv import load_dotenv

load_dotenv()

def create_database_tables():
    """Create all database tables"""
    from app.database import engine
    Base.metadata.create_all(bind=engine)
    return engine

def seed_menu_data():
    """Seed the database with menu categories and items"""
    engine = create_database_tables()
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Clear existing data (optional)
        print("Clearing existing menu data...")
        db.query(MenuItem).delete()
        db.query(Category).delete()
        db.commit()
        
        print("Seeding categories and menu items...")
        
        for category_data in HOTEL_MENU_DATA["categories"]:
            # Create category
            category = Category(
                name=category_data["name"],
                description=category_data["description"],
                display_order=category_data["display_order"],
                is_active=category_data["is_active"]
            )
            db.add(category)
            db.flush()  # Get the category ID without committing
            
            print(f"Added category: {category.name}")
            
            # Create menu items for this category
            for item_data in category_data["items"]:
                menu_item = MenuItem(
                    name=item_data["name"],
                    description=item_data["description"],
                    price=item_data["price"],
                    category_id=category.id,
                    is_available=item_data["is_available"],
                    preparation_time=item_data["preparation_time"],
                    dietary=item_data["dietary"]
                )
                db.add(menu_item)
                print(f"  Added item: {menu_item.name} - ${menu_item.price}")
        
        db.commit()
        print("\n✅ Database seeded successfully!")
        
        # Print summary
        category_count = db.query(Category).count()
        item_count = db.query(MenuItem).count()
        print(f"📊 Summary: {category_count} categories, {item_count} menu items")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_sample_guest():
    """Create a sample guest for testing"""
    engine = create_database_tables()
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        from app.models import Guest
        from datetime import datetime
        
        # Check if sample guest already exists
        existing_guest = db.query(Guest).filter(Guest.email == "john.doe@example.com").first()
        if existing_guest:
            print("Sample guest already exists")
            return
        
        sample_guest = Guest(
            name="John Doe",
            email="john.doe@example.com",
            phone_number="+1-555-0123",
            room_number="101",
            check_in_date=datetime.now(),
            is_active=True
        )
        
        db.add(sample_guest)
        db.commit()
        print(f"✅ Created sample guest: {sample_guest.name} in room {sample_guest.room_number}")
        
    except Exception as e:
        print(f"❌ Error creating sample guest: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🏨 Hotel Room Service - Database Seeding")
    print("=" * 50)
    
    seed_menu_data()
    create_sample_guest()
    
    print("\n🎉 Database setup complete!")
    print("You can now start the FastAPI server and test the endpoints.")