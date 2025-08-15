"""
Hotel Room Service Voice Pipeline with Tavus Video Avatar Integration
Refactored version with proper flow implementation and database validation
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import re
from datetime import datetime
import json

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.groq.llm import GroqLLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.services.soniox.stt import SonioxSTTService, SonioxInputParams
from pipecat.transcriptions.language import Language

# Import Tavus Video Service
from pipecat.services.tavus.video import TavusVideoService

# Import pipecat_flows with proper error handling
try:
    from pipecat_flows import FlowConfig, FlowManager, FlowResult, FlowArgs
except ImportError as e:
    logger.warning(f"pipecat_flows import issue: {e}. Using fallback implementation.")
    # Fallback implementation for FlowResult
    class FlowResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

sys.path.append(str(Path(__file__).parent.parent))
from runner import configure

# Import OrderStatus enum
sys.path.append(str(Path(__file__).parent))
from app.schemas import OrderStatus

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# ============================================================================
# Global Configuration and Cache
# ============================================================================

class ServiceCache:
    """Cache for API responses to reduce redundant calls"""
    def __init__(self):
        self.categories = None
        self.menu_items = None
        self.guest_info = None
        self.last_update = None
        
    async def get_categories(self, force_refresh=False):
        """Get cached categories or fetch from API"""
        if self.categories is None or force_refresh:
            await self.refresh_menu_data()
        return self.categories
    
    async def get_menu_items(self, force_refresh=False):
        """Get cached menu items or fetch from API"""
        if self.menu_items is None or force_refresh:
            await self.refresh_menu_data()
        return self.menu_items
    
    async def refresh_menu_data(self):
        """Refresh both categories and menu items from API"""
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        async with aiohttp.ClientSession() as session:
            # Fetch categories
            try:
                async with session.get(f"{api_base_url}/api/v1/categories/?is_active=true") as response:
                    if response.status == 200:
                        self.categories = await response.json()
                    else:
                        logger.error(f"Failed to fetch categories: {response.status}")
                        self.categories = []
            except Exception as e:
                logger.error(f"Error fetching categories: {e}")
                self.categories = []
            
            # Fetch menu items
            try:
                async with session.get(f"{api_base_url}/api/v1/menu-items/?is_available=true") as response:
                    if response.status == 200:
                        self.menu_items = await response.json()
                    else:
                        logger.error(f"Failed to fetch menu items: {response.status}")
                        self.menu_items = []
            except Exception as e:
                logger.error(f"Error fetching menu items: {e}")
                self.menu_items = []
        
        self.last_update = datetime.now()

# Global cache instance
service_cache = ServiceCache()

# ============================================================================
# Order Manager Class
# ============================================================================

class OrderManager:
    """Manages the current order state"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the order to initial state"""
        self.guest_id = None
        self.guest_name = None
        self.room_number = None
        self.items = []
        self.special_requests = None
        self.delivery_notes = None
        self.order_id = None
        self.total_amount = 0.0
    
    def add_item(self, menu_item: Dict[str, Any], quantity: int, special_notes: Optional[str] = None):
        """Add an item to the order"""
        item = {
            "menu_item_id": menu_item["id"],
            "name": menu_item["name"],
            "quantity": quantity,
            "unit_price": menu_item["price"],
            "total_price": menu_item["price"] * quantity,
            "special_notes": special_notes
        }
        self.items.append(item)
        self.total_amount += item["total_price"]
        return item
    
    def remove_item(self, item_name: str) -> bool:
        """Remove an item from the order by name"""
        for i, item in enumerate(self.items):
            if item["name"].lower() == item_name.lower():
                self.total_amount -= item["total_price"]
                self.items.pop(i)
                return True
        return False
    
    def get_summary(self) -> str:
        """Get a formatted order summary"""
        if not self.items:
            return "No items in the order yet."
        
        summary = "Order Summary:\n"
        for item in self.items:
            summary += f"- {item['quantity']}x {item['name']} - ${item['total_price']:.2f}"
            if item.get('special_notes'):
                summary += f" (Note: {item['special_notes']})"
            summary += "\n"
        
        summary += f"\nTotal: ${self.total_amount:.2f}"
        
        if self.special_requests:
            summary += f"\nSpecial Requests: {self.special_requests}"
        
        if self.delivery_notes:
            summary += f"\nDelivery Notes: {self.delivery_notes}"
        
        return summary

# Global order manager instance
order_manager = OrderManager()

# ============================================================================
# API Service Functions
# ============================================================================

async def validate_room_number(room_number: str) -> Optional[Dict[str, Any]]:
    """Validate room number and get guest information"""
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_endpoint = f"{api_base_url}/api/v1/guests/room/{room_number}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint) as response:
                if response.status == 200:
                    guest_info = await response.json()
                    # Cache guest info
                    service_cache.guest_info = guest_info
                    return guest_info
                elif response.status == 404:
                    logger.info(f"No guest found for room {room_number}")
                    return None
                else:
                    logger.error(f"Failed to fetch guest for room {room_number}: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error validating room number: {str(e)}")
        return None



async def create_order_api(guest_id: str, order_items: List[Dict[str, Any]], 
                          special_requests: Optional[str] = None,
                          delivery_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create an order via API"""
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_endpoint = f"{api_base_url}/api/v1/orders/"
    
    # Format order items for API
    formatted_items = []
    for item in order_items:
        formatted_items.append({
            "menu_item_id": item["menu_item_id"],
            "quantity": item["quantity"],
            "special_notes": item.get("special_notes")
        })
    
    order_data = {
        "guest_id": guest_id,
        "order_items": formatted_items
    }
    
    if special_requests:
        order_data["special_requests"] = special_requests
    
    if delivery_notes:
        order_data["delivery_notes"] = delivery_notes
    
    logger.debug(f"Creating order with data: {order_data}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json=order_data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    logger.error(f"Failed to create order: {response.status}")
                    error_content = await response.text()
                    logger.error(f"Error response: {error_content}")
                    return None
    except Exception as e:
        logger.error(f"Error creating order via API: {str(e)}")
        return None

# ============================================================================
# Utility Functions
# ============================================================================

def convert_text_to_number(text: Union[str, int]) -> int:
    """Convert text numbers to integers (e.g., 'two' -> 2)"""
    if isinstance(text, int):
        return text
    
    if isinstance(text, str) and text.isdigit():
        return int(text)
    
    text_to_num = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
        'eighty': 80, 'ninety': 90, 'hundred': 100
    }
    
    if not isinstance(text, str):
        return 1
    
    text = text.lower().strip()
    
    if text in text_to_num:
        return text_to_num[text]
    
    # Handle compound numbers
    if '-' in text:
        parts = text.split('-')
        if len(parts) == 2 and parts[0] in text_to_num and parts[1] in text_to_num:
            return text_to_num[parts[0]] + text_to_num[parts[1]]
    
    # Handle "a" or "an" as 1
    if text in ['a', 'an']:
        return 1
    
    # Try to extract numbers from text
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    
    return 1

def find_menu_item_by_name(item_name: str, menu_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find a menu item by name with fuzzy matching"""
    item_name_lower = item_name.lower()
    
    # Try exact match first
    for item in menu_items:
        if item["name"].lower() == item_name_lower:
            return item
    
    # Try partial match
    for item in menu_items:
        if item_name_lower in item["name"].lower() or item["name"].lower() in item_name_lower:
            return item
    
    # Try word-based matching
    item_words = set(item_name_lower.split())
    for item in menu_items:
        menu_words = set(item["name"].lower().split())
        if len(item_words.intersection(menu_words)) >= len(item_words) * 0.7:  # 70% word match
            return item
    
    return None

# ============================================================================
# Flow Functions
# ============================================================================

async def request_room_number(args: FlowArgs) -> tuple[None, str]:
    """Request the room number from the guest"""
    return None, "request_room"

async def validate_room(args: FlowArgs) -> tuple[Dict[str, Any], str]:
    """Validate the room number and get guest info"""
    room_number = args["room_number"].strip()
    logger.info(f"validate_room called with room number: '{room_number}'")
    
    guest_info = await validate_room_number(room_number)
    
    if guest_info:
        logger.info(f"Room validation successful for guest: {guest_info['name']} in room {room_number}")
        # Store guest info in order manager
        order_manager.guest_id = guest_info["id"]
        order_manager.guest_name = guest_info["name"]
        order_manager.room_number = room_number
        
        result = {
            "status": "valid",
            "guest_name": guest_info["name"],
            "room_number": room_number
        }
        return result, "welcome_guest"
    else:
        logger.warning(f"Room validation failed for room: {room_number}")
        result = {
            "status": "invalid",
            "room_number": room_number
        }
        return result, "invalid_room"

async def show_categories(args: FlowArgs) -> tuple[Dict[str, Any], str]:
    """Show menu categories to the guest"""
    categories = await service_cache.get_categories()
    
    result = {
        "categories": [cat["name"] for cat in categories if cat.get("is_active", True)]
    }
    return result, "category_selection"

async def select_category(args: FlowArgs) -> tuple[Dict[str, Any], str]:
    """Select a category and show its items"""
    category_name = args["category_name"]
    categories = await service_cache.get_categories()
    menu_items = await service_cache.get_menu_items()
    
    # Find matching category
    category = None
    category_name_lower = category_name.lower()
    
    for cat in categories:
        if cat["name"].lower() == category_name_lower or category_name_lower in cat["name"].lower():
            category = cat
            break
    
    if not category:
        return {"status": "not_found", "category": category_name}, "category_not_found"
    
    # Get items for this category
    category_items = [item for item in menu_items if item.get("category_id") == category["id"]]
    
    result = {
        "category": category["name"],
        "items": [{"name": item["name"], "price": item["price"], "description": item.get("description", "")} 
                  for item in category_items]
    }
    return result, "show_items"

async def add_to_order(args: FlowArgs) -> tuple[Dict[str, Any], str]:
    """Add an item to the order"""
    item_name = args["item_name"]
    quantity = args.get("quantity", 1)
    special_notes = args.get("special_notes")
    
    logger.info(f"add_to_order called: item='{item_name}', quantity={quantity}, notes='{special_notes}'")
    
    menu_items = await service_cache.get_menu_items()
    
    # Find the menu item
    menu_item = find_menu_item_by_name(item_name, menu_items)
    
    if not menu_item:
        logger.warning(f"Menu item not found: '{item_name}'")
        return {"status": "not_found", "item": item_name}, "item_not_found"
    
    # Convert quantity to integer
    quantity_int = convert_text_to_number(quantity)
    
    # Add to order
    order_item = order_manager.add_item(menu_item, quantity_int, special_notes)
    logger.info(f"Added to order: {order_item['name']} x{quantity_int} = ${order_item['total_price']:.2f}")
    
    result = {
        "status": "added",
        "item_name": menu_item["name"],
        "quantity": quantity_int,
        "price": order_item["total_price"],
        "special_notes": special_notes
    }
    return result, "item_added"

async def continue_ordering(args: FlowArgs) -> tuple[None, str]:
    """Check if guest wants to continue ordering"""
    response = args["response"]
    response_lower = response.lower()
    
    logger.info(f"continue_ordering called with response: '{response}'")
    
    if any(word in response_lower for word in ["yes", "yeah", "sure", "more", "add", "continue"]):
        logger.info("Guest wants to continue ordering")
        return None, "category_selection"
    else:
        logger.info("Guest finished ordering, moving to special requests")
        return None, "request_special"

async def set_special_requests(args: FlowArgs) -> tuple[None, str]:
    """Set special requests and delivery notes"""
    requests = args.get("requests")
    notes = args.get("notes")
    
    if requests and requests.lower() not in ["no", "none", "nothing"]:
        order_manager.special_requests = requests
    
    if notes and notes.lower() not in ["no", "none", "nothing"]:
        order_manager.delivery_notes = notes
    
    return None, "confirm_order"

async def place_order(args: FlowArgs) -> tuple[Dict[str, Any], str]:
    """Place the final order"""
    confirmation = args.get("confirmation", "").lower()
    logger.info(f"place_order function called with confirmation: '{confirmation}'")
    
    # Check for negative confirmation
    if confirmation in ["no", "cancel", "stop", "negative"]:
        logger.info("User cancelled the order")
        return {"status": "cancelled"}, "start"
    
    if not order_manager.items:
        logger.warning("Attempting to place empty order")
        return {"status": "empty"}, "empty_order"
    
    logger.info(f"Placing order with {len(order_manager.items)} items for guest {order_manager.guest_id}")
    
    # Create order via API
    order = await create_order_api(
        guest_id=order_manager.guest_id,
        order_items=order_manager.items,
        special_requests=order_manager.special_requests,
        delivery_notes=order_manager.delivery_notes
    )
    
    if order:
        logger.info(f"Order created successfully with ID: {order['id']}")
        result = {
            "status": "success",
            "order_id": order["id"],
            "total_amount": order["total_amount"],
            "estimated_time": "20-30 minutes",
            "items": order_manager.items,
            "special_requests": order_manager.special_requests,
            "delivery_notes": order_manager.delivery_notes
        }
        
        # Store order ID
        order_manager.order_id = order["id"]
        
        return result, "order_complete"
    else:
        logger.error("Failed to create order via API")
        return {"status": "failed"}, "order_failed"

async def end_call(args: FlowArgs) -> tuple[None, str]:
    """End the call properly"""
    return None, "goodbye"

# ============================================================================
# Hotel Room Service Flow Configuration
# ============================================================================

hotel_room_service_flow: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": """You are a professional hotel room service assistant for Grand Plaza Hotel.
                    
                    CRITICAL: You have function-calling capabilities. You MUST use the available functions to progress the conversation.
                    
                    Your available functions:
                    - request_room_number: Use when guest needs to provide room number
                    - validate_room: Use when guest provides room number  
                    - show_categories: Use to display menu categories
                    - select_category: Use when guest selects a category
                    - add_to_order: Use when guest wants to order specific items
                    - continue_ordering: Use when asking if guest wants more items
                    - set_special_requests: Use to capture special requests
                    - place_order: Use ONLY when guest explicitly confirms order with "yes", "okay", "confirm"
                    - end_call: Use to end conversation
                    
                    Be concise, polite, and efficient. Always use functions to progress the conversation."""
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": """Greet the guest briefly: "Good [morning/afternoon/evening], this is room service at Grand Plaza Hotel."
                    Then immediately ask: "May I have your room number, please?" 
                    
                    IMPORTANT: You MUST use the request_room_number function to progress the conversation.
                    Do not mention any menu items or categories yet."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "request_room_number",
                        "description": "Request the room number from guest",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        "handler": request_room_number
                    }
                }
            ],
        },
        "request_room": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The guest needs to provide their room number. Listen for their response and capture the room number.
                    
                    IMPORTANT: You MUST use the validate_room function with the room number they provide.
                    If unclear, politely ask them to repeat it, then use the function."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "validate_room",
                        "description": "Validate room number and get guest information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "room_number": {"type": "string", "description": "The room number provided by guest"}
                            },
                            "required": ["room_number"]
                        },
                        "handler": validate_room
                    }
                }
            ],
        },
        "invalid_room": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The room number provided is not valid or no guest is registered to that room.
                    Say: "I'm sorry, I couldn't find a guest registered to room {room_number}. Could you please verify your room number?"
                    Listen for their response and try to validate again."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "validate_room",
                        "description": "Validate room number and get guest information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "room_number": {"type": "string", "description": "The room number to validate"}
                            },
                            "required": ["room_number"]
                        },
                        "handler": validate_room
                    }
                }
            ],
        },
        "welcome_guest": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Thank the guest by name: "Thank you, {guest_name}."
                    Then briefly mention: "We have the following categories available: Breakfast, Appetizers, Salads, Main Courses, Sandwiches, Desserts, and Beverages."
                    Ask: "Which category would you like to explore?" 
                    
                    IMPORTANT: You MUST use the select_category function when the guest chooses a category.
                    Keep it concise - do not list individual items."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "show_categories",
                        "description": "Show available menu categories",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        "handler": show_categories
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "select_category",
                        "description": "Select a menu category to browse",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category_name": {"type": "string", "description": "The name of the category to select"}
                            },
                            "required": ["category_name"]
                        },
                        "handler": select_category
                    }
                }
            ],
        },
        "category_selection": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The guest needs to select a category. Available categories are:
                    Breakfast, Appetizers, Salads, Main Courses, Sandwiches, Desserts, Beverages.
                    
                    IMPORTANT: You MUST use the select_category function when they choose.
                    Listen for their selection and use the function to show items from that category.
                    If they ask for something specific, help them find the right category first."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "select_category",
                        "description": "Select a menu category to browse",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category_name": {"type": "string", "description": "The name of the category to select"}
                            },
                            "required": ["category_name"]
                        },
                        "handler": select_category
                    }
                }
            ],
        },
        "category_not_found": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The category wasn't found. Say: "I couldn't find that category. 
                    We have: Breakfast, Appetizers, Salads, Main Courses, Sandwiches, Desserts, and Beverages.
                    Which would you like?" Keep it brief."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "select_category",
                        "description": "Select a menu category to browse",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category_name": {"type": "string", "description": "The name of the category to select"}
                            },
                            "required": ["category_name"]
                        },
                        "handler": select_category
                    }
                }
            ],
        },
        "show_items": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """List the items in the selected category with prices. Be concise - just name and price.
                    For example: "In {category}, we have: [item1] at $[price1], [item2] at $[price2]..."
                    Then ask: "What would you like to order?" 
                    
                    IMPORTANT: You MUST use the add_to_order function when guest wants to order items.
                    You can also use select_category function if they want a different category.
                    Do not provide lengthy descriptions unless asked."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "add_to_order",
                        "description": "Add a menu item to the order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "item_name": {"type": "string", "description": "The name of the item to add"},
                                "quantity": {"type": "integer", "description": "The quantity of items to add", "default": 1},
                                "special_notes": {"type": "string", "description": "Any special notes for the item"}
                            },
                            "required": ["item_name"]
                        },
                        "handler": add_to_order
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "select_category",
                        "description": "Select a different menu category",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category_name": {"type": "string", "description": "The name of the category to select"}
                            },
                            "required": ["category_name"]
                        },
                        "handler": select_category
                    }
                }
            ],
        },
        "item_not_found": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The item wasn't found. Say briefly: "I couldn't find that item. 
                    Would you like me to show the items again, or would you like to try a different category?" """
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "select_category",
                        "description": "Select a menu category to browse",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category_name": {"type": "string", "description": "The name of the category to select"}
                            },
                            "required": ["category_name"]
                        },
                        "handler": select_category
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "add_to_order",
                        "description": "Add a menu item to the order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "item_name": {"type": "string", "description": "The name of the item to add"},
                                "quantity": {"type": "integer", "description": "The quantity of items", "default": 1},
                                "special_notes": {"type": "string", "description": "Special notes for the item"}
                            },
                            "required": ["item_name"]
                        },
                        "handler": add_to_order
                    }
                }
            ],
        },
        "item_added": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Confirm the item briefly: "Added {quantity} {item_name} to your order."
                    If there were special notes, acknowledge them.
                    Then ask: "Would you like to add anything else?" 
                    
                    IMPORTANT: You MUST use the continue_ordering function to capture their response.
                    Keep it very brief."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "continue_ordering",
                        "description": "Check if guest wants to continue ordering",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "response": {"type": "string", "description": "Guest's response about continuing"}
                            },
                            "required": ["response"]
                        },
                        "handler": continue_ordering
                    }
                }
            ],
        },
        "request_special": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Ask concisely: "Any special requests for your order?" 
                    Wait for response.
                    Then ask: "Any delivery instructions for your room?"
                    
                    IMPORTANT: You MUST use the set_special_requests function to capture both responses.
                    Capture both responses together in one function call."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "set_special_requests",
                        "description": "Set special requests and delivery notes",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "requests": {"type": "string", "description": "Special requests for the order"},
                                "notes": {"type": "string", "description": "Delivery notes for the room"}
                            },
                            "required": []
                        },
                        "handler": set_special_requests
                    }
                }
            ],
        },
        "confirm_order": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Provide a concise order summary and ask for confirmation:
                    "Your order: [list items with quantities and total price].
                    Total: $[amount].
                    {Include special requests/delivery notes if any}
                    
                    Do you want me to place this order? Please say yes to confirm or no to cancel."
                    
                    CRITICAL: You MUST use the place_order function when the user says YES, OKAY, CONFIRM, or similar.
                    Keep it brief and clear."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "place_order",
                        "description": "Place the final order when user confirms with yes, okay, confirm, or similar affirmative response",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "confirmation": {
                                    "type": "string",
                                    "description": "User's confirmation response (yes/no/okay/confirm/cancel)"
                                }
                            },
                            "required": ["confirmation"]
                        },
                        "handler": place_order
                    }
                }
            ],
        },
        "empty_order": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """There are no items in the order. Say: "You haven't added any items yet. 
                    Would you like to browse our menu?" """
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "show_categories",
                        "description": "Show menu categories to browse",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        "handler": show_categories
                    }
                }
            ],
        },
        "order_failed": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """There was an error placing the order. Say: "I apologize, there was an error processing your order. 
                    Please call the front desk for assistance. Thank you." Then end the call."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "end_call",
                        "description": "End the call properly",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        "handler": end_call
                    }
                }
            ],
        },
        "order_complete": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Confirm the order successfully: "Your order has been placed. 
                    Your order reference is {order_id}. 
                    It will be delivered to room {room_number} in approximately {estimated_time}.
                    Thank you for your order, {guest_name}. Have a wonderful day."
                    Then end the call."""
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "end_call",
                        "description": "End the call properly",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        "handler": end_call
                    }
                }
            ],
        },
        "goodbye": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """The conversation is ending. Say goodbye briefly and end the call."""
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}

# ============================================================================
# Main Application
# ============================================================================

async def main():
    """Main function to set up and run the hotel room service bot with Tavus video avatar"""
    
    try:
        async with aiohttp.ClientSession() as session:
            (room_url, _) = await configure(session)

            # Initialize transport with video enabled for Tavus
            transport = DailyTransport(
                room_url,
                None,
                "Hotel Concierge",
                DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    video_out_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(),
                ),
            )

            # Initialize STT service
            soniox_key = os.getenv("SONIOX_API_KEY")
            if soniox_key:
                logger.info("Using Soniox STT service")
                stt = SonioxSTTService(
                    api_key=soniox_key,
                    params=SonioxInputParams(
                        language_hints=[Language.EN],
                    ),
                )
            else:
                logger.info("Using Deepgram STT service")
                stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

            # Initialize TTS service
            cartesia_key = os.getenv("CARTESIA_API_KEY")
            if cartesia_key:
                logger.info("Using Cartesia TTS service")
                tts = CartesiaTTSService(
                    api_key=cartesia_key,
                    voice_id="820a3788-2b37-4d21-847a-b65d8a68c99a",
                )
            else:
                logger.info("Using Deepgram TTS service")
                tts = DeepgramTTSService(
                    api_key=os.getenv("DEEPGRAM_API_KEY"),
                    voice="aura-angus-en",
                )

            # Initialize LLM service
            llm = GroqLLMService(
                api_key=os.getenv("GROQ_API_KEY"),
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.7,
                max_tokens=512,
            )

            # Initialize Tavus Video Service
            tavus_api_key = os.getenv("TAVUS_API_KEY")
            tavus_replica_id = os.getenv("TAVUS_REPLICA_ID")
            
            if tavus_api_key and tavus_replica_id:
                logger.info("Initializing Tavus video avatar service...")
                tavus_service = TavusVideoService(
                    api_key=tavus_api_key,
                    replica_id=tavus_replica_id,
                    session=session,
                )
            else:
                logger.warning("Tavus API credentials not found. Continuing without video avatar...")
                tavus_service = None

            # Set up context and aggregator
            context = OpenAILLMContext()
            context_aggregator = llm.create_context_aggregator(context)

            # Build pipeline
            if tavus_service:
                pipeline = Pipeline([
                    transport.input(),
                    stt,
                    context_aggregator.user(),
                    llm,
                    tts,
                    tavus_service,
                    transport.output(),
                    context_aggregator.assistant(),
                ])
                logger.info("Pipeline created with Tavus video avatar")
            else:
                pipeline = Pipeline([
                    transport.input(),
                    stt,
                    context_aggregator.user(),
                    llm,
                    tts,
                    transport.output(),
                    context_aggregator.assistant(),
                ])
                logger.info("Pipeline created without video avatar")

            task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

            # Initialize flow manager
            flow_manager = FlowManager(
                task=task,
                llm=llm,
                context_aggregator=context_aggregator,
                flow_config=hotel_room_service_flow,
            )

            # Pre-load menu data into cache
            logger.info("Pre-loading menu data...")
            await service_cache.refresh_menu_data()

            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                await transport.capture_participant_transcription(participant["id"])
                logger.debug("First participant joined - initializing flow")
                
                # Add system context
                context.add_message({
                    "role": "system",
                    "content": "You are a professional hotel room service assistant. Be concise and efficient."
                })
                
                # Add avatar context if using Tavus
                if tavus_service:
                    context.add_message({
                        "role": "system",
                        "content": "You are appearing as a video avatar. Maintain professional demeanor and eye contact."
                    })
                
                # Initialize the flow
                await flow_manager.initialize()

            # Handle Tavus-specific events
            if tavus_service:
                @transport.event_handler("on_participant_updated")
                async def on_participant_updated(transport, participant):
                    if participant.get("info", {}).get("userName") == "Tavus":
                        await transport.update_subscriptions(
                            participant_settings={
                                participant["id"]: {
                                    "media": "video"
                                }
                            }
                        )

            @transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                logger.info(f"Participant left: {participant['id']}, reason: {reason}")
                
                # Cancel the task
                task.cancel()

            # Run the pipeline
            runner = PipelineRunner()
            await runner.run(task)
            
    except asyncio.CancelledError:
        logger.info("Voice session was cancelled")
    except Exception as e:
        logger.error(f"Error in voice pipeline: {e}")
        raise
    finally:
        # Clean up
        logger.info("Cleaning up voice session")
        
        # Reset order manager for next session
        order_manager.reset()
        
        # Log session completion
        logger.info("Voice session completed")

if __name__ == "__main__":
    asyncio.run(main())