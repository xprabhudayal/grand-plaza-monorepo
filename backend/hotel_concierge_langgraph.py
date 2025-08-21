"""
Hotel Room Service Voice Pipeline with LangGraph Integration
Replaces pipecat-flows with LangGraph agent architecture
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

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
from pipecat.services.tavus.video import TavusVideoService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContextFrame

# Import LangGraph agent
from langgraph_agent import get_concierge_agent

sys.path.append(str(Path(__file__).parent.parent))
from runner import configure
sys.path.append(str(Path(__file__).parent))
from app.schemas import OrderStatus

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# ============================================================================
# LangGraph Integration Handler
# ============================================================================

class LangGraphHandler:
    """Handler for LangGraph agent integration with Pipecat"""
    
    def __init__(self):
        self.agent = None
        self.conversation_state = {
            "messages": [],
            "room_number": None,
            "order_summary": {},
            "tool_output": None
        }
        
    async def initialize_agent(self):
        """Initialize the LangGraph agent"""
        try:
            self.agent = get_concierge_agent()
            logger.info("LangGraph agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            raise
    
    async def process_user_input(self, message: str) -> str:
        """Process user input through LangGraph agent"""
        try:
            if not self.agent:
                await self.initialize_agent()
            
            # Process message through agent
            result = await self.agent.process_message(message, self.conversation_state)
            
            # Update conversation state
            self.conversation_state = result
            
            # Extract the last AI message
            if result.get("messages"):
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    response = last_message.content
                else:
                    response = str(last_message)
                    
                logger.info(f"LangGraph response: {response}")
                return response
            
            return "I'm here to help with your room service order. How can I assist you today?"
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return "I apologize, but I'm having some technical difficulties. Please contact the front desk for assistance."
    
    def get_room_number(self) -> Optional[str]:
        """Get the current room number from state"""
        return self.conversation_state.get("room_number")
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get the current order summary"""
        return self.conversation_state.get("order_summary", {})


# ============================================================================
# Main Pipeline Handler
# ============================================================================

class HotelConciergeVoicePipeline:
    """Main voice pipeline with LangGraph integration"""
    
    def __init__(self):
        self.lang_handler = LangGraphHandler()
        self.session_data = {}
        
    async def initialize(self):
        """Initialize the pipeline components"""
        await self.lang_handler.initialize_agent()
        logger.info("Hotel Concierge Voice Pipeline initialized")
    
    async def create_pipeline(self, room_url: str, token: str) -> Pipeline:
        """Create the main pipeline with LangGraph integration"""
        
        # Initialize LangGraph if not already done
        if not self.lang_handler.agent:
            await self.initialize()
        
        # Configure transport
        transport = DailyTransport(
            room_url=room_url,
            token=token,
            bot_name="Hotel Concierge",
            params=DailyParams(
                audio_out_enabled=True,
                audio_in_enabled=True,
                video_out_enabled=True,
                video_in_enabled=False,
                transcription_enabled=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer()
            )
        )
        
        # Configure STT Service
        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            model="nova-2",
            language="en-US",
            interim_results=True
        )
        
        # Configure TTS Service  
        tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            voice="aura-luna-en"
        )
        
        # Configure Tavus Video Service if available
        video_service = None
        if os.getenv("TAVUS_API_KEY"):
            try:
                video_service = TavusVideoService(
                    api_key=os.getenv("TAVUS_API_KEY"),
                    replica_id=os.getenv("TAVUS_REPLICA_ID")
                )
            except Exception as e:
                logger.warning(f"Tavus video service unavailable: {e}")
        
        # Custom LLM service that integrates with LangGraph
        class LangGraphLLMService(GroqLLMService):
            """Custom LLM service that uses LangGraph agent"""
            
            def __init__(self, lang_handler, **kwargs):
                super().__init__(**kwargs)
                self.lang_handler = lang_handler
            
            async def _process_context(self, context):
                """Override to use LangGraph agent instead of direct LLM calls"""
                try:
                    # Get the user message from context
                    messages = context.get_messages()
                    if messages:
                        # Get the last user message
                        user_messages = [msg for msg in messages if msg.get("role") == "user"]
                        if user_messages:
                            user_input = user_messages[-1].get("content", "")
                            
                            # Process through LangGraph
                            response = await self.lang_handler.process_user_input(user_input)
                            
                            # Create response message
                            await self.push_frame(
                                OpenAILLMContextFrame({
                                    "role": "assistant", 
                                    "content": response
                                })
                            )
                            return
                    
                    # Fallback response
                    await self.push_frame(
                        OpenAILLMContextFrame({
                            "role": "assistant",
                            "content": "Hello! I'm your hotel concierge assistant. How can I help you with room service today?"
                        })
                    )
                    
                except Exception as e:
                    logger.error(f"Error in LangGraph LLM service: {e}")
                    await self.push_frame(
                        OpenAILLMContextFrame({
                            "role": "assistant",
                            "content": "I apologize for the technical difficulty. How can I assist you with room service?"
                        })
                    )
        
        # Create LLM service with LangGraph integration
        llm = LangGraphLLMService(
            lang_handler=self.lang_handler,
            api_key=os.getenv("GROQ_API_KEY"),
            model="qwen/qwen3-32b"
        )
        
        # Context aggregator
        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)
        
        # Build pipeline
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant()
        ])
        
        # Add video if available
        if video_service:
            pipeline.processors.insert(-2, video_service)  # Insert before transport output
        
        return pipeline
    
    async def run_pipeline(self, room_url: str, token: str):
        """Run the complete pipeline"""
        try:
            # Create pipeline
            pipeline = await self.create_pipeline(room_url, token)
            
            # Create and run task
            task = PipelineTask(
                pipeline=pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=True,
                    enable_usage_metrics=True
                )
            )
            
            # Run the pipeline
            runner = PipelineRunner()
            await runner.run(task)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise


# ============================================================================
# Main Entry Points - Using Working Pipeline Logic
# ============================================================================

async def main():
    """Main function to set up and run the hotel room service bot with LangGraph integration"""
    
    try:
        async with aiohttp.ClientSession() as session:
            (room_url, _) = await configure(session)

            # Initialize transport with proper configuration
            transport = DailyTransport(
                room_url,
                None,  # Token handled by configure()
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

            # Initialize LangGraph handler
            lang_handler = LangGraphHandler()
            await lang_handler.initialize_agent()

            # Custom LLM service that integrates with LangGraph
            class LangGraphLLMService(GroqLLMService):
                """Custom LLM service that uses LangGraph agent"""
                
                def __init__(self, lang_handler, **kwargs):
                    super().__init__(**kwargs)
                    self.lang_handler = lang_handler
                
                async def _process_context(self, context):
                    """Override to use LangGraph agent instead of direct LLM calls"""
                    try:
                        # Get the user message from context
                        messages = context.get_messages()
                        if messages:
                            # Get the last user message
                            user_messages = [msg for msg in messages if msg.get("role") == "user"]
                            if user_messages:
                                user_input = user_messages[-1].get("content", "")
                                
                                # Process through LangGraph
                                response = await self.lang_handler.process_user_input(user_input)
                                
                                # Create response message
                                await self.push_frame(
                                    OpenAILLMContextFrame({
                                        "role": "assistant", 
                                        "content": response
                                    })
                                )
                                return
                        
                        # Fallback response
                        await self.push_frame(
                            OpenAILLMContextFrame({
                                "role": "assistant",
                                "content": "Hello! I'm your hotel concierge assistant. How can I help you with room service today?"
                            })
                        )
                        
                    except Exception as e:
                        logger.error(f"Error in LangGraph LLM service: {e}")
                        await self.push_frame(
                            OpenAILLMContextFrame({
                                "role": "assistant",
                                "content": "I apologize for the technical difficulty. How can I assist you with room service?"
                            })
                        )

            # Initialize LLM service with LangGraph integration
            llm = LangGraphLLMService(
                lang_handler=lang_handler,
                api_key=os.getenv("GROQ_API_KEY"),
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.7,
                max_tokens=512,
            )

            # Initialize Tavus Video Service with session
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

            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                await transport.capture_participant_transcription(participant["id"])
                logger.debug("First participant joined - initializing LangGraph context")
                
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
        logger.info("Voice session completed")


if __name__ == "__main__":
    asyncio.run(main())