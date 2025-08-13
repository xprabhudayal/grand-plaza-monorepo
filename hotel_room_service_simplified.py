"""
Hotel Room Service Voice Pipeline (Simplified)
Adapted version that works with existing pipecat infrastructure
while incorporating hotel room service functionality
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
from app.order_service import order_service
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


# For LLM, we'll use OpenAI-compatible endpoint with Perplexity
# from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.perplexity.llm import PerplexityLLMService

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
from data.menu_data import search_menu_items, get_menu_categories, get_menu_items_by_category, HOTEL_MENU_DATA

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

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
class MenuSearchResult(FlowResult):
    query: str
    results: List[Dict[str, Any]]

class CategorySelectResult(FlowResult):
    category_name: str
    items: List[Dict[str, Any]]

class OrderItemResult(FlowResult):
    item_name: str
    quantity: Union[str, int]
    price: float
    special_notes: str = None

class OrderSummaryResult(FlowResult):
    items: List[Dict[str, Any]]
    total_amount: float
    estimated_time: int

# Flow Functions
async def browse_menu(flow_manager: FlowManager) -> tuple[None, str]:
    """Start browsing the menu"""
    return None, "menu_browse"

async def search_items(flow_manager: FlowManager, query: str) -> tuple[MenuSearchResult, str]:
    """Search for menu items by name or description"""
    results = search_menu_items(query)
    search_result = MenuSearchResult(query=query, results=results)
    return search_result, "show_search_results"

async def select_category(flow_manager: FlowManager, category_name: str) -> tuple[CategorySelectResult, str]:
    """Select a specific menu category to browse"""
    # Validate category name
    valid_categories = [cat["name"] for cat in HOTEL_MENU_DATA["categories"]]
    if category_name not in valid_categories:
        # Find closest match
        category_name = next((cat for cat in valid_categories if cat.lower() in category_name.lower()), valid_categories[0])
    
    items = get_menu_items_by_category(category_name)
    category_result = CategorySelectResult(category_name=category_name, items=items)
    return category_result, "show_category_items"

async def add_item_to_order(
    flow_manager: FlowManager, 
    item_name: str, 
    quantity: Union[str, int] = 1,
    special_notes: str = None
) -> tuple[OrderItemResult, str]:
    """Add an item to the current order"""
    # Convert quantity from text to number
    quantity_int = convert_text_to_number(quantity)
    
    # Find the item in the menu to get the price
    all_items = []
    for category in HOTEL_MENU_DATA["categories"]:
        all_items.extend(category["items"])
    
    menu_item = next((item for item in all_items if item["name"].lower() == item_name.lower()), None)
    
    if not menu_item:
        # Try partial match
        menu_item = next((item for item in all_items if item_name.lower() in item["name"].lower()), None)
    
    if menu_item:
        order_item = OrderItemResult(
            item_name=menu_item["name"],
            quantity=quantity_int,
            price=menu_item["price"] * quantity_int,
            special_notes=special_notes
        )
        
        # Track items for database storage
        if not hasattr(flow_manager, 'current_order'):
            flow_manager.current_order = {'items': [], 'room_number': None, 'guest_name': None}
        
        flow_manager.current_order['items'].append({
            'name': menu_item["name"],
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

async def confirm_final_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Confirm and place the final order"""
    # Store the order in the database
    try:
        # Get collected order data from context
        context = flow_manager.context_aggregator.context
        
        # Extract order items from context (you'll need to track these as items are added)
        # For now, we'll store them in a simple way
        if not hasattr(flow_manager, 'current_order'):
            flow_manager.current_order = {'items': [], 'room_number': None, 'guest_name': None}
        
        room_number = os.getenv("GUEST_ROOM_NUMBER", "101")  # Default or from environment
        guest_name = getattr(flow_manager, 'guest_name', 'Guest')  # Should be collected in flow
        
        if flow_manager.current_order['items']:
            # Create order in database
            order = await order_service.create_order_from_voice(
                room_number=room_number,
                guest_name=guest_name,
                items=flow_manager.current_order['items'],
                special_requests=getattr(flow_manager, 'special_requests', None)
            )
            
            # Store order ID for reference
            flow_manager.order_id = order['id']
            flow_manager.order_confirmation = order_service.format_order_confirmation(order)
            logger.info(f"Order stored in database: {order['id']}")
        else:
            logger.warning("No items in order to save")
    except Exception as e:
        logger.error(f"Failed to store order: {str(e)}")
        # Continue with flow even if storage fails
    
    return None, "order_placed"

async def modify_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Make changes to the current order"""
    return None, "menu_browse"

async def cancel_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Cancel the entire order"""
    return None, "order_cancelled"

# Hotel Room Service Flow Configuration
hotel_room_service_flow: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": """You are a professional and friendly hotel room service assistant. You help guests order food and beverages from our comprehensive room service menu. 
                    
                    Always be warm, courteous, and efficient. Speak as if you're taking an order over the phone. Keep responses concise but helpful."""
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": """Greet the guest warmly and ask how you can help them with their room service order today. 
                    
                    Let them know they can:
                    - Browse our menu categories (Breakfast, Appetizers, Salads, Main Courses, Sandwiches, Desserts, Beverages)
                    - Search for specific items
                    - Ask about dietary options
                    
                    Ask what they'd like to do first."""
                }
            ],
            "functions": [browse_menu, search_items],
        },
        "menu_browse": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Help the guest navigate our room service menu. Our categories are:
                    
                    🍳 Breakfast - Available 24/7 (Continental, American, Avocado Toast, Pancakes, Oatmeal)
                    🥗 Appetizers - Light bites (Shrimp Cocktail, Wings, Hummus, Nachos)  
                    🥬 Salads - Fresh options (Caesar, Mediterranean, Quinoa Bowl)
                    🍽️ Main Courses - Hearty entrees (Salmon, Steak, Chicken Parmesan, Curry)
                    🥪 Sandwiches - Gourmet options (Club, Burger, Veggie Burger, Reuben)
                    🍰 Desserts - Sweet treats (Chocolate Cake, Cheesecake, Ice Cream)
                    ☕ Beverages - Hot & cold drinks (Coffee, Tea, Juices, Wine, Beer)
                    
                    Ask which category interests them or if they'd like to search for something specific."""
                }
            ],
            "functions": [select_category, search_items, add_item_to_order, review_current_order],
        },
        "show_search_results": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Present the search results clearly with names, prices, and brief descriptions. 
                    
                    If items have dietary information (vegetarian, vegan, gluten-free), mention it. 
                    Ask if they'd like to add any of these items to their order or search for something else."""
                }
            ],
            "functions": [add_item_to_order, search_items, select_category, review_current_order],
        },
        "show_category_items": {
            "task_messages": [
                {
                    "role": "system", 
                    "content": """Show the items in the selected category with prices and descriptions. 
                    
                    Highlight any special dietary options. Ask if they'd like to add any items to their order, 
                    browse other categories, or need more details about specific items."""
                }
            ],
            "functions": [add_item_to_order, select_category, search_items, review_current_order],
        },
        "item_added": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Confirm the item has been added to their order with quantity and any special notes.
                    
                    Ask if they'd like to:
                    - Add more items
                    - Review their current order
                    - Browse other menu categories
                    - Place their order"""
                }
            ],
            "functions": [add_item_to_order, browse_menu, review_current_order, confirm_final_order],
        },
        "order_review": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Review their complete order including all items, quantities, prices, and total amount.
                    
                    Provide an estimated delivery time (typically 20-45 minutes depending on items).
                    Ask if they want to:
                    - Confirm and place the order
                    - Add more items  
                    - Remove or modify items
                    - Cancel the order"""
                }
            ],
            "functions": [confirm_final_order, add_item_to_order, modify_order, cancel_order],
        },
        "order_placed": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Thank the guest for their order and confirm it has been placed with the kitchen.
                    
                    If an order confirmation is available, share the reference number.
                    Provide:
                    - Order confirmation with reference ID (if available)
                    - Estimated delivery time (20-30 minutes)
                    - Room number confirmation
                    - Let them know they can call back if they need anything else
                    
                    End on a warm, professional note."""
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
        "order_cancelled": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Politely acknowledge the order cancellation and ask if there's anything else you can help them with.
                    
                    Let them know they can always call back when they're ready to place an order."""
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}

async def main():
    """Main function to set up and run the hotel room service bot"""
    async with aiohttp.ClientSession() as session:
        (room_url, _) = await configure(session)

        # Initialize services
        transport = DailyTransport(
            room_url,
            None,
            "Hotel Room Service AI",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # Use Soniox STT if available, fallback to Deepgram
        soniox_key = os.getenv("SONIOX_API_KEY")
        if soniox_key:
            # For now, we'll use Deepgram as Soniox integration needs custom processor
            logger.info("Soniox API key found, but using Deepgram for compatibility")
            stt = SonioxSTTService(
                api_key=os.getenv("SONIOX_API_KEY"),
                params=SonioxInputParams(
                language_hints=[Language.EN],
            ),
            )
        else:
            stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

        # Use Cartesia TTS
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="820a3788-2b37-4d21-847a-b65d8a68c99a",  # Professional voice
        )

        # # Use Perplexity Sonar Pro via OpenAI-compatible endpoint
        # perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        # llm = PerplexityLLMService(
        #     api_key=perplexity_key,
        #     model="sonar-pro",  # Use Perplexity's Sonar Pro model
        #     temperature=0.7,  # Adjust temperature for more creative responses
        #     max_tokens=512,  # Limit response length
        # )
        llm = GroqLLMService(
            api_key=os.getenv("GROQ_API_KEY"),
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Use Groq's Llama 4 model
            temperature=0.7,  # Adjust temperature for more creative responses
            max_tokens=512,  # Limit response length
        )

        

        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        # Create pipeline
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

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
            logger.debug("Initializing hotel room service flow")
            
            # Add room context
            room_number = os.getenv("GUEST_ROOM_NUMBER", "")
            if room_number:
                context.add_message({
                    "role": "system", 
                    "content": f"The guest is calling from room {room_number}."
                })
            
            await flow_manager.initialize()

        runner = PipelineRunner()
        await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())