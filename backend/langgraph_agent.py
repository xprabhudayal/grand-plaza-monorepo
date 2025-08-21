"""
LangGraph Agent for Hotel Concierge System
Replaces pipecat-flows with dynamic, tool-based agent architecture
"""

import os
import json
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

# Try to import RAG pipeline - make it optional
try:
    from rag_pipeline import get_rag_pipeline
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG pipeline not available: {e}")
    RAG_AVAILABLE = False
    def get_rag_pipeline():
        raise ImportError("RAG pipeline dependencies not installed")


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
        """Provide fallback menu information when RAG is unavailable"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["breakfast", "morning", "cereal", "eggs", "pancake"]):
            return """Breakfast Menu:
            - American Breakfast: Eggs, bacon, toast, hash browns - $12
            - Continental Breakfast: Pastries, fruits, cereals - $8
            - Pancakes: Stack of 3 with syrup and butter - $9
            - Omelet: Choice of fillings (cheese, vegetables, meat) - $11"""
            
        elif any(word in query_lower for word in ["appetizer", "starter", "soup", "salad"]):
            return """Appetizers & Salads:
            - Caesar Salad: Crisp romaine, parmesan, croutons - $8
            - Soup of the Day: Ask for today's selection - $6
            - Chicken Wings: Buffalo or BBQ style - $10
            - Garlic Bread: Fresh baked with herbs - $5"""
            
        elif any(word in query_lower for word in ["main", "entree", "dinner", "lunch"]):
            return """Main Courses:
            - Grilled Chicken: With vegetables and rice - $18
            - Beef Steak: 8oz sirloin with potato - $24
            - Pasta Marinara: Fresh tomato sauce - $14
            - Fish & Chips: Beer battered cod - $16"""
            
        elif any(word in query_lower for word in ["sandwich", "burger", "wrap"]):
            return """Sandwiches & Wraps:
            - Club Sandwich: Turkey, bacon, lettuce, tomato - $12
            - Cheeseburger: Beef patty with cheese and fries - $14
            - Chicken Wrap: Grilled chicken with vegetables - $11
            - Veggie Sandwich: Fresh vegetables and hummus - $9"""
            
        elif any(word in query_lower for word in ["dessert", "sweet", "cake", "ice cream"]):
            return """Desserts:
            - Chocolate Cake: Rich chocolate layer cake - $7
            - Ice Cream: Vanilla, chocolate, or strawberry - $5
            - Apple Pie: Classic with vanilla ice cream - $6
            - Fruit Salad: Fresh seasonal fruits - $5"""
            
        elif any(word in query_lower for word in ["drink", "beverage", "coffee", "tea", "juice"]):
            return """Beverages:
            - Coffee: Fresh brewed, espresso drinks - $3-5
            - Tea: Various herbal and black teas - $3
            - Fresh Juices: Orange, apple, cranberry - $4
            - Soft Drinks: Coke, Pepsi, Sprite - $3"""
            
        else:
            return """Our full menu includes:
            - Breakfast: Eggs, pancakes, cereals, pastries
            - Appetizers & Salads: Soups, salads, wings, bread
            - Main Courses: Chicken, beef, pasta, seafood
            - Sandwiches: Burgers, wraps, club sandwiches
            - Desserts: Cakes, ice cream, pies, fruit
            - Beverages: Coffee, tea, juices, soft drinks
            
            What category would you like to know more about?"""


class OrderPlacementInput(BaseModel):
    """Input for placing an order"""
    order_summary: str = Field(description="Complete order summary with items and quantities")
    room_number: str = Field(description="Validated guest room number")


class OrderPlacementTool(BaseTool):
    """Tool for placing orders via API"""
    name: str = "place_order"
    description: str = "Place an order by making POST request to /api/v1/orders/ endpoint"
    args_schema: type[BaseModel] = OrderPlacementInput
    
    async def _arun(self, order_summary: str, room_number: str) -> str:
        """Place order asynchronously"""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            # Parse order summary to create order data
            order_data = {
                "guest_room": room_number,
                "items": [],
                "order_status": "pending",
                "total_amount": 0.0,
                "special_instructions": ""
            }
            
            # This is a simplified order parsing - in production, you'd want more robust parsing
            # For now, we'll pass the order summary as special instructions
            order_data["special_instructions"] = f"Order: {order_summary}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base_url}/api/v1/orders/",
                    json=order_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 201 or response.status == 200:
                        result = await response.json()
                        order_id = result.get("id", "unknown")
                        return f"Order placed successfully! Your order ID is {order_id}. Estimated delivery time is 25-30 minutes."
                    else:
                        error_text = await response.text()
                        logger.error(f"Order placement failed: {response.status} - {error_text}")
                        return f"Sorry, I couldn't place your order right now. Please try again or contact the front desk."
                        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return "I'm having trouble placing your order right now. Please contact the front desk for assistance."
    
    def _run(self, order_summary: str, room_number: str) -> str:
        """Synchronous wrapper"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(order_summary, room_number))


class OrderUpdateInput(BaseModel):
    """Input for updating order"""
    action: str = Field(description="Action to perform: 'add' or 'remove'")
    item_name: str = Field(description="Name of the item to add or remove")
    quantity: int = Field(description="Quantity of the item", default=1)


class OrderUpdateTool(BaseTool):
    """Tool for managing the order cart"""
    name: str = "update_order"
    description: str = "Add or remove items from the current order cart"
    args_schema: type[BaseModel] = OrderUpdateInput
    
    def _run(self, action: str, item_name: str, quantity: int = 1) -> str:
        """Update the order summary"""
        try:
            # This tool manages the order_summary in the agent's state
            # For now, we'll return a formatted response that the agent can use
            if action.lower() == "add":
                return f"Added {quantity}x {item_name} to your order."
            elif action.lower() == "remove":
                return f"Removed {quantity}x {item_name} from your order."
            else:
                return "Invalid action. Please use 'add' or 'remove'."
                
        except Exception as e:
            logger.error(f"Error updating order: {e}")
            return "I had trouble updating your order. Please try again."


# ============================================================================
# Agent Nodes & Decision Functions
# ============================================================================

def guest_validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate guest information and room number"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    # Check if room number is already captured
    if state.get("room_number"):
        return {"validation_status": "room_validated"}
    
    # Check if last message contains room number pattern
    if last_message and hasattr(last_message, 'content'):
        content = str(last_message.content).lower()
        import re
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


def intent_classification_node(state: AgentState) -> Dict[str, Any]:
    """Classify user intent for routing"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    if not last_message or not hasattr(last_message, 'content'):
        return {"intent": "unknown"}
    
    content = str(last_message.content).lower()
    
    # Intent classification logic
    menu_keywords = ["menu", "food", "pizza", "sandwich", "beverage", "what do you have", "options"]
    order_keywords = ["order", "add", "want", "get", "place", "buy"]
    modify_keywords = ["change", "remove", "cancel", "modify", "update", "delete"]
    confirm_keywords = ["confirm", "yes", "place order", "finalize", "checkout"]
    
    if any(keyword in content for keyword in confirm_keywords):
        return {"intent": "order_confirmation"}
    elif any(keyword in content for keyword in modify_keywords):
        return {"intent": "order_modification"}
    elif any(keyword in content for keyword in order_keywords):
        return {"intent": "order_placement"}
    elif any(keyword in content for keyword in menu_keywords):
        return {"intent": "menu_inquiry"}
    else:
        return {"intent": "general_inquiry"}


def order_validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate order before placement"""
    order_summary = state.get("order_summary", {})
    room_number = state.get("room_number")
    
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
        
        system_context = f"""You are a menu specialist for hotel room service in room {room_number}. 
        Your role is to help guests browse the menu, answer questions about food items, 
        ingredients, prices, and availability. Use the retrieve_menu_info tool to retrieve current menu items."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        response = llm.bind_tools([tool for tool in tools if tool.name == "retrieve_menu_info"]).invoke(full_messages)
        return {"messages": [response], "conversation_phase": "menu_browsing"}
    
    def order_management_agent(state: AgentState) -> Dict[str, Any]:
        """Specialized agent for order placement and modification"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        order_summary = state.get("order_summary", {})
        
        system_context = f"""You are an order specialist for hotel room service in room {room_number}.
        Current order: {order_summary if order_summary else 'Empty'}
        Your role is to help guests add items to their order, modify quantities, remove items,
        and manage their current order. Use order management tools as needed."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        order_tools = [tool for tool in tools if tool.name in ["update_order"]]
        response = llm.bind_tools(order_tools).invoke(full_messages)
        return {"messages": [response], "conversation_phase": "ordering"}
    
    def general_agent(state: AgentState) -> Dict[str, Any]:
        """General conversational agent for other inquiries"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        
        system_context = f"""You are a helpful hotel concierge assistant for room {room_number}.
        Handle general inquiries, provide information about hotel services, and maintain 
        a friendly, professional conversation. If the guest wants to order food, 
        guide them appropriately."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        response = llm.bind_tools([]).invoke(full_messages)  # No specific tools for general chat
        return {"messages": [response]}
    
    def order_placement_tools(state: AgentState) -> Dict[str, Any]:
        """Final order placement with all validation complete"""
        order_summary = state.get("order_summary", {})
        room_number = state.get("room_number", "")
        
        if order_summary and room_number:
            # This would integrate with actual order placement system
            confirmation_msg = f"Order placed successfully for room {room_number}! Your items: {list(order_summary.keys())}. Estimated delivery: 25-30 minutes."
            return {
                "messages": [AIMessage(content=confirmation_msg)],
                "conversation_phase": "completed"
            }
        else:
            return {
                "messages": [AIMessage(content="Unable to place order. Missing information.")],
                "conversation_phase": "ordering"
            }
    
    return {
        "menu_retrieval_agent": menu_retrieval_agent,
        "order_management_agent": order_management_agent,
        "general_agent": general_agent,
        "order_placement_tools": order_placement_tools
    }


def create_agent_node(llm, tools):
    """Create the main agent reasoning node - DEPRECATED in enhanced version"""
    
    def agent_node(state: AgentState) -> Dict[str, Any]:
        """Main agent reasoning logic"""
        
        # Build system prompt
        system_prompt = """You are a helpful hotel room service concierge assistant. Your role is to:

1. Help guests with menu inquiries using the retrieve_menu_info tool
2. Take and manage food orders using the update_order tool  
3. Place final orders using the place_order tool (only when guest confirms)

IMPORTANT GUIDELINES:
- Always greet guests warmly and ask for their room number first
- Use retrieve_menu_info tool for ANY menu-related questions
- Keep track of items being added to the order using update_order tool
- Only use place_order tool when the guest explicitly confirms they want to place the order
- Be conversational and helpful, ask clarifying questions
- If technical issues occur, suggest contacting the front desk

Current order summary: {order_summary}
Guest room number: {room_number}
"""
        
        # Add system message with current state context
        messages = [SystemMessage(content=system_prompt.format(
            order_summary=json.dumps(state.get("order_summary", {}), indent=2),
            room_number=state.get("room_number", "Not provided")
        ))]
        messages.extend(state["messages"])
        
        # Get response from LLM
        response = llm.with_config({"tools": tools}).invoke(messages)
        
        return {"messages": [response]}
    
    return agent_node


def tool_executor_node(state: AgentState) -> Dict[str, Any]:
    """Execute the requested tool"""
    
    last_message = state["messages"][-1]
    
    # Extract tool calls from the message
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # Create tool node to handle execution
        tool_node = ToolNode([
            MenuRetrievalTool(),
            OrderPlacementTool(), 
            OrderUpdateTool()
        ])
        
        # Execute tools
        result = tool_node.invoke(state)
        
        # Update order summary if order was updated
        if any(tool_call.get("name") == "update_order" for tool_call in last_message.tool_calls):
            # Extract order updates and maintain state
            updated_order = state.get("order_summary", {})
            # Tool result will be in the messages, parse it to update state
            # This is simplified - in production you'd want more robust state management
            
            return {
                "messages": result.get("messages", []),
                "order_summary": updated_order,
                "tool_output": "Order updated"
            }
        
        return result
    
    return {"messages": []}


def should_continue(state: AgentState) -> str:
    """Determine next step in the workflow"""
    
    last_message = state["messages"][-1]
    
    # If the last message has tool calls, go to tool execution
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end the conversation turn
    return END


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
        
    def initialize(self, groq_api_key: Optional[str] = None):
        """Initialize the agent with LLM and tools"""
        
        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Initialize LLM
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="qwen/qwen2-32b-instruct",  # Updated model name
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
        
        # Phase 5: Tool Execution
        workflow.add_node("tools", tool_executor_node)
        
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
        
        # menu_retrieval_agent -> [tools | intent_classification]
        # Tool execution for menu queries or back to intent classification
        workflow.add_conditional_edges(
            "menu_retrieval_agent",
            should_continue_to_tools,
            {
                "tools": "tools",
                "intent_classification": "intent_classification"
            }
        )
        
        # order_management_agent -> [tools | intent_classification]
        # Tool execution for order management or back to intent classification
        workflow.add_conditional_edges(
            "order_management_agent",
            should_continue_to_tools,
            {
                "tools": "tools",
                "intent_classification": "intent_classification"
            }
        )
        
        # general_agent -> [intent_classification]
        # General inquiries return to intent classification for next action
        workflow.add_edge("general_agent", "intent_classification")
        
        # order_validation -> [order_placement_tools | guest_validation | order_management_agent | general_agent]
        # Routes based on order validation result
        workflow.add_conditional_edges(
            "order_validation",
            route_after_order_validation,
            {
                "order_placement_tools": "order_placement_tools",
                "guest_validation": "guest_validation",
                "order_management_agent": "order_management_agent",
                "general_agent": "general_agent"
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
    
    async def process_message(self, message: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user message and return the response"""
        
        if not self.app:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        # Initialize state if not provided
        if current_state is None:
            current_state = {
                "messages": [],
                "room_number": None,
                "order_summary": {},
                "tool_output": None
            }
        
        # Add user message to state
        current_state["messages"].append(HumanMessage(content=message))
        
        # Process through the graph
        result = await self.app.ainvoke(current_state)
        
        return result
    
    def process_message_sync(self, message: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous version of process_message"""
        import asyncio
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