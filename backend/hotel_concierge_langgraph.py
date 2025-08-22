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
import re
from datetime import datetime

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.transcript_processor import TranscriptProcessor

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
from pipecat.frames.frames import TextFrame, LLMFullResponseStartFrame, LLMFullResponseEndFrame

# Import LangGraph agent
from langgraph_agent import get_concierge_agent

# Import transcript logger
from transcript_logger import TranscriptLogger
import uuid

# Configure logging at the very beginning
from logging_config import configure_logging
configure_logging()

from loguru import logger

# LangSmith Integration
from langsmith import traceable, Client

# Import Daily room configuration
from runner import configure

os.environ["LANGSMITH_PROJECT"] = "voice-ai-concierge"

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
            "tool_output": None,
            "conversation_phase": "greeting",
            "session_id": str(uuid.uuid4()),
            "start_time": datetime.now()
        }
        # Initialize LangSmith client for voice pipeline
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
        )
        
    @traceable(
        name="agent_initialization",
        metadata={"component": "voice_pipeline", "interface": "initialization"},
        tags=["initialization", "voice", "agent"]
    )
    async def initialize_agent(self):
        """Initialize the LangGraph agent"""
        try:
            self.agent = get_concierge_agent()
            
            # Log initialization metrics
            self.langsmith_client.log_metrics({
                "voice_pipeline_initialization": 1,
                "session_id": self.conversation_state["session_id"],
                "initialization_time": (datetime.now() - self.conversation_state["start_time"]).total_seconds()
            })
            
            logger.info("LangGraph agent initialized successfully")
        except Exception as e:
            # Track initialization errors
            self.langsmith_client.log_metrics({
                "voice_pipeline_init_error": 1,
                "error_type": type(e).__name__
            })
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            raise
    
    @traceable(
        name="voice_input_processing",
        metadata={"interface": "voice", "component": "voice_pipeline"},
        tags=["voice", "real-time", "stt", "processing"]
    )
    async def process_user_input(self, message: str) -> str:
        """Process user input through LangGraph agent with comprehensive tracking"""
        start_time = datetime.now()
        
        try:
            if not self.agent:
                await self.initialize_agent()
            
            # Process message through agent
            result = await self.agent.process_message(message, self.conversation_state)
            
            # Update conversation state
            self.conversation_state = result
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Track voice processing metrics
            self.langsmith_client.log_metrics({
                "voice_processing_latency_ms": processing_time,
                "input_length_chars": len(message),
                "session_id": self.conversation_state.get("session_id"),
                "conversation_phase": result.get("conversation_phase", "unknown"),
                "room_validated": bool(result.get("room_number")),
                "order_items_count": len(result.get("order_summary", {})),
                "intent": result.get("intent", "unknown"),
                "voice_to_response_success": 1
            })
            
            # Extract the last AI message
            if result.get("messages"):
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    response = last_message.content
                else:
                    response = str(last_message)
                    
                # Track response metrics
                self.langsmith_client.log_metrics({
                    "response_length_chars": len(response),
                    "response_generated": 1
                })
                    
                logger.info(f"LangGraph response: {response}")
                return response
            
            return "I'm here to help with your room service order. How can I assist you today?"
            
        except Exception as e:
            # Track voice processing errors
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.langsmith_client.log_metrics({
                "voice_processing_error": 1,
                "error_type": type(e).__name__,
                "error_latency_ms": error_time,
                "input_length_chars": len(message),
                "session_id": self.conversation_state.get("session_id")
            })
            
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




# ============================================================================
# Main Entry Points - Using Working Pipeline Logic
# ============================================================================

async def main():
    """Main function to set up and run the hotel room service bot with LangGraph integration"""
    
    try:
        async with aiohttp.ClientSession() as session:
            use_daily = os.getenv("DAILY_API_KEY")
            transport = None
            tavus_service = None

            if use_daily:
                logger.info("Using Daily transport for WebRTC connection.")
                (room_url, _) = await configure(session)
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
            else:
                logger.info("DAILY_API_KEY not found. Using local microphone and speakers.")
                from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
                transport = LocalAudioTransport(
                    params=LocalAudioTransportParams(
                        audio_in_enabled=True,
                        audio_out_enabled=True,
                        vad_analyzer=SileroVADAnalyzer(),
                    )
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
            
            # Initialize transcript logging
            session_id = str(uuid.uuid4())
            transcript_logger = TranscriptLogger()
            transcript = TranscriptProcessor()
            logger.info(f"Session started with ID: {session_id}")

            # Custom LLM service that integrates with LangGraph
            class LangGraphLLMService(GroqLLMService):
                """Custom LLM service that uses LangGraph agent"""
                
                def __init__(self, lang_handler, **kwargs):
                    super().__init__(**kwargs)
                    self.lang_handler = lang_handler
                    self._pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

                def _clean_text(self, text: str) -> str:
                    return self._pattern.sub(' ', text).strip()
                
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
                                clean_response = self._clean_text(response)

                                if clean_response:
                                    # Create response message
                                    await self.push_frame(LLMFullResponseStartFrame())
                                    await self.push_frame(TextFrame(clean_response))
                                    await self.push_frame(LLMFullResponseEndFrame())
                                return
                        
                        # Fallback response
                        await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(TextFrame("Hello! I'm your hotel concierge assistant. How can I help you with room service today?"))
                        await self.push_frame(LLMFullResponseEndFrame())
                        
                    except Exception as e:
                        logger.error(f"Error in LangGraph LLM service: {e}")
                        await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(TextFrame("I apologize for the technical difficulty. How can I assist you with room service?"))
                        await self.push_frame(LLMFullResponseEndFrame())

            # Initialize LLM service with LangGraph integration
            llm = LangGraphLLMService(
                lang_handler=lang_handler,
                api_key=os.getenv("GROQ_API_KEY"),
                model="qwen/qwen3-32b",
                temperature=0.1,
                max_tokens=1000,
            )

            # Initialize Tavus Video Service with session
            tavus_api_key = os.getenv("TAVUS_API_KEY")
            tavus_replica_id = os.getenv("TAVUS_REPLICA_ID")
            
            if use_daily and tavus_api_key and tavus_replica_id:
                logger.info("Initializing Tavus video avatar service...")
                tavus_service = TavusVideoService(
                    api_key=tavus_api_key,
                    replica_id=tavus_replica_id,
                    session=session,
                )
            elif use_daily:
                logger.warning("Tavus API credentials not found. Continuing without video avatar...")
            else:
                logger.info("Tavus video avatar not supported for local transport.")
                tavus_service = None

            # Set up context and aggregator
            context = OpenAILLMContext()
            context_aggregator = llm.create_context_aggregator(context)

            # Build pipeline with transcript processors
            pipeline_components = [
                transport.input(),
                stt,
                transcript.user(),           # Capture user transcripts
                context_aggregator.user(),
                llm,
                tts,
            ]
            if tavus_service:
                pipeline_components.append(tavus_service)
            
            pipeline_components.append(transport.output())
            pipeline_components.append(transcript.assistant())  # Capture assistant transcripts
            pipeline_components.append(context_aggregator.assistant())
            
            pipeline = Pipeline(pipeline_components)
            logger.info(f"Pipeline created with {'Tavus video avatar' if tavus_service else 'audio only'}")

            task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
            
            # Transcript event handler
            @transcript.event_handler("on_transcript_update")
            async def handle_transcript_update(processor, frame):
                """Save transcripts to CSV log file"""
                try:
                    for message in frame.messages:
                        # Get room number from LangGraph state
                        room_number = lang_handler.get_room_number()
                        
                        # Log to CSV
                        await transcript_logger.alog_message(
                            session_id=session_id,
                            role=message.role,
                            content=message.content,
                            room_number=room_number,
                            confidence_score=getattr(message, 'confidence', None),
                            processing_time_ms=getattr(message, 'processing_time', None)
                        )
                        
                        logger.debug(f"[Transcript] {message.role}: {message.content[:100]}...")
                except Exception as e:
                    logger.error(f"Failed to log transcript: {e}")

            @transcript.event_handler("on_conversation_end")
            async def collect_feedback(*args):
                """Collect implicit feedback for LangSmith"""
                try:
                    client = Client()
                    # Track conversation metrics
                    client.create_feedback(
                        run_id=session_id,
                        key="conversation_completed",
                        score=1.0 if lang_handler.get_order_summary() else 0.5,
                        comment=f"Order placed: {bool(lang_handler.get_order_summary())}"
                    )
                    logger.info(f"LangSmith feedback collected for session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to collect LangSmith feedback: {e}")

            # Event handlers
            if use_daily:
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
            else:
                # For local transport, we can add initial context directly
                logger.debug("Initializing LangGraph context for local session")
                context.add_message({
                    "role": "system",
                    "content": "You are a professional hotel room service assistant. Be concise and efficient."
                })


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
        
        # Close transcript logger
        if 'transcript_logger' in locals():
            transcript_logger.close()
            
            # Log session summary
            transcripts = transcript_logger.get_session_transcripts(session_id)
            logger.info(f"Session {session_id} completed with {len(transcripts)} messages")
        
        logger.info("Voice session completed")


if __name__ == "__main__":
    asyncio.run(main())