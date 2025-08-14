"""
Hotel Room Service Voice Pipeline with Tavus Video Avatar Integration
This version integrates Tavus video avatars for a visual conversational experience
while maintaining all hotel room service functionality
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Union
import re

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
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.services.soniox.stt import SonioxSTTService, SonioxInputParams
from pipecat.transcriptions.language import Language

# Import Tavus Video Service
from pipecat.services.tavus.video import TavusVideoService

# For LLM, we can use Groq or Perplexity
# from pipecat.services.perplexity.llm import PerplexityLLMService

# Import only needed parts from pipecat_flows to avoid loading all LLM services
try:
    from pipecat_flows import FlowConfig, FlowManager, FlowResult
except ImportError as e:
    # If pipecat_flows has dependency issues, we can create minimal versions
    if "anthropic" in str(e):
        print("⚠️  pipecat_flows has optional dependencies. Creating minimal flow manager...")
        # Define minimal flow classes inline
        class FlowResult:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class FlowManager:
            def __init__(self, task, llm, context_aggregator, flow_config):
                self.task = task
                self.llm = llm
                self.context_aggregator = context_aggregator
                self.flow_config = flow_config
            
            async def initialize(self):
                # Start with greeting node
                await self._start_flow("greeting")
            
            async def _start_flow(self, node_name):
                # Basic flow implementation
                pass
        
        FlowConfig = dict  # FlowConfig is just a dict
    else:
        raise

sys.path.append(str(Path(__file__).parent.parent))
from runner import configure

# Import hotel-specific data
sys.path.append(str(Path(__file__).parent))
from data.menu_data import get_menu_categories, get_menu_items_by_category

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Function to get guest by room number
async def get_guest_by_room_number(room_number: str) -> Dict[str, Any]:
    """Get guest information by room number via API"""
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_endpoint = f"{api_base_url}/api/v1/guests/room/{room_number}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch guest for room {room_number}: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error getting guest by room number via API: {str(e)}")
        return None

# Function to search menu items via API
async def search_menu_items_api(query: str) -> List[Dict[str, Any]]:
    """Search menu items by name or description via API"""
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_endpoint = f"{api_base_url}/api/v1/menu-items/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint) as response:
                if response.status == 200:
                    menu_items = await response.json()
                    query = query.lower()
                    results = []
                    
                    for item in menu_items:
                        if (query in item["name"].lower() or 
                            query in item["description"].lower() or
                            (item.get("dietary") and query in item["dietary"].lower())):
                            results.append(item)
                    
                    return results
                else:
                    logger.error(f"Failed to fetch menu items: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error searching menu items via API: {str(e)}")
        return []

# Function to create an order via API
async def create_order_api(guest_id: str, order_items: List[Dict[str, Any]], special_requests: str = None) -> Dict[str, Any]:
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
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json=order_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to create order: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error creating order via API: {str(e)}")
        return None

# Text-to-number conversion for STT post-processing
def convert_text_to_number(text: Union[str, int]) -> int:
    """Convert text numbers to integers (e.g., 'two' -> 2, 'twenty-one' -> 21)"""
    if isinstance(text, int):
        return text
    
    if isinstance(text, str) and text.isdigit():
        return int(text)
    
    # Dictionary for text to number conversion
    text_to_num = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
        'eighty': 80, 'ninety': 90, 'hundred': 100
    }
    
    if not isinstance(text, str):
        return 1  # Default to 1 if invalid input
    
    text = text.lower().strip()
    
    # Handle simple cases
    if text in text_to_num:
        return text_to_num[text]
    
    # Handle compound numbers like "twenty-one", "thirty-five"
    if '-' in text:
        parts = text.split('-')
        if len(parts) == 2 and parts[0] in text_to_num and parts[1] in text_to_num:
            return text_to_num[parts[0]] + text_to_num[parts[1]]
    
    # Handle "a" or "an" as 1
    if text in ['a', 'an']:
        return 1
    
    # Try to extract numbers from text using regex
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    
    # Default to 1 if no conversion possible
    return 1

# Hotel Room Service Flow Result Types
# We'll define the structure but functions will return dictionaries
MenuSearchResult = FlowResult
CategorySelectResult = FlowResult
OrderItemResult = FlowResult
OrderSummaryResult = FlowResult

# Flow Functions
async def browse_menu(flow_manager: FlowManager) -> tuple[None, str]:
    """Start browsing the menu"""
    # Get categories from API for the prompt
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    categories_endpoint = f"{api_base_url}/api/v1/categories/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(categories_endpoint) as response:
                if response.status == 200:
                    categories = await response.json()
                    # Update the flow configuration with actual categories
                    # This would require a more complex implementation to dynamically update prompts
                    pass
    except Exception as e:
        logger.error(f"Error fetching categories via API: {str(e)}")
    
    return None, "menu_browse"

async def search_items(flow_manager: FlowManager, query: str) -> tuple[Dict[str, Any], str]:
    """Search for menu items by name or description"""
    results = await search_menu_items_api(query)
    search_result = {
        "query": query,
        "results": results,
        "status": "success"
    }
    return search_result, "show_search_results"

async def select_category(flow_manager: FlowManager, category_name: str) -> tuple[Dict[str, Any], str]:
    """Select a specific menu category to browse"""
    # First get categories from API to validate
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    categories_endpoint = f"{api_base_url}/api/v1/categories/"
    menu_items_endpoint = f"{api_base_url}/api/v1/menu-items/"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get categories
            async with session.get(categories_endpoint) as response:
                if response.status == 200:
                    categories = await response.json()
                else:
                    logger.error(f"Failed to fetch categories: {response.status}")
                    categories = []
            
            # Find the matching category
            category = next((cat for cat in categories if cat["name"].lower() == category_name.lower()), None)
            
            if not category:
                # Try partial match
                category = next((cat for cat in categories if category_name.lower() in cat["name"].lower()), None)
            
            if category:
                # Get menu items for this category
                async with session.get(f"{menu_items_endpoint}?category_id={category['id']}") as response:
                    if response.status == 200:
                        items = await response.json()
                    else:
                        logger.error(f"Failed to fetch menu items: {response.status}")
                        items = []
                
                category_result = {
                    "category_name": category["name"], 
                    "items": items,
                    "status": "success"
                }
                return category_result, "show_category_items"
            else:
                # Category not found, go back to menu browsing
                return None, "menu_browse"
    except Exception as e:
        logger.error(f"Error selecting category via API: {str(e)}")
        return None, "menu_browse"

async def add_item_to_order(
    flow_manager: FlowManager, 
    item_name: str, 
    quantity: Union[str, int] = 1,
    special_notes: str = None
) -> tuple[Dict[str, Any], str]:
    """Add an item to the current order"""
    # Convert quantity from text to number
    quantity_int = convert_text_to_number(quantity)
    
    # Find the item in the menu to get the price via API
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_endpoint = f"{api_base_url}/api/v1/menu-items/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint) as response:
                if response.status == 200:
                    all_items = await response.json()
                else:
                    logger.error(f"Failed to fetch menu items: {response.status}")
                    all_items = []
    except Exception as e:
        logger.error(f"Error fetching menu items via API: {str(e)}")
        all_items = []
    
    menu_item = next((item for item in all_items if item["name"].lower() == item_name.lower()), None)
    
    if not menu_item:
        # Try partial match
        menu_item = next((item for item in all_items if item_name.lower() in item["name"].lower()), None)
    
    if menu_item:
        order_item = {
            "item_name": menu_item["name"],
            "quantity": quantity_int,
            "price": menu_item["price"] * quantity_int,
            "special_notes": special_notes,
            "status": "success"
        }
        
        # Track items for database storage
        if not hasattr(flow_manager, 'current_order'):
            flow_manager.current_order = {'items': [], 'room_number': None, 'guest_name': None}
        
        flow_manager.current_order['items'].append({
            'name': menu_item["name"],
            'menu_item_id': menu_item["id"],
            'quantity': quantity_int,
            'special_notes': special_notes
        })
        
        return order_item, "item_added"
    else:
        # Item not found, go back to menu
        return None, "menu_browse"

async def review_current_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Review the items in the current order"""
    return None, "order_review"

async def confirm_final_order(flow_manager: FlowManager) -> tuple[Dict[str, Any], str]:
    """Confirm and place the final order"""
    try:
        # Get room number from environment or flow context
        room_number = os.getenv("GUEST_ROOM_NUMBER", "101")  # Default or from environment
        
        # Get guest information
        guest = await get_guest_by_room_number(room_number)
        if not guest:
            logger.error(f"Could not find guest for room {room_number}")
            return None, "order_placed"  # Still complete the flow but log the error
        
        guest_id = guest["id"]
        
        # Extract order items from flow context
        if not hasattr(flow_manager, 'current_order') or not flow_manager.current_order['items']:
            logger.warning("No items in order to save")
            return None, "order_placed"
        
        # Format items for API
        order_items = []
        menu_items = await search_menu_items_api("")  # Get all menu items to map names to IDs
        
        for item in flow_manager.current_order['items']:
            # Find the menu item ID by name
            menu_item = next((mi for mi in menu_items if mi["name"].lower() == item['name'].lower()), None)
            if menu_item:
                order_items.append({
                    "menu_item_id": menu_item["id"],
                    "quantity": item['quantity'],
                    "special_notes": item.get('special_notes')
                })
            else:
                logger.warning(f"Could not find menu item ID for {item['name']}")
        
        if not order_items:
            logger.error("No valid items found for order")
            return None, "order_placed"
        
        # Create order via API
        special_requests = getattr(flow_manager, 'special_requests', None)
        order = await create_order_api(
            guest_id=guest_id,
            order_items=order_items,
            special_requests=special_requests
        )
        
        if order:
            # Store order ID for reference
            flow_manager.order_id = order['id']
            logger.info(f"Order created via API: {order['id']}")
        else:
            logger.error("Failed to create order via API")
            
    except Exception as e:
        logger.error(f"Failed to create order: {str(e)}")
        # Continue with flow even if storage fails
    
    return None, "order_placed"

async def modify_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Make changes to the current order"""
    return None, "menu_browse"

async def cancel_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Cancel the entire order"""
    return None, "order_cancelled"

# Hotel Room Service Flow Configuration with Avatar-friendly prompts
hotel_room_service_flow: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": """You are a professional and friendly hotel room service assistant with a warm, welcoming personality. 
                    You help guests order food and beverages from our comprehensive room service menu. 
                    
                    Always be warm, courteous, and efficient. Speak naturally and conversationally, as if you're having a video call with the guest.
                    Use appropriate facial expressions and maintain eye contact through the camera. Keep responses concise but helpful."""
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": """Greet the guest warmly with a smile and ask how you can help them with their room service order today. 
                    
                    Let them know they can:
                    - Browse our menu categories (Breakfast, Appetizers, Salads, Main Courses, Sandwiches, Desserts, Beverages)
                    - Search for specific items
                    - Ask about dietary options
                    
                    Ask what they'd like to do first. Remember to maintain friendly eye contact and a welcoming demeanor."""
                }
            ],
            "functions": [browse_menu, search_items],
        },
        "menu_browse": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Help the guest navigate our room service menu with enthusiasm. Our categories are:
                    
                    🍳 Breakfast - Available 24/7 (Continental, American, Avocado Toast, Pancakes, Oatmeal)
                    🥗 Appetizers - Light bites (Shrimp Cocktail, Wings, Hummus, Nachos)  
                    🥬 Salads - Fresh options (Caesar, Mediterranean, Quinoa Bowl)
                    🍽️ Main Courses - Hearty entrees (Salmon, Steak, Chicken Parmesan, Curry)
                    🥪 Sandwiches - Gourmet options (Club, Burger, Veggie Burger, Reuben)
                    🍰 Desserts - Sweet treats (Chocolate Cake, Cheesecake, Ice Cream)
                    ☕ Beverages - Hot & cold drinks (Coffee, Tea, Juices, Wine, Beer)
                    
                    Ask which category interests them or if they'd like to search for something specific. 
                    Show genuine interest in helping them find the perfect meal."""
                }
            ],
            "functions": [select_category, search_items, add_item_to_order, review_current_order],
        },
        "show_search_results": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Present the search results clearly with names, prices, and brief descriptions. 
                    
                    If items have dietary information (vegetarian, vegan, gluten-free), mention it enthusiastically. 
                    Ask if they'd like to add any of these items to their order or search for something else.
                    Express excitement about their choices when appropriate."""
                }
            ],
            "functions": [add_item_to_order, search_items, select_category, review_current_order],
        },
        "show_category_items": {
            "task_messages": [
                {
                    "role": "system", 
                    "content": """Show the items in the selected category with prices and descriptions enthusiastically. 
                    
                    Highlight any special dietary options. Ask if they'd like to add any items to their order, 
                    browse other categories, or need more details about specific items.
                    Use positive body language and facial expressions to convey the appeal of the dishes."""
                }
            ],
            "functions": [add_item_to_order, select_category, search_items, review_current_order],
        },
        "item_added": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Confirm the item has been added to their order with quantity and any special notes, showing satisfaction with their choice.
                    
                    Ask if they'd like to:
                    - Add more items
                    - Review their current order
                    - Browse other menu categories
                    - Place their order
                    
                    Maintain a helpful and encouraging demeanor."""
                }
            ],
            "functions": [add_item_to_order, browse_menu, review_current_order, confirm_final_order],
        },
        "order_review": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Review their complete order including all items, quantities, prices, and total amount with care and attention.
                    
                    Provide an estimated delivery time (typically 20-45 minutes depending on items).
                    Ask if they want to:
                    - Confirm and place the order
                    - Add more items  
                    - Remove or modify items
                    - Cancel the order
                    
                    Show attentiveness and readiness to help with any changes."""
                }
            ],
            "functions": [confirm_final_order, add_item_to_order, modify_order, cancel_order],
        },
        "order_placed": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Thank the guest warmly for their order and confirm it has been placed with the kitchen.
                    
                    If an order confirmation is available, share the reference number.
                    Provide:
                    - Order confirmation with reference ID (if available)
                    - Estimated delivery time (20-30 minutes)
                    - Room number confirmation
                    - Let them know they can call back if they need anything else
                    
                    End with a warm smile and professional goodbye. Thank them for choosing our room service."""
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
        "order_cancelled": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Politely acknowledge the order cancellation with understanding and ask if there's anything else you can help them with.
                    
                    Let them know they can always call back when they're ready to place an order.
                    Maintain a friendly and professional demeanor despite the cancellation."""
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}

async def main():
    """Main function to set up and run the hotel room service bot with Tavus video avatar"""
    async with aiohttp.ClientSession() as session:
        (room_url, _) = await configure(session)

        # Initialize transport with video enabled for Tavus
        transport = DailyTransport(
            room_url,
            None,
            "Hotel Concierge",  # Name displayed for the avatar
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                video_out_enabled=True,  # Enable video output for Tavus
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

        # Initialize TTS service (Cartesia works well with Tavus)
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="820a3788-2b37-4d21-847a-b65d8a68c99a",  # Professional voice
        )

        # Initialize LLM service
        groq_key = os.getenv("GROQ_API_KEY")
        # perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        
        # if perplexity_key:
        #     logger.info("Using Perplexity LLM service")
        #     llm = PerplexityLLMService(
        #         api_key=perplexity_key,
        #         model="sonar-pro",
        #         temperature=0.7,
        #         max_tokens=512,
        #     )
        # else:
        #     logger.info("Using Groq LLM service")
        
        
        # choosing only with groq for now
        llm = GroqLLMService(
            api_key=groq_key,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.7,
            max_tokens=512,
        )


        # Initialize Tavus Video Service
        tavus_api_key = os.getenv("TAVUS_API_KEY")
        tavus_replica_id = os.getenv("TAVUS_REPLICA_ID")
        
        if not tavus_api_key or not tavus_replica_id:
            logger.warning("Tavus API credentials not found. Please set TAVUS_API_KEY and TAVUS_REPLICA_ID in your .env file")
            logger.info("Continuing without video avatar...")
            tavus_service = None
        else:
            logger.info("Initializing Tavus video avatar service...")
            tavus_service = TavusVideoService(
                api_key=tavus_api_key,
                replica_id=tavus_replica_id,
                session=session,
            )

        # Set up context and aggregator
        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        # Build pipeline with Tavus integration
        if tavus_service:
            # Pipeline with Tavus video avatar
            pipeline = Pipeline([
                transport.input(),
                stt,
                context_aggregator.user(),
                llm,
                tts,
                tavus_service,  # Tavus processes TTS audio to generate video
                transport.output(),
                context_aggregator.assistant(),
            ])
            logger.info("Pipeline created with Tavus video avatar")
        else:
            # Fallback pipeline without video
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

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            logger.debug("Initializing hotel room service flow with video avatar")
            
            # Add room context
            room_number = os.getenv("GUEST_ROOM_NUMBER", "")
            if room_number:
                context.add_message({
                    "role": "system", 
                    "content": f"The guest is calling from room {room_number}."
                })
                
                # Get guest information and add to context
                guest = await get_guest_by_room_number(room_number)
                if guest:
                    context.add_message({
                        "role": "system",
                        "content": f"Guest name: {guest['name']}"
                    })
                    # Store guest info in flow manager
                    flow_manager.guest_id = guest["id"]
                    flow_manager.guest_name = guest["name"]
                else:
                    logger.warning(f"Could not find guest for room {room_number}")
            else:
                logger.warning("No room number found in environment variables")
            
            # Add avatar context
            if tavus_service:
                context.add_message({
                    "role": "system",
                    "content": "You are appearing as a video avatar. Remember to maintain eye contact, use appropriate facial expressions, and appear professional and welcoming."
                })
            
            await flow_manager.initialize()

        # Handle Tavus-specific events if needed
        if tavus_service:
            @transport.event_handler("on_participant_updated")
            async def on_participant_updated(transport, participant):
                # This could be used to handle Tavus replica's microphone state
                if participant.get("info", {}).get("userName") == "Tavus":
                    # Ensure we're not subscribed to Tavus's microphone
                    await transport.update_subscriptions(
                        participant_settings={
                            participant["id"]: {
                                "media": "video"  # Only subscribe to video, not audio
                            }
                        }
                    )

        runner = PipelineRunner()
        await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())