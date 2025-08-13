#!/usr/bin/env python3
"""
Test script to verify order storage functionality
"""

import asyncio
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.order_service import order_service
from loguru import logger

async def test_order_creation():
    """Test creating an order through the order service"""
    
    logger.info("Testing order creation from voice pipeline...")
    
    # Sample order data simulating voice conversation result
    test_order_data = {
        "room_number": "101",
        "guest_name": "John Doe",
        "items": [
            {
                "name": "Caesar Salad",
                "quantity": 1,
                "special_notes": "No croutons please"
            },
            {
                "name": "Grilled Salmon",
                "quantity": 2,
                "special_notes": "Well done"
            },
            {
                "name": "Chocolate Cake",
                "quantity": 1,
                "special_notes": None
            }
        ],
        "special_requests": "Please deliver with extra napkins and utensils"
    }
    
    try:
        # Create the order
        order = await order_service.create_order_from_voice(
            room_number=test_order_data["room_number"],
            guest_name=test_order_data["guest_name"],
            items=test_order_data["items"],
            special_requests=test_order_data["special_requests"]
        )
        
        logger.success(f"✅ Order created successfully!")
        logger.info(f"Order ID: {order['id']}")
        logger.info(f"Total Amount: ${order.get('total_amount', 0):.2f}")
        
        # Format and display confirmation
        confirmation = order_service.format_order_confirmation(order)
        logger.info(f"Confirmation Message:\n{confirmation}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create order: {str(e)}")
        return False

async def check_api_connectivity():
    """Check if the API server is running"""
    import aiohttp
    
    api_url = "http://localhost:8000/health"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.success(f"✅ API server is running: {data}")
                    return True
                else:
                    logger.error(f"❌ API server returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to API server: {str(e)}")
        logger.info("Please make sure the FastAPI server is running:")
        logger.info("Run: uvicorn app.main:app --reload")
        return False

async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("ORDER STORAGE INTEGRATION TEST")
    logger.info("=" * 60)
    
    # First check API connectivity
    if not await check_api_connectivity():
        logger.error("Please start the API server first!")
        sys.exit(1)
    
    # Run the order creation test
    success = await test_order_creation()
    
    if success:
        logger.success("\n✅ All tests passed! Orders are being stored in the database.")
        logger.info("You can verify the order in the database by:")
        logger.info("1. Using a SQLite browser to open database.db")
        logger.info("2. Calling GET http://localhost:8000/api/v1/orders")
    else:
        logger.error("\n❌ Test failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())