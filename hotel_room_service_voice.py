"""
Hotel Room Service Voice AI Pipeline
Voice-enabled hotel room service ordering system with Soniox STT, Perplexity Sonar Pro LLM, and Cartesia TTS
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport

# Custom imports
from pipecat_flows import FlowConfig, FlowManager, FlowResult

# Add app directory to path
sys.path.append(str(Path(__file__).parent))
from data.menu_data import search_menu_items, get_menu_categories, get_menu_items_by_category
from app.models import Guest, Order, OrderItem, VoiceSession

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

class SonioxSTTService:
    """Custom Soniox Speech-to-Text service"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.soniox.com/v1"
        
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Soniox API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "audio": audio_data.hex(),  # Convert to hex string
            "model": "stt-async-preview",
            "include_nonfinal": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/transcriptions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("text", "")
                    else:
                        logger.error(f"Soniox API error: {response.status}")
                        return ""
        except Exception as e:
            logger.error(f"Soniox transcription error: {e}")
            return ""

class PerplexitySonarProLLM:
    """Custom Perplexity Sonar Pro LLM service"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar-pro"
    
    async def generate_response(self, messages: List[Dict[str, str]], context: Dict[str, Any] = None) -> str:
        """Generate response using Perplexity Sonar Pro"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Add context about the hotel and available services
        system_message = self._build_system_message(context)
        full_messages = [{"role": "system", "content": system_message}] + messages
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": 150,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"Perplexity API error: {response.status}")
                        return "I apologize, but I'm having trouble processing your request right now."
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return "I apologize, but I'm having trouble processing your request right now."
    
    def _build_system_message(self, context: Dict[str, Any] = None) -> str:
        """Build system message with hotel context"""
        base_message = """You are a friendly and professional hotel room service AI assistant. 
        You help guests order food and beverages from our room service menu. You should:
        
        1. Greet guests warmly
        2. Help them browse the menu or search for specific items
        3. Take their orders clearly and confirm details
        4. Provide information about preparation times and dietary options
        5. Handle special requests and dietary restrictions
        6. Be concise but helpful in your responses
        
        Always speak naturally as if you're having a phone conversation."""
        
        if context:
            guest_info = context.get("guest", {})
            room_number = guest_info.get("room_number", "")
            if room_number:
                base_message += f"\n\nThe guest is calling from room {room_number}."
        
        return base_message

# Hotel Room Service Flow Functions
async def start_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Start the ordering process"""
    return None, "browse_menu"

async def browse_categories(flow_manager: FlowManager) -> tuple[None, str]:
    """Let user browse menu categories"""
    return None, "browse_menu"

async def search_menu(flow_manager: FlowManager, query: str) -> tuple[Dict[str, Any], str]:
    """Search for menu items"""
    results = search_menu_items(query)
    return {"search_results": results}, "show_items"

async def select_category(flow_manager: FlowManager, category_name: str) -> tuple[Dict[str, Any], str]:
    """Select a menu category"""
    items = get_menu_items_by_category(category_name)
    return {"category": category_name, "items": items}, "show_items"

async def add_to_order(
    flow_manager: FlowManager, 
    item_name: str, 
    quantity: int = 1, 
    special_notes: str = None
) -> tuple[Dict[str, Any], str]:
    """Add item to order"""
    # In a real implementation, this would interact with the database
    order_item = {
        "item_name": item_name,
        "quantity": quantity,
        "special_notes": special_notes
    }
    
    # Store in flow context
    current_order = flow_manager.get_context().get("current_order", [])
    current_order.append(order_item)
    
    return {"order_item": order_item, "current_order": current_order}, "confirm_item"

async def review_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Review the current order"""
    return None, "order_review"

async def confirm_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Confirm and place the order"""
    return None, "order_confirmed"

async def modify_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Allow modifications to the order"""
    return None, "browse_menu"

async def cancel_order(flow_manager: FlowManager) -> tuple[None, str]:
    """Cancel the current order"""
    return None, "end"

# Flow Configuration for Hotel Room Service
hotel_flow_config: FlowConfig = {
    "initial_node": "start",
    "nodes": {
        "start": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a friendly hotel room service assistant. Greet the guest and ask how you can help them with their order today. Keep responses conversational and helpful."
                }
            ],
            "task_messages": [
                {
                    "role": "system", 
                    "content": "Welcome the guest and ask if they'd like to browse our menu, search for specific items, or if they already know what they want to order."
                }
            ],
            "functions": [start_order, browse_categories],
        },
        "browse_menu": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """You can help guests with our room service menu. Our categories include:
                    - Breakfast (available 24/7)
                    - Appetizers 
                    - Salads
                    - Main Courses
                    - Sandwiches
                    - Desserts
                    - Beverages
                    
                    Ask what category they're interested in, or if they want to search for specific items. Use the available functions to help them."""
                }
            ],
            "functions": [select_category, search_menu, add_to_order, review_order],
        },
        "show_items": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Present the menu items clearly, including prices and descriptions. Ask if they'd like to add any items to their order or need more information."
                }
            ],
            "functions": [add_to_order, select_category, search_menu, review_order],
        },
        "confirm_item": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Confirm the item has been added to their order. Ask if they'd like to add more items, review their current order, or proceed to checkout."
                }
            ],
            "functions": [add_to_order, browse_categories, review_order, confirm_order],
        },
        "order_review": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Review the complete order with prices and total. Ask if they want to modify anything, add more items, or confirm the order."
                }
            ],
            "functions": [confirm_order, modify_order, add_to_order, cancel_order],
        },
        "order_confirmed": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank the guest, provide an estimated delivery time (usually 20-45 minutes), and let them know they can call if they need anything else."
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
        "end": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank the guest and end the conversation politely."
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}

async def main():
    """Main function to set up and run the hotel room service voice AI"""
    async with aiohttp.ClientSession() as session:
        # Configure Daily room (you'll need to implement this)
        room_url = os.getenv("DAILY_ROOM_URL", "")
        
        if not room_url:
            logger.error("DAILY_ROOM_URL environment variable required")
            return
        
        # Initialize transport
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
        
        # Initialize services with custom implementations
        soniox_api_key = os.getenv("SONIOX_API_KEY")
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        cartesia_api_key = os.getenv("CARTESIA_API_KEY")
        
        if not all([soniox_api_key, perplexity_api_key, cartesia_api_key]):
            logger.error("Missing required API keys")
            return
        
        # For now, we'll use a fallback to OpenAI-compatible service since we need to integrate custom services
        # In production, you'd create custom pipecat processors for Soniox and Perplexity
        stt = SonioxSTTService(api_key=soniox_api_key)
        llm = PerplexitySonarProLLM(api_key=perplexity_api_key)
        tts = CartesiaTTSService(
            api_key=cartesia_api_key,
            voice_id="820a3788-2b37-4d21-847a-b65d8a68c99a",  # Professional voice
        )
        
        # For the pipeline, we'll need to adapt this to work with pipecat's architecture
        # This is a simplified version - full integration would require custom processors
        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context) if hasattr(llm, 'create_context_aggregator') else None
        
        # Create pipeline - this would need to be adapted for custom services
        pipeline_components = [
            transport.input(),
            # Custom STT processor would go here
            # Custom LLM processor would go here  
            tts,
            transport.output(),
        ]
        
        if context_aggregator:
            pipeline_components.extend([
                context_aggregator.user(),
                context_aggregator.assistant(),
            ])
        
        pipeline = Pipeline(pipeline_components)
        
        task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
        
        # Initialize flow manager
        flow_manager = FlowManager(
            task=task,
            llm=llm if hasattr(llm, 'create_context_aggregator') else None,
            context_aggregator=context_aggregator,
            flow_config=hotel_flow_config,
        )
        
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            logger.debug("Initializing hotel room service flow")
            
            # Set up guest context if available
            room_number = os.getenv("GUEST_ROOM_NUMBER", "Unknown")
            guest_context = {
                "guest": {
                    "room_number": room_number
                }
            }
            flow_manager.set_context(guest_context)
            
            await flow_manager.initialize()
        
        runner = PipelineRunner()
        await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())