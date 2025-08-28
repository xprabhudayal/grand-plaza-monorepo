"""
LangGraph Agent for Hotel Concierge System
Replaces pipecat-flows with dynamic, tool-based agent architecture
"""

import os
import json
import re
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from loguru import logger
from langsmith import traceable, Client

# Try to import RAG pipeline - make it optional
try:
    from rag_pipeline import get_rag_pipeline
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG pipeline not available: {e}")
    RAG_AVAILABLE = False
    def get_rag_pipeline():
        raise ImportError("RAG pipeline dependencies not installed")

# Import semantic intent classifier
from semantic_intent_classifier import classify_user_intent


# setup the project name for LangSmith
os.environ["LANGSMITH_PROJECT"] = "voice-ai-concierge"

# ============================================================================
# Agent State Definition
# ============================================================================

class AgentState(TypedDict):
    """Enhanced state maintained across the conversation with detailed phase tracking"""
    messages: Annotated[list[BaseMessage], add_messages]
    room_number: Optional[str]
    order_summary: Dict[str, Any]
    tool_output: Optional[str]
    validation_status: Optional[str]  # room_needed, room_captured, room_validated
    intent: Optional[str]  # menu_inquiry, order_placement, order_modification, order_confirmation, general_inquiry
    validation_result: Optional[str]  # valid, missing_room, empty_order
    conversation_phase: Optional[str]  # greeting, room_validation, intent_classification, menu_browsing, ordering, confirming, completed
    last_agent: Optional[str]  # track which specialized agent was last active
    order_confirmed: Optional[bool]  # track if order has been confirmed by user
    order_placed: Optional[bool]  # track if order has been successfully placed to prevent duplicates
    error_count: Optional[int]  # track consecutive errors for fallback handling


# ============================================================================
# Tool Definitions
# ============================================================================

class MenuRetrievalInput(BaseModel):
    """Input for menu information retrieval"""
    query: str = Field(description="User's question about the menu (e.g., 'what salads do you have?', 'is the burger gluten-free?')")


class MenuRetrievalTool(BaseTool):
    """Tool for retrieving menu information using RAG"""
    name: str = "retrieve_menu_info"
    description: str = "Retrieve relevant menu information based on user queries using RAG pipeline"
    args_schema: type[BaseModel] = MenuRetrievalInput
    
    @traceable(
        name="rag_retrieve",
        metadata={"pipeline": "menu_rag", "tool": "menu_retrieval"},
        tags=["rag", "retrieval", "menu"]
    )
    def _run(self, query: str) -> str:
        """Execute the RAG pipeline with error handling"""
        try:
            if not RAG_AVAILABLE:
                return self._get_fallback_menu_info(query)
                
            rag_pipeline = get_rag_pipeline()
            context = rag_pipeline.get_context_for_query(query, k=5)
            
            if not context or context == "No relevant menu information found.":
                return self._get_fallback_menu_info(query)
            
            return context
            
        except Exception as e:
            logger.error(f"Error in menu retrieval: {e}")
            return self._get_fallback_menu_info(query)
    
    def _get_fallback_menu_info(self, query: str) -> str:
        """Provide minimal fallback menu information when RAG is unavailable"""
        logger.warning(f"RAG unavailable, providing minimal fallback for query: {query}")
        
        return """I'm sorry, our menu system is temporarily unavailable right now. However, I can tell you that we offer a wonderful variety of delicious options including fresh pizzas with various toppings, hearty sandwiches and wraps, healthy salads and soups, classic breakfast items, refreshing beverages, and tasty desserts. 

For specific details about ingredients, prices, and availability, please contact room service directly at extension one two three four, and they'll be happy to help you with your order. Is there anything else I can assist you with today?"""


class OrderPlacementInput(BaseModel):
    """Input for placing an order"""
    order_summary: Dict[str, int] = Field(description="Complete order summary as a JSON object with items and quantities")
    room_number: str = Field(description="Validated guest room number")


class OrderPlacementTool(BaseTool):
    """Tool for placing orders by sending a payload to a webhook"""
    name: str = "place_order_webhook"
    description: str = "Place a final order by sending the complete order payload to a pre-configured webhook URL."
    args_schema: type[BaseModel] = OrderPlacementInput

    def _get_price_from_rag(self, item_name: str) -> float:
        """Get item price using RAG pipeline metadata (more efficient and reliable)"""
        try:
            if not RAG_AVAILABLE:
                logger.warning(f"RAG not available, defaulting price for '{item_name}' to 12.00")
                return 12.00
                
            rag_pipeline = get_rag_pipeline()
            # Search for the item in the vectorstore
            results = rag_pipeline.retrieve(item_name.lower(), k=5)
            
            # Look for exact or close matches in metadata
            for result in results:
                metadata = result.get('metadata', {})
                stored_item_name = metadata.get('item_name', '').lower()
                
                # Check for exact match or if the stored item contains our search term
                if (stored_item_name == item_name.lower() or 
                    item_name.lower() in stored_item_name or 
                    stored_item_name in item_name.lower()):
                    
                    price_str = metadata.get('price', '')
                    if price_str:
                        # Extract numeric price from string (handles "$12.50" format)
                        price_clean = price_str.replace('$', '').strip()
                        if price_clean:
                            return float(price_clean)
            
            logger.warning(f"Could not find price in metadata for '{item_name}', using default")
            return 12.00
            
        except Exception as e:
            logger.error(f"Error getting price from RAG metadata for '{item_name}': {e}")
            return 12.00

    @traceable(
        name="order_placement_webhook",
        metadata={"tool": "order_placement_webhook", "interface": "webhook"},
        tags=["order", "placement", "webhook"]
    )
    async def _arun(self, order_summary: Dict[str, int], room_number: str) -> str:
        """Place order asynchronously by sending data to a webhook."""
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            logger.error("WEBHOOK_URL environment variable not set. Cannot place order.")
            return "I'm sorry, the ordering system is currently unavailable due to a configuration issue. Please contact the front desk for assistance."

        try:
            # Consolidate order details for the webhook payload
            item_names = ", ".join(order_summary.keys())
            total_quantity = sum(order_summary.values())

            # Get prices using RAG pipeline instead of hardcoded values
            total_price = sum(self._get_price_from_rag(name) * qty for name, qty in order_summary.items())

            order_data = {
                "guest_room": room_number,
                "name": item_names,
                "quantity": total_quantity,
                "consolidated_pricing": total_price,
                "order_status": "pending"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=order_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        return f"Great news! Your order has been successfully placed for room {room_number}. You can expect your delicious food to arrive in about 25 to 30 minutes. Is there anything else I can help you with today?"
                    else:
                        error_text = await response.text()
                        logger.error(f"Order placement webhook failed: {response.status} - {error_text}")
                        return f"I apologize, but I'm having some difficulty placing your order at the moment. There seems to be a technical issue with our ordering system. Please try again in a few moments, or feel free to call the front desk and they'll be happy to assist you with your order."

        except Exception as e:
            logger.error(f"Error sending order to webhook: {e}")
            return "I'm having trouble placing your order right now due to a technical issue. Please contact the front desk for assistance."

    def _run(self, order_summary: Dict[str, int], room_number: str) -> str:
        """Synchronous wrapper"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._arun(order_summary, room_number))


class OrderUpdateInput(BaseModel):
    """Input for updating order"""
    action: str = Field(description="Action to perform: 'add', 'remove', or 'set' to a specific quantity")
    item_name: str = Field(description="Name of the item to add, remove, or set")
    quantity: int = Field(description="Quantity of the item", default=1)


class OrderUpdateTool(BaseTool):
    """Tool for managing the order cart"""
    name: str = "update_order"
    description: str = "Add, remove, or set the quantity of items in the current order cart"
    args_schema: type[BaseModel] = OrderUpdateInput
    
    @traceable(
        name="order_update",
        metadata={"tool": "order_update"},
        tags=["order", "cart", "update"]
    )
    def _run(self, action: str, item_name: str, quantity: int = 1) -> str:
        """Update the order summary"""
        try:
            # Return a JSON string that tool_executor_node can parse
            return json.dumps({
                "action": action.lower(),
                "item_name": item_name,
                "quantity": quantity
            })
        except Exception as e:
            logger.error(f"Error creating order update data: {e}")
            return json.dumps({"error": "Failed to process update."})


# ============================================================================
# Agent Nodes & Decision Functions
# ============================================================================

@traceable(
    name="guest_validation",
    metadata={"node_type": "validation", "agent_component": "guest_validation"},
    tags=["validation", "guest", "room"]
)
def guest_validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate guest information and room number"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    # Check if room number is already captured
    if state.get("room_number"):
        return {"validation_status": "room_validated"}
    
    # Check if last message contains room number pattern
    if last_message and hasattr(last_message, 'content'):
        content = str(last_message.content).lower()
        room_match = re.search(r'\b\d{3,4}\b', content)
        if room_match:
            room_number = room_match.group()
            return {
                "room_number": room_number,
                "validation_status": "room_captured",
                "messages": [AIMessage(content=f"Thank you! I've noted your room number as {room_number}. How can I assist you today?")]
            }
    
    return {
        "validation_status": "room_needed",
        "messages": [AIMessage(content="Welcome to our hotel room service! Could you please provide your room number so I can assist you better?")]
    }


@traceable(
    name="intent_classification",
    metadata={"node_type": "classification", "agent_component": "intent_classification"},
    tags=["intent", "classification", "routing"]
)
def intent_classification_node(state: AgentState) -> Dict[str, Any]:
    """Classify user intent using semantic intent classifier"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if not last_message or not hasattr(last_message, 'content'):
        return {"intent": "unknown"}
    
    content = str(last_message.content)
    
    try:
        # Use semantic intent classifier instead of keyword matching
        classification_result = classify_user_intent(content)
        intent = classification_result.get("intent", "general_assistance")
        
        logger.info(f"Intent classified: '{intent}' (confidence: {classification_result.get('confidence', 0):.3f})")
        
        return {"intent": intent}
        
    except Exception as e:
        logger.error(f"Error in semantic intent classification: {e}")
        # Fallback to general assistance if classification fails
        return {"intent": "general_assistance"}


@traceable(
    name="order_validation",
    metadata={"node_type": "validation", "agent_component": "order_validation"},
    tags=["validation", "order", "placement"]
)
def order_validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate order before placement"""
    order_summary = state.get("order_summary", {})
    room_number = state.get("room_number")
    order_placed = state.get("order_placed", False)
    
    # If order is already placed, gracefully end instead of re-placing
    if order_placed:
        return {
            "validation_result": "already_placed",
            "messages": [AIMessage(content="You're very welcome! Your order is already on its way to your room. Have a wonderful day!")]
        }
    
    if not room_number:
        return {
            "validation_result": "missing_room",
            "messages": [AIMessage(content="I need your room number to place the order. Could you provide it?")]
        }
    
    if not order_summary or len(order_summary) == 0:
        return {
            "validation_result": "empty_order",
            "messages": [AIMessage(content="Your order appears to be empty. Would you like to add some items first?")]
        }
    
    return {
        "validation_result": "valid",
        "messages": [AIMessage(content=f"Order validation complete. Ready to place order for room {room_number}.")]
    }


# ============================================================================
# Routing/Decision Functions
# ============================================================================

def route_after_guest_validation(state: AgentState) -> str:
    """Route after guest validation"""
    validation_status = state.get("validation_status", "")
    
    if validation_status == "room_needed":
        return "END"  # Wait for room number input
    elif validation_status == "room_captured":
        return "intent_classification"
    elif validation_status == "room_validated":
        return "intent_classification"
    else:
        return "guest_validation"


def route_after_intent_classification(state: AgentState) -> str:
    """Route based on classified intent"""
    intent = state.get("intent", "")
    
    if intent == "menu_inquiry":
        return "menu_retrieval_agent"
    elif intent == "order_placement":
        return "order_management_agent"
    elif intent == "order_modification":
        return "order_management_agent"
    elif intent == "order_confirmation":
        return "order_validation"
    else:
        return "general_agent"


def route_after_order_validation(state: AgentState) -> str:
    """Route after order validation"""
    validation_result = state.get("validation_result", "")
    
    if validation_result == "valid":
        return "order_placement_tools"
    elif validation_result == "already_placed":
        return "END"  # Gracefully end conversation
    elif validation_result == "missing_room":
        return "guest_validation"
    elif validation_result == "empty_order":
        return "order_management_agent"
    else:
        return "general_agent"


def should_continue_to_tools(state: AgentState) -> str:
    """Determine if we need to execute tools"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    # If the last message has tool calls, go to tool execution
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, continue conversation
    return "intent_classification"


def should_end_conversation(state: AgentState) -> str:
    """Determine if conversation should end"""
    conversation_phase = state.get("conversation_phase", "")
    
    if conversation_phase == "completed":
        return "END"
    else:
        return "guest_validation"


def route_from_tools(state: AgentState) -> str:
    """Route from tools back to appropriate agent based on last intent"""
    intent = state.get("intent", "general_inquiry")
    
    if intent == "menu_inquiry":
        return "menu_retrieval_agent"
    elif intent in ["order_placement", "order_modification"]:
        return "order_management_agent"
    else:
        return "general_agent"

def create_specialized_agent_nodes(llm, tools):
    """Create specialized agent nodes for different intents"""
    
    def menu_retrieval_agent(state: AgentState) -> Dict[str, Any]:
        """Specialized agent for menu-related queries"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        
        system_context = f"""You are a friendly menu specialist for hotel room service talking to a guest in room {room_number}. You're having a natural conversation over the phone, so speak warmly and conversationally. 
        
Your role is to help guests browse our menu, answer questions about food items, ingredients, prices, and availability. Always use the retrieve_menu_info tool to get current and accurate information - never guess or provide information from memory. 

CRITICAL: This will be read aloud by text-to-speech, so format everything for natural speech:
- Say prices as "5 dollars and 50 cents" NOT "$5.50" 
- NO asterisks, bullet points, dashes, or formatting symbols
- NO numbered lists like "1. Item 2. Item" - just speak naturally
- Say "dollars" and "cents" instead of dollar signs
- Use natural speech patterns like "we have" instead of bullet points

Speak naturally as if you're talking to someone on the phone. Be conversational, helpful, and enthusiastic about our menu offerings."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        response = llm.bind_tools([tool for tool in tools if tool.name == "retrieve_menu_info"]).invoke(full_messages)
        return {"messages": [response], "conversation_phase": "menu_browsing"}
    
    def order_management_agent(state: AgentState) -> Dict[str, Any]:
        """Specialized agent for order placement and modification"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        order_summary = state.get("order_summary", {})
        
        system_context = f"""You are a helpful order specialist for hotel room service talking to a guest in room {room_number}. You're having a natural conversation over the phone, so speak warmly and conversationally.

Current order: {order_summary if order_summary else 'Empty'}

Your role is to help guests add items to their order, modify quantities, remove items, and manage their current order. Always use the retrieve_menu_info tool when guests ask about menu items to get accurate information - never guess prices or details.

IMPORTANT: If a guest asks to order an item that is a category, like "pizza" or "sandwich," or any other category in which you think, there could be a sub variety you MUST NOT add it to the order. Instead, use the `retrieve_menu_info` tool to look up the options for that category. Then, ask a clarifying question. For example: "We have several kinds of pizza: Margherita, Pepperoni, and BBQ Chicken. Which one would you like?" Only add an item to the order when the guest specifies a complete, orderable item. These are just for your reference about the types of the pizza, and it should noted that you should not take these are a reference to say that we have, these pizzas actually. You have to use the "retrieve_menu_tool" inorder to fetch the right information available for the provided user query.

CRITICAL: This will be read aloud by text-to-speech, so format everything for natural speech:
- Say prices as "5 dollars and 50 cents" NOT "$5.50" 
- NO asterisks, bullet points, dashes, or formatting symbols
- NO numbered lists like "1. Item 2. Item" - just speak naturally
- Say "dollars" and "cents" instead of dollar signs
- Use natural speech patterns like "we have" instead of bullet points

Speak naturally as if you're talking to someone on the phone. Be conversational, helpful, and confirm each change to their order clearly."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        order_tools = [tool for tool in tools if tool.name in ["update_order", "retrieve_menu_info"]]
        response = llm.bind_tools(order_tools).invoke(full_messages)
        return {"messages": [response], "conversation_phase": "ordering"}
    
    def general_agent(state: AgentState) -> Dict[str, Any]:
        """General conversational agent for other inquiries"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        
        system_context = f"""You are a friendly hotel concierge assistant talking to a guest in room {room_number}. You're having a natural conversation over the phone, so speak warmly and conversationally.
        
Handle general inquiries, provide information about hotel services, and maintain a friendly, professional conversation. If the guest wants to order food, guide them appropriately to our room service options.

CRITICAL: This will be read aloud by text-to-speech, so format everything for natural speech:
- Say prices as "5 dollars and 50 cents" NOT "$5.50" 
- NO asterisks, bullet points, dashes, or formatting symbols
- NO numbered lists like "1. Item 2. Item" - just speak naturally
- Say "dollars" and "cents" instead of dollar signs
- Use natural speech patterns like "we have" instead of bullet points
        
Speak naturally as if you're talking to someone on the phone. Be conversational, helpful, and make the guest feel welcome."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        response = llm.bind_tools([]).invoke(full_messages)  # No specific tools for general chat
        return {"messages": [response]}
    
    def order_placement_tools(state: AgentState) -> Dict[str, Any]:
        """Final order placement with all validation complete"""
        order_summary = state.get("order_summary", {})
        room_number = state.get("room_number", "")
        
        if order_summary and room_number:
            # Use shared tool instance from self.tools
            placement_tool = next((tool for tool in tools if isinstance(tool, OrderPlacementTool)), None)
            if not placement_tool:
                placement_tool = OrderPlacementTool()  # Fallback if not found
            
            result_message = placement_tool._run(
                order_summary=order_summary,
                room_number=room_number
            )
            
            return {
                "messages": [AIMessage(content=result_message)],
                "conversation_phase": "completed",
                "order_placed": True  # Mark order as successfully placed
            }
        else:
            return {
                "messages": [AIMessage(content="Unable to place order. Missing room number or order is empty.")],
                "conversation_phase": "ordering"
            }
    
    return {
        "menu_retrieval_agent": menu_retrieval_agent,
        "order_management_agent": order_management_agent,
        "general_agent": general_agent,
        "order_placement_tools": order_placement_tools
    }



@traceable(
    name="tool_execution",
    metadata={"node_type": "tool_execution", "agent_component": "tool_executor"},
    tags=["tools", "execution", "state_update"]
)
def tool_executor_node(state: AgentState, shared_tools: List[BaseTool] = None) -> Dict[str, Any]:
    """Execute the requested tool and update state if necessary"""
    
    last_message = state["messages"][-1]
    
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {} # No tools to execute

    # Use shared tools if provided, otherwise create new instances (fallback)
    if shared_tools:
        tool_instances = shared_tools
    else:
        tool_instances = [
            MenuRetrievalTool(),
            OrderPlacementTool(),
            OrderUpdateTool()
        ]
    
    tool_node = ToolNode(tool_instances)
    
    # result is a dict with a 'messages' key containing ToolMessage objects
    result = tool_node.invoke(state)
    
    updated_order_summary = state.get("order_summary", {}).copy()
    
    tool_messages = result['messages']

    # Correlate tool calls with tool messages
    for tool_call, tool_message in zip(last_message.tool_calls, tool_messages):
        if tool_call['name'] == 'update_order':
            try:
                update_data = json.loads(tool_message.content)
                item_name = update_data['item_name']
                quantity = update_data.get('quantity', 1)
                
                if update_data['action'] == 'add':
                    updated_order_summary[item_name] = updated_order_summary.get(item_name, 0) + quantity
                    logger.info(f"Order summary updated: added {quantity}x {item_name}")
                elif update_data['action'] == 'remove':
                    if item_name in updated_order_summary:
                        updated_order_summary[item_name] -= quantity
                        if updated_order_summary[item_name] <= 0:
                            del updated_order_summary[item_name]
                        logger.info(f"Order summary updated: removed {quantity}x {item_name}")
                    else:
                        logger.warning(f"Attempted to remove item not in order: {item_name}")
                elif update_data['action'] == 'set':
                    if quantity > 0:
                        updated_order_summary[item_name] = quantity
                        logger.info(f"Order summary updated: set {item_name} quantity to {quantity}")
                    else:
                        if item_name in updated_order_summary:
                            del updated_order_summary[item_name]
                            logger.info(f"Order summary updated: removed {item_name} by setting quantity to {quantity}")

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Could not parse tool output for order update: {e} - content: {tool_message.content}")

    result['order_summary'] = updated_order_summary
    result['tool_output'] = "Tool execution is complete."
    
    return result




# ============================================================================
# Graph Construction
# ============================================================================

class HotelConciergeAgent:
    """Main LangGraph agent for hotel concierge"""
    
    def __init__(self):
        self.llm = None
        self.tools = None
        self.graph = None
        self.app = None

    # Initialize LLM with enhanced tracing
    @traceable(
        name = "llm_node",
        metadata = {
            "agent_type": "hotel_concierge",
            "version": "2.0",
            "environment": os.getenv("LANGSMITH_RUN_ENVIRONMENT", "development")
        },
        tags=["hotel_concierge", "llm"]
    )    
    def initialize(self, groq_api_key: Optional[str] = None):
        """Initialize the agent with LLM and tools"""
        
        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        # Add LangSmith client initialization with enhanced configuration
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        )
        
        # Track initialization metrics (commented out - using @traceable decorators instead)
        # Note: log_metrics is not part of the official LangSmith API
        
       
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=os.getenv("GROQ_MODEL_NAME", "qwen/qwen3-32b"),  # Use environment variable with fallback
            temperature=0.1,
            max_tokens=1000
        )
        
        
        # Initialize tools
        self.tools = [
            MenuRetrievalTool(),
            OrderPlacementTool(),
            OrderUpdateTool()
        ]
        
        # Don't bind tools here - bind them per-node basis
        
        # Create the graph
        self._build_graph()
        
        logger.info("Hotel Concierge Agent initialized successfully")
    
    def _build_graph(self):
        """Build the enhanced LangGraph workflow with detailed phase management"""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # ============================================================================
        # NODE DEFINITIONS - Comprehensive conversation flow phases
        # ============================================================================
        
        # Phase 1: Guest Validation & Welcome
        workflow.add_node("guest_validation", guest_validation_node)
        
        # Phase 2: Intent Classification & Routing
        workflow.add_node("intent_classification", intent_classification_node)
        
        # Phase 3: Specialized Agent Nodes
        specialized_nodes = create_specialized_agent_nodes(self.llm, self.tools)
        workflow.add_node("menu_retrieval_agent", specialized_nodes["menu_retrieval_agent"])
        workflow.add_node("order_management_agent", specialized_nodes["order_management_agent"])
        workflow.add_node("general_agent", specialized_nodes["general_agent"])
        
        # Phase 4: Order Processing & Validation
        workflow.add_node("order_validation", order_validation_node)
        workflow.add_node("order_placement_tools", specialized_nodes["order_placement_tools"])
        
        # Phase 5: Tool Execution - pass shared tools to avoid repeated instantiation
        workflow.add_node("tools", lambda state: tool_executor_node(state, self.tools))
        
        # ============================================================================
        # EDGE DEFINITIONS - Detailed conversation flow with conditional routing
        # ============================================================================
        
        # START -> guest_validation (Entry point for all conversations)
        workflow.set_entry_point("guest_validation")
        
        # guest_validation -> [intent_classification | END]
        # Routes based on room validation status
        workflow.add_conditional_edges(
            "guest_validation",
            route_after_guest_validation,
            {
                "intent_classification": "intent_classification",
                "END": END
            }
        )
        
        # intent_classification -> [menu_retrieval_agent | order_management_agent | general_agent | order_validation]
        # Routes based on classified user intent
        workflow.add_conditional_edges(
            "intent_classification",
            route_after_intent_classification,
            {
                "menu_retrieval_agent": "menu_retrieval_agent",
                "order_management_agent": "order_management_agent", 
                "order_validation": "order_validation",
                "general_agent": "general_agent"
            }
        )
        
        # menu_retrieval_agent -> [tools | END]
        # If no tool is called, the agent has responded and the turn should end.
        workflow.add_conditional_edges(
            "menu_retrieval_agent",
            should_continue_to_tools,
            {
                "tools": "tools",
                "intent_classification": END
            }
        )
        
        # order_management_agent -> [tools | END]
        # If no tool is called, the agent has responded and the turn should end.
        workflow.add_conditional_edges(
            "order_management_agent",
            should_continue_to_tools,
            {
                "tools": "tools",
                "intent_classification": END
            }
        )
        
        # general_agent -> [intent_classification]
        # General inquiries return to intent classification for next action
        workflow.add_edge("general_agent", END)
        
        # order_validation -> [order_placement_tools | guest_validation | order_management_agent | general_agent | END]
        # Routes based on order validation result
        workflow.add_conditional_edges(
            "order_validation",
            route_after_order_validation,
            {
                "order_placement_tools": "order_placement_tools",
                "guest_validation": "guest_validation",
                "order_management_agent": "order_management_agent",
                "general_agent": "general_agent",
                "END": END
            }
        )
        
        # order_placement_tools -> [END | guest_validation]
        # Final order placement leads to completion or back to start for new orders
        workflow.add_conditional_edges(
            "order_placement_tools",
            should_end_conversation,
            {
                "END": END,
                "guest_validation": "guest_validation"
            }
        )
        
        # tools -> [menu_retrieval_agent | order_management_agent | general_agent]
        # Tool execution results route back to appropriate specialized agents
        workflow.add_conditional_edges(
            "tools",
            route_from_tools,
            {
                "menu_retrieval_agent": "menu_retrieval_agent",
                "order_management_agent": "order_management_agent",
                "general_agent": "general_agent"
            }
        )
        
        # Compile the graph
        self.app = workflow.compile()
        
        logger.info("Enhanced LangGraph workflow compiled successfully with detailed phase management")
    
    @traceable(
        name="process_message",
        metadata={
            "agent_type": "concierge",
            "interface": "conversation",
            "version": "2.0",
            "component": "langgraph_agent"
        },
        tags=["conversation", "message_processing", "hotel_concierge"]
    )
    async def process_message(self, message: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user message and return the response with comprehensive tracking"""
        
        if not self.app:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        # Track conversation start time for latency monitoring
        start_time = datetime.now()
        
        # Initialize state if not provided
        if current_state is None:
            current_state = {
                "messages": [],
                "room_number": None,
                "order_summary": {},
                "tool_output": None,
                "conversation_phase": "greeting",
                "order_placed": False,
                "error_count": 0
            }
        
        # Add user message to state
        current_state["messages"].append(HumanMessage(content=message))
        
        try:
            # Process through the graph
            result = await self.app.ainvoke(current_state)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Performance metrics are tracked via @traceable decorator metadata above
            # Additional metrics can be logged to langsmith through enhanced tracing
            logger.info(f"Message processed in {processing_time:.2f}ms - Phase: {result.get('conversation_phase', 'unknown')}")
            
            return result
            
        except Exception as e:
            # Track errors for debugging
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Error tracking via logs (log_metrics is not available in LangSmith API)
            logger.error(f"Processing error: {type(e).__name__} after {error_time:.2f}ms")
            
            logger.error(f"Error processing message: {e}")
            raise
    
    def process_message_sync(self, message: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous version of process_message"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.process_message(message, current_state))


# ============================================================================
# Agent Singleton
# ============================================================================

_agent = None

def get_concierge_agent() -> HotelConciergeAgent:
    """Get or create the concierge agent singleton"""
    global _agent
    if _agent is None:
        _agent = HotelConciergeAgent()
        _agent.initialize()
    return _agent