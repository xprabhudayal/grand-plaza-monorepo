#!/usr/bin/env python3
"""
Quick test script to verify the hotel room service functions work correctly.
Run this before your demo to ensure API calls are working.
"""

import asyncio
import os
from dotenv import load_dotenv

# Import the functions to test
from hotel_room_service_tavus import (
    place_order, add_to_order, validate_room, continue_ordering,
    order_manager, service_cache
)

load_dotenv()

async def test_functions():
    """Test the critical functions to ensure they work"""
    print("🧪 Testing Hotel Room Service Functions...")
    
    # Test 1: Validate room function
    print("\n1. Testing room validation...")
    try:
        result, next_node = await validate_room({"room_number": "999"})
        print(f"✅ validate_room: {result['status']} -> {next_node}")
    except Exception as e:
        print(f"❌ validate_room failed: {e}")
    
    # Test 2: Load menu data
    print("\n2. Testing menu data loading...")
    try:
        await service_cache.refresh_menu_data()
        categories = await service_cache.get_categories()
        menu_items = await service_cache.get_menu_items()
        print(f"✅ Loaded {len(categories)} categories, {len(menu_items)} menu items")
    except Exception as e:
        print(f"❌ Menu loading failed: {e}")
    
    # Test 3: Add item to order
    print("\n3. Testing add to order...")
    try:
        # First ensure we have a guest set
        order_manager.guest_id = "test_guest"
        order_manager.guest_name = "Test User"
        order_manager.room_number = "999"
        
        result, next_node = await add_to_order({
            "item_name": "Caesar Salad", 
            "quantity": 2,
            "special_notes": "No croutons"
        })
        print(f"✅ add_to_order: {result['status']} -> {next_node}")
        print(f"   Order summary: {order_manager.get_summary()}")
    except Exception as e:
        print(f"❌ add_to_order failed: {e}")
    
    # Test 4: Continue ordering
    print("\n4. Testing continue ordering...")
    try:
        result, next_node = await continue_ordering({"response": "no, that's all"})
        print(f"✅ continue_ordering: next_node = {next_node}")
    except Exception as e:
        print(f"❌ continue_ordering failed: {e}")
    
    # Test 5: Place order (this should make API call)
    print("\n5. Testing place order...")
    try:
        result, next_node = await place_order({"confirmation": "yes"})
        print(f"✅ place_order: {result['status']} -> {next_node}")
        if result['status'] == 'success':
            print(f"   Order ID: {result['order_id']}")
        elif result['status'] == 'failed':
            print("   ⚠️  API call failed - check your backend server")
    except Exception as e:
        print(f"❌ place_order failed: {e}")
    
    print(f"\n🎯 Test completed! Check your backend logs for API calls.")
    print(f"Expected logs:")
    print(f"- GET /api/v1/guests/room/999")
    print(f"- GET /api/v1/categories/?is_active=true")
    print(f"- GET /api/v1/menu-items/?is_available=true")  
    print(f"- POST /api/v1/orders/ (if place_order succeeded)")

if __name__ == "__main__":
    asyncio.run(test_functions())
