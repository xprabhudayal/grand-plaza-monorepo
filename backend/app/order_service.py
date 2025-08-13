"""
Order service for voice pipeline integration.
Handles creating orders from voice conversation results.
"""

import asyncio
import aiohttp
import os
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import json
from loguru import logger

class OrderService:
    """Service for managing orders from voice pipeline"""
    
    def __init__(self):
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_endpoint = f"{self.api_base_url}/api/v1/orders"
        
    async def create_order_from_voice(
        self,
        room_number: str,
        guest_name: str,
        items: List[Dict[str, Any]],
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an order from voice conversation data.
        
        Args:
            room_number: Guest's room number
            guest_name: Guest's booking name
            items: List of order items with name, quantity, and special notes
            special_requests: Any special requests from the guest
            
        Returns:
            Created order data with reference ID
        """
        try:
            # First, find or create the guest
            guest_id = await self._get_or_create_guest(room_number, guest_name)
            
            # Prepare order items with menu item IDs
            order_items = []
            for item in items:
                menu_item_id = await self._find_menu_item_id(item['name'])
                if menu_item_id:
                    order_items.append({
                        "menu_item_id": menu_item_id,
                        "quantity": item.get('quantity', 1),
                        "special_notes": item.get('special_notes')
                    })
                else:
                    logger.warning(f"Menu item not found: {item['name']}")
            
            if not order_items:
                raise ValueError("No valid menu items found in order")
            
            # Create the order
            order_data = {
                "guest_id": guest_id,
                "order_items": order_items,
                "special_requests": special_requests,
                "delivery_notes": f"Room {room_number}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint,
                    json=order_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 201:
                        order = await response.json()
                        logger.info(f"Order created successfully: {order['id']}")
                        return order
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create order: {error_text}")
                        raise Exception(f"Order creation failed: {error_text}")
                        
        except Exception as e:
            logger.error(f"Error creating order from voice: {str(e)}")
            raise
    
    async def _get_or_create_guest(self, room_number: str, guest_name: str) -> str:
        """Get existing guest or create a new one"""
        guests_endpoint = f"{self.api_base_url}/api/v1/guests"
        
        async with aiohttp.ClientSession() as session:
            # Try to find existing guest by room number
            async with session.get(f"{guests_endpoint}/room/{room_number}") as response:
                if response.status == 200:
                    guest = await response.json()
                    return guest['id']
            
            # Create new guest if not found
            guest_data = {
                "name": guest_name,
                "email": f"room{room_number}@hotel.local",  # Placeholder email
                "room_number": room_number,
                "check_in_date": datetime.now().isoformat(),
                "check_out_date": (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            async with session.post(
                guests_endpoint,
                json=guest_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 201:
                    guest = await response.json()
                    return guest['id']
                else:
                    # Try to get by email as fallback
                    async with session.get(f"{guests_endpoint}?email={guest_data['email']}") as resp:
                        if resp.status == 200:
                            guests = await resp.json()
                            if guests:
                                return guests[0]['id']
                    
                    error_text = await response.text()
                    raise Exception(f"Failed to create guest: {error_text}")
    
    async def _find_menu_item_id(self, item_name: str) -> Optional[str]:
        """Find menu item ID by name"""
        menu_endpoint = f"{self.api_base_url}/api/v1/menu-items"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(menu_endpoint) as response:
                if response.status == 200:
                    menu_items = await response.json()
                    # Try exact match first
                    for item in menu_items:
                        if item['name'].lower() == item_name.lower():
                            return item['id']
                    
                    # Try partial match
                    for item in menu_items:
                        if item_name.lower() in item['name'].lower():
                            return item['id']
        
        return None
    
    def format_order_confirmation(self, order: Dict[str, Any]) -> str:
        """Format order confirmation message for the guest"""
        total = order.get('total_amount', 0)
        order_id = order.get('id', 'Unknown')
        
        confirmation = f"""
        Your order has been placed successfully!
        
        Order Reference: {order_id[:8].upper()}
        Total Amount: ${total:.2f}
        Estimated Delivery: 20-30 minutes
        
        We'll deliver it to your room shortly. Thank you!
        """
        
        return confirmation.strip()


# Singleton instance
order_service = OrderService()