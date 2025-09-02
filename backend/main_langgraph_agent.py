"""
LangGraph Agent for Hotel Concierge System
Replaces pipecat-flows with dynamic, tool-based agent architecture
NOW REFACTORED TO USE PRODUCTION RAG SYSTEM
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
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from loguru import logger
from langsmith import traceable, Client

# Import the new production-ready RAG system
from production_rag_system import create_production_rag_system, ProductionRAGSystem


# setup the project name for LangSmith
os.environ["LANGSMITH_PROJECT"] = "voice-ai-concierge"

# ============================================================================
# Singleton for Production RAG System
# ============================================================================

_rag_system: Optional[ProductionRAGSystem] = None

def get_production_rag_system() -> ProductionRAGSystem:
    """Get or create the ProductionRAGSystem singleton"""
    global _rag_system
    if _rag_system is None:
        logger.info("Initializing ProductionRAGSystem singleton...")
        _rag_system = create_production_rag_system()
        _rag_system.initialize()
        logger.info("ProductionRAGSystem singleton initialized.")
    return _rag_system

# ============================================================================
# Agent State Definition
# ============================================================================

class AgentState(TypedDict):
    """Enhanced state maintained across the conversation with detailed phase tracking"""
    messages: Annotated[list[BaseMessage], add_messages]
    room_number: Optional[str]
    order_summary: Dict[str, Any]
    tool_output: Optional[str]
    validation_status: Optional[str]
    intent: Optional[str]
    validation_result: Optional[str]
    conversation_phase: Optional[str]
    last_agent: Optional[str]
    order_confirmed: Optional[bool]
    order_placed: Optional[bool]
    error_count: Optional[int]


# ============================================================================
# Tool Definitions (Refactored)
# ============================================================================

class MenuRetrievalInput(BaseModel):
    """Input for menu information retrieval"""
    query: str = Field(description="User's question about the menu (e.g., 'what salads do you have?', 'is the burger gluten-free?')")


class MenuRetrievalTool(BaseTool):
    """Tool for retrieving menu information using the Production RAG System"""
    name: str = "retrieve_menu_info"
    description: str = "Retrieve relevant menu information based on user queries using the production RAG system."
    args_schema: type[BaseModel] = MenuRetrievalInput
    
    @traceable(name="rag_retrieve_production", tags=["rag", "retrieval", "menu", "production"])
    def _run(self, query: str) -> str:
        """Execute the RAG pipeline with error handling"""
        try:
            system = get_production_rag_system()
            context = system.get_quick_context(query)
            
            if not context or "I'm unable to find relevant information" in context:
                return self._get_fallback_menu_info(query)
            
            return context
            
        except Exception as e:
            logger.error(f"Error in production menu retrieval: {e}")
            return self._get_fallback_menu_info(query)
    
    def _get_fallback_menu_info(self, query: str) -> str:
        """Provide minimal fallback menu information when RAG is unavailable"""
        logger.warning(f"RAG unavailable, providing minimal fallback for query: {query}")
        return "I'm sorry, our menu system is temporarily unavailable. We offer pizzas, sandwiches, salads, and more. For specifics, please call extension one two three four."


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
        """Get item price using the Production RAG System"""
        try:
            system = get_production_rag_system()
            price_query = f"What is the price of {item_name}? Show me the exact price in USD."
            result = system.process_query(price_query, include_debug_info=True)
            
            retrieved_docs = result.get("debug_info", {}).get("retrieved_documents", [])

            for doc in retrieved_docs:
                metadata = doc.get('metadata', {})
                stored_item_name = metadata.get('item_name', '').lower()
                
                if (stored_item_name == item_name.lower() or 
                    item_name.lower() in stored_item_name or 
                    stored_item_name in item_name.lower()):
                    
                    price_str = metadata.get('price', '')
                    if price_str:
                        price_clean = price_str.replace('$', '').strip()
                        if price_clean:
                            return float(price_clean)
            
            logger.warning(f"Could not find price in metadata for '{item_name}', using default 12.00")
            return 12.00
            
        except Exception as e:
            logger.error(f"Error getting price from production RAG for '{item_name}': {e}")
            return 12.00

    @traceable(name="order_placement_webhook_production", tags=["order", "webhook", "production"])
    async def _arun(self, order_summary: Dict[str, int], room_number: str) -> str:
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            logger.error("WEBHOOK_URL environment variable not set. Cannot place order.")
            return "I'm sorry, the ordering system is currently unavailable due to a configuration issue. Please contact the front desk for assistance."

        try:
            item_names = ", ".join(order_summary.keys())
            total_quantity = sum(order_summary.values())
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
    name: str = "update_order"
    description: str = "Add, remove, or set the quantity of items in the current order cart"
    args_schema: type[BaseModel] = OrderUpdateInput
    
    @traceable(name="order_update", tags=["order", "cart", "update"])
    def _run(self, action: str, item_name: str, quantity: int = 1) -> str:
        try:
            return json.dumps({
                "action": action.lower(),
                "item_name": item_name,
                "quantity": quantity
            })
        except Exception as e:
            logger.error(f"Error creating order update data: {e}")
            return json.dumps({"error": "Failed to process update."})


# ============================================================================
# Agent Nodes & Decision Functions (Refactored)
# ============================================================================

def _convert_words_to_digits(text: str) -> str:
    """Converts number words in a string to digits."""
    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'oh': '0'
    }
    
    processed_text = text.lower()
    for word, digit in word_to_digit.items():
        processed_text = re.sub(r'\b' + word + r'\b', digit, processed_text)
        
    return processed_text


@traceable(
    name="guest_validation",
    metadata={"node_type": "validation", "agent_component": "guest_validation"},
    tags=["validation", "guest", "room"]
)
def guest_validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate guest information and room number, handling words and digits."""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if state.get("room_number"):
        return {"validation_status": "room_validated"}
    
    if last_message and hasattr(last_message, 'content'):
        content = str(last_message.content)
        
        # Convert words to digits and extract all numbers
        processed_content = _convert_words_to_digits(content)
        digits = re.sub(r'[^0-9]', '', processed_content)
        
        room_number = None
        # First, look for a 3 or 4 digit number
        match = re.search(r'\d{3,4}', digits)
        if match:
            room_number = match.group(0)

        if room_number:
            return {
                "room_number": room_number,
                "validation_status": "room_captured",
                "messages": [AIMessage(content=f"Thank you! I've noted your room number as {room_number}. How can I assist you today?")]
            }
    
    return {
        "validation_status": "room_needed",
        "messages": [AIMessage(content="Welcome to our hotel room service! Could you please provide your room number so I can assist you better?")]
    }


@traceable(name="intent_classification_production", tags=["intent", "classification", "production"])
def intent_classification_node(state: AgentState) -> Dict[str, Any]:
    """Classify user intent using the Production RAG System."""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if not last_message or not hasattr(last_message, 'content') or not str(last_message.content).strip():
        return {"intent": "unknown"}
    
    content = str(last_message.content)
    
    try:
        system = get_production_rag_system()
        intent_classifier = system.intent_manager.get_classifier()
        classification_result = intent_classifier.classify_intent(content)
        
        intent = classification_result.get("intent", "general_assistance")
        
        if intent == "general_assistance":
            mapped_intent = "general_inquiry"
        else:
            mapped_intent = intent

        logger.info(f"Production intent classification: '{intent}' -> Mapped to: '{mapped_intent}' with confidence {classification_result.get('confidence')}")
        
        return {"intent": mapped_intent}
        
    except Exception as e:
        logger.error(f"Error in production intent classification: {e}")
        return {"intent": "general_inquiry"}


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
        return "END"
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
        return "END"
    elif validation_result == "missing_room":
        return "guest_validation"
    elif validation_result == "empty_order":
        return "order_management_agent"
    else:
        return "general_agent"


def should_continue_to_tools(state: AgentState) -> str:
    """Determine if we need to execute tools"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
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
        
        response = llm.bind_tools([]).invoke(full_messages)
        return {"messages": [response]}
    
    def order_placement_tools(state: AgentState) -> Dict[str, Any]:
        """Final order placement with all validation complete"""
        order_summary = state.get("order_summary", {})
        room_number = state.get("room_number", "")
        
        if order_summary and room_number:
            placement_tool = next((tool for tool in tools if isinstance(tool, OrderPlacementTool)), None)
            if not placement_tool:
                placement_tool = OrderPlacementTool()
            
            result_message = placement_tool._run(
                order_summary=order_summary,
                room_number=room_number
            )
            
            return {
                "messages": [AIMessage(content=result_message)],
                "conversation_phase": "completed",
                "order_placed": True
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
        return {}

    if shared_tools:
        tool_instances = shared_tools
    else:
        tool_instances = [
            MenuRetrievalTool(),
            OrderPlacementTool(),
            OrderUpdateTool()
        ]
    
    tool_node = ToolNode(tool_instances)
    
    result = tool_node.invoke(state)
    
    updated_order_summary = state.get("order_summary", {}).copy()
    
    tool_messages = result['messages']

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

    @traceable(
        name = "llm_node_production",
        tags=["hotel_concierge", "llm", "production"]
    )    
    def initialize(self, groq_api_key: Optional[str] = None):
        """Initialize the agent with LLM and tools"""
        
        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        )
        
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=os.getenv("GROQ_MODEL_NAME", "qwen/qwen3-32b"),
            temperature=0.1,
            max_tokens=1000
        )
        
        # self.llm = ChatOpenAI(
        #     openai_api_key=os.getenv("OPENAI_API_KEY"),
        #     model_name=os.getenv("OPENAI_MODEL_NAME"),
        #     base_url=os.getenv("OPENAI_BASE_URL"),
        #     temperature=0.1,
        #     max_tokens=1000
        # )

        self.tools = [
            MenuRetrievalTool(),
            OrderPlacementTool(),
            OrderUpdateTool()
        ]
        
        self._build_graph()
        
        logger.info("Hotel Concierge Agent initialized successfully with Production Systems")
    
    def _build_graph(self):
        """Build the enhanced LangGraph workflow with detailed phase management"""
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("guest_validation", guest_validation_node)
        workflow.add_node("intent_classification", intent_classification_node)
        
        specialized_nodes = create_specialized_agent_nodes(self.llm, self.tools)
        workflow.add_node("menu_retrieval_agent", specialized_nodes["menu_retrieval_agent"])
        workflow.add_node("order_management_agent", specialized_nodes["order_management_agent"])
        workflow.add_node("general_agent", specialized_nodes["general_agent"])
        
        workflow.add_node("order_validation", order_validation_node)
        workflow.add_node("order_placement_tools", specialized_nodes["order_placement_tools"])
        
        workflow.add_node("tools", lambda state: tool_executor_node(state, self.tools))
        
        workflow.set_entry_point("guest_validation")
        
        workflow.add_conditional_edges(
            "guest_validation",
            route_after_guest_validation,
            {"intent_classification": "intent_classification", "END": END}
        )
        
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
        
        workflow.add_conditional_edges(
            "menu_retrieval_agent",
            should_continue_to_tools,
            {"tools": "tools", "intent_classification": END}
        )
        
        workflow.add_conditional_edges(
            "order_management_agent",
            should_continue_to_tools,
            {"tools": "tools", "intent_classification": END}
        )
        
        workflow.add_edge("general_agent", END)
        
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
        
        workflow.add_conditional_edges(
            "order_placement_tools",
            should_end_conversation,
            {"END": END, "guest_validation": "guest_validation"}
        )
        
        workflow.add_conditional_edges(
            "tools",
            route_from_tools,
            {
                "menu_retrieval_agent": "menu_retrieval_agent",
                "order_management_agent": "order_management_agent",
                "general_agent": "general_agent"
            }
        )
        
        self.app = workflow.compile()
        
        logger.info("Enhanced LangGraph workflow compiled successfully with detailed phase management")
    
    @traceable(
        name="process_message_production",
        tags=["conversation", "message_processing", "hotel_concierge", "production"]
    )
    async def process_message(self, message: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user message and return the response with comprehensive tracking"""
        
        if not self.app:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        start_time = datetime.now()
        
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
        
        current_state["messages"].append(HumanMessage(content=message))
        
        try:
            result = await self.app.ainvoke(current_state)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Message processed in {processing_time:.2f}ms - Phase: {result.get('conversation_phase', 'unknown')}")
            
            return result
            
        except Exception as e:
            error_time = (datetime.now() - start_time).total_seconds() * 1000
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
