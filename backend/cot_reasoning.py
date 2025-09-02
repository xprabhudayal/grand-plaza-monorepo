"""
Chain of Thought (COT) Reasoning Module for Hotel Concierge System
Enables step-by-step reasoning for any LLM model
"""

import os
from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from loguru import logger
from langsmith import traceable
import re


class COTWrapper:
    """
    Chain of Thought wrapper for LLM calls
    Adds reasoning capabilities to basic LLM models
    """
    
    def __init__(self, llm, enable_cot: bool = None):
        """
        Initialize COT wrapper
        
        Args:
            llm: Base LLM instance (ChatGroq or ChatOpenAI)
            enable_cot: Whether to enable COT (defaults to env var)
        """
        self.llm = llm
        self.enable_cot = enable_cot if enable_cot is not None else os.getenv("ENABLE_COT", "false").lower() == "true"
        self.cot_mode = os.getenv("COT_MODE", "simple")  # simple, structured, or adaptive
        
        logger.info(f"COT Wrapper initialized - Enabled: {self.enable_cot}, Mode: {self.cot_mode}")
    
    def _create_cot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """
        Create a COT reasoning prompt based on the mode
        """
        if self.cot_mode == "structured":
            return self._structured_cot_prompt(task, context)
        elif self.cot_mode == "adaptive":
            return self._adaptive_cot_prompt(task, context)
        else:
            return self._simple_cot_prompt(task, context)
    
    def _simple_cot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Simple COT prompt - basic reasoning steps"""
        return f"""Let's think step by step about this task.

Task: {task}
Context: Room {context.get('room_number', 'unknown')}, Current order: {context.get('order_summary', {})}

First, I need to understand what the user is asking for.
Second, I should consider what information I need to gather.
Third, I should determine the appropriate action to take.
Finally, I should formulate a helpful response.

My reasoning:"""
    
    def _structured_cot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Structured COT prompt - detailed reasoning framework"""
        return f"""<reasoning_framework>
Task: {task}
Current State:
- Room Number: {context.get('room_number', 'Not provided')}
- Order Summary: {context.get('order_summary', {})}
- Conversation Phase: {context.get('conversation_phase', 'unknown')}

Step 1 - Intent Analysis:
What is the user's primary intent? What are they trying to accomplish?

Step 2 - Information Assessment:
What information do I have? What information do I need?

Step 3 - Constraint Check:
Are there any constraints or validations I need to consider?

Step 4 - Action Planning:
What specific actions should I take? What tools do I need to use?

Step 5 - Response Formulation:
How should I respond to be most helpful and clear?

</reasoning_framework>

My step-by-step reasoning:"""
    
    def _adaptive_cot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Adaptive COT prompt - changes based on conversation phase"""
        phase = context.get('conversation_phase', 'greeting')
        
        if phase == 'greeting':
            return f"""This is the start of a conversation. I need to:
1. Greet the guest warmly
2. Identify if they've provided their room number
3. Understand their initial request
4. Set the appropriate conversation tone

User input: {task}
My reasoning:"""
            
        elif phase == 'menu_browsing':
            return f"""The guest is browsing the menu. I need to:
1. Identify what specific menu information they want
2. Use the retrieve_menu_info tool if needed
3. Present information in a clear, appetizing way
4. Be ready to help them make selections

User input: {task}
Current context: {context}
My reasoning:"""
            
        elif phase == 'ordering':
            return f"""The guest is placing/modifying an order. I need to:
1. Understand if they're adding, removing, or modifying items
2. Clarify quantities and specific items
3. Update the order summary correctly
4. Confirm changes clearly

User input: {task}
Current order: {context.get('order_summary', {})}
My reasoning:"""
            
        else:
            return self._simple_cot_prompt(task, context)
    
    def _extract_reasoning_and_response(self, full_response: str) -> Dict[str, str]:
        """
        Extract reasoning and final response from COT output
        """
        # Pattern to separate reasoning from final response
        reasoning_pattern = r"My reasoning:(.*?)(?:Final response:|Therefore,|In conclusion,|$)"
        response_pattern = r"(?:Final response:|Therefore,|In conclusion,)(.*?)$"
        
        reasoning_match = re.search(reasoning_pattern, full_response, re.DOTALL)
        response_match = re.search(response_pattern, full_response, re.DOTALL)
        
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        
        if response_match:
            final_response = response_match.group(1).strip()
        else:
            # If no clear separation, use the last paragraph as response
            paragraphs = full_response.split('\n\n')
            final_response = paragraphs[-1] if paragraphs else full_response
        
        return {
            "reasoning": reasoning,
            "response": final_response,
            "full_output": full_response
        }
    
    @traceable(name="cot_enhanced_invoke", tags=["cot", "reasoning"])
    async def ainvoke_with_cot(
        self, 
        messages: List[BaseMessage], 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseMessage:
        """
        Invoke LLM with COT reasoning if enabled
        """
        if not self.enable_cot:
            # Direct pass-through if COT is disabled
            return await self.llm.ainvoke(messages, **kwargs)
        
        context = context or {}
        
        # Extract the user's task from messages
        user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        task = user_messages[-1].content if user_messages else ""
        
        # Create COT-enhanced messages
        cot_messages = messages.copy()
        
        # Add COT reasoning prompt to the last user message
        if user_messages:
            cot_prompt = self._create_cot_prompt(task, context)
            enhanced_content = f"{task}\n\n{cot_prompt}"
            
            # Replace the last user message with COT-enhanced version
            for i in range(len(cot_messages) - 1, -1, -1):
                if isinstance(cot_messages[i], HumanMessage):
                    cot_messages[i] = HumanMessage(content=enhanced_content)
                    break
        
        # Add instruction for structured output
        cot_messages.append(SystemMessage(content="""
After your reasoning, clearly mark your final response with "Final response:" 
This response will be spoken to the guest, so make it natural and conversational."""))
        
        # Invoke LLM with COT-enhanced prompt
        cot_response = await self.llm.ainvoke(cot_messages, **kwargs)
        
        # Extract and process the response
        extracted = self._extract_reasoning_and_response(cot_response.content)
        
        # Log reasoning for debugging
        if extracted["reasoning"]:
            logger.debug(f"COT Reasoning: {extracted['reasoning']}")
        
        # Return cleaned response
        return AIMessage(content=extracted["response"])
    
    def invoke_with_cot(
        self, 
        messages: List[BaseMessage], 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseMessage:
        """
        Synchronous version of COT invoke
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.ainvoke_with_cot(messages, context, **kwargs)
        )


def create_cot_enhanced_llm(
    model_type: str = None,
    enable_cot: bool = None
) -> COTWrapper:
    """
    Factory function to create COT-enhanced LLM
    
    Args:
        model_type: "groq" or "openai" (defaults to env var)
        enable_cot: Whether to enable COT (defaults to env var)
    
    Returns:
        COTWrapper instance
    """
    model_type = model_type or os.getenv("LLM_MODEL_TYPE", "groq")
    
    if model_type == "openai":
        base_llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4"),
            temperature=0.1,
            max_tokens=1000
        )
    else:
        base_llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "mixtral-8x7b-32768"),
            temperature=0.1,
            max_tokens=1000
        )
    
    return COTWrapper(base_llm, enable_cot)


# Example integration in your existing agent
def integrate_cot_in_agent_nodes(llm, tools):
    """
    Modify existing agent nodes to use COT wrapper
    """
    # Wrap the LLM with COT capabilities
    cot_llm = COTWrapper(llm)
    
    def menu_retrieval_agent_with_cot(state):
        """Menu agent with COT reasoning"""
        messages = state["messages"]
        context = {
            "room_number": state.get("room_number"),
            "order_summary": state.get("order_summary"),
            "conversation_phase": "menu_browsing"
        }
        
        # Use COT-enhanced invoke
        if cot_llm.enable_cot:
            response = cot_llm.invoke_with_cot(messages, context)
        else:
            # Fallback to original behavior
            response = llm.bind_tools([tool for tool in tools if tool.name == "retrieve_menu_info"]).invoke(messages)
        
        return {"messages": [response], "conversation_phase": "menu_browsing"}
    
    return menu_retrieval_agent_with_cot