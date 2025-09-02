"""
Integration example for COT reasoning in main_langgraph_agent.py
This shows how to modify the existing agent to use COT
"""

# Add this import at the top of main_langgraph_agent.py
from cot_reasoning import create_cot_enhanced_llm, COTWrapper

# Modify the HotelConciergeAgent.initialize method:
def initialize_with_cot(self, groq_api_key: Optional[str] = None):
    """Initialize the agent with COT-enhanced LLM and tools"""
    
    if not groq_api_key:
        groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    self.langsmith_client = Client(
        api_key=os.getenv("LANGSMITH_API_KEY"),
        api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    )
    
    # Original LLM creation
    base_llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=os.getenv("GROQ_MODEL_NAME", "mixtral-8x7b-32768"),
        temperature=0.1,
        max_tokens=1000
    )
    
    # Wrap with COT if enabled
    enable_cot = os.getenv("ENABLE_COT", "false").lower() == "true"
    if enable_cot:
        self.llm = COTWrapper(base_llm)
        logger.info("COT reasoning enabled for LLM")
    else:
        self.llm = base_llm
        logger.info("Using standard LLM without COT")
    
    self.tools = [
        MenuRetrievalTool(),
        OrderPlacementTool(),
        OrderUpdateTool()
    ]
    
    self._build_graph()
    
    logger.info("Hotel Concierge Agent initialized with COT support")


# Modify create_specialized_agent_nodes to support COT:
def create_specialized_agent_nodes_with_cot(llm, tools):
    """Create specialized agent nodes with COT support"""
    
    # Check if llm is COT-wrapped
    is_cot_wrapped = isinstance(llm, COTWrapper)
    
    def menu_retrieval_agent(state: AgentState) -> Dict[str, Any]:
        """Specialized agent for menu-related queries with COT support"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        
        system_context = f"""You are a friendly menu specialist for hotel room service talking to a guest in room {room_number}. 
        
Your role is to help guests browse our menu, answer questions about food items, ingredients, prices, and availability. 
Always use the retrieve_menu_info tool to get current and accurate information - never guess or provide information from memory.

CRITICAL: This will be read aloud by text-to-speech, so format everything for natural speech:
- Say prices as "5 dollars and 50 cents" NOT "$5.50" 
- NO asterisks, bullet points, dashes, or formatting symbols
- NO numbered lists like "1. Item 2. Item" - just speak naturally
- Say "dollars" and "cents" instead of dollar signs
- Use natural speech patterns like "we have" instead of bullet points

Speak naturally as if you're talking to someone on the phone. Be conversational, helpful, and enthusiastic about our menu offerings."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        if is_cot_wrapped:
            # Use COT-enhanced reasoning
            context = {
                "room_number": room_number,
                "order_summary": state.get("order_summary", {}),
                "conversation_phase": "menu_browsing"
            }
            # First get COT reasoning
            cot_response = llm.invoke_with_cot(full_messages, context)
            
            # Then bind tools and get final response
            tool_llm = llm.llm.bind_tools([tool for tool in tools if tool.name == "retrieve_menu_info"])
            final_messages = full_messages + [cot_response]
            response = tool_llm.invoke(final_messages)
        else:
            # Original behavior
            response = llm.bind_tools([tool for tool in tools if tool.name == "retrieve_menu_info"]).invoke(full_messages)
        
        return {"messages": [response], "conversation_phase": "menu_browsing"}
    
    def order_management_agent(state: AgentState) -> Dict[str, Any]:
        """Specialized agent for order placement with COT support"""
        messages = state["messages"]
        room_number = state.get("room_number", "")
        order_summary = state.get("order_summary", {})
        
        system_context = f"""You are a helpful order specialist for hotel room service talking to a guest in room {room_number}.

Current order: {order_summary if order_summary else 'Empty'}

Your role is to help guests add items to their order, modify quantities, remove items, and manage their current order.

IMPORTANT: If a guest asks to order a category item, use retrieve_menu_info to find specific options.

CRITICAL: Format for text-to-speech - natural speech only, no symbols or formatting."""
        
        system_message = SystemMessage(content=system_context)
        full_messages = [system_message] + messages
        
        if is_cot_wrapped:
            # COT-enhanced reasoning for complex order management
            context = {
                "room_number": room_number,
                "order_summary": order_summary,
                "conversation_phase": "ordering"
            }
            
            # Check if this needs complex reasoning
            last_message = messages[-1] if messages else None
            needs_cot = False
            
            if last_message and hasattr(last_message, 'content'):
                # Trigger COT for complex order modifications
                complex_keywords = ['change', 'modify', 'instead', 'replace', 'update', 'actually']
                needs_cot = any(keyword in last_message.content.lower() for keyword in complex_keywords)
            
            if needs_cot:
                cot_response = llm.invoke_with_cot(full_messages, context)
                order_tools = [tool for tool in tools if tool.name in ["update_order", "retrieve_menu_info"]]
                tool_llm = llm.llm.bind_tools(order_tools)
                final_messages = full_messages + [cot_response]
                response = tool_llm.invoke(final_messages)
            else:
                # Direct response for simple additions
                order_tools = [tool for tool in tools if tool.name in ["update_order", "retrieve_menu_info"]]
                response = llm.llm.bind_tools(order_tools).invoke(full_messages)
        else:
            # Original behavior
            order_tools = [tool for tool in tools if tool.name in ["update_order", "retrieve_menu_info"]]
            response = llm.bind_tools(order_tools).invoke(full_messages)
        
        return {"messages": [response], "conversation_phase": "ordering"}
    
    # Return the modified agent nodes
    return {
        "menu_retrieval_agent": menu_retrieval_agent,
        "order_management_agent": order_management_agent,
        # ... other agents remain the same
    }