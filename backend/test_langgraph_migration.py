"""
Test script for LangGraph Hotel Concierge System
Tests RAG pipeline and agent functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from loguru import logger
import sys

# Add the backend directory to path
sys.path.append(os.path.dirname(__file__))

from rag_pipeline import get_rag_pipeline
from langgraph_agent import get_concierge_agent

load_dotenv()

# Test queries for menu system
TEST_QUERIES = [
    "What pizzas do you have?",
    "Are there any vegetarian options?",
    "What's the price of the Margherita pizza?",
    "Do you have any beverages?",
    "What sandwiches are available?",
    "How many calories are in the BBQ Chicken pizza?",
    "What hotdogs do you serve?",
    "Show me non-vegetarian items",
    "What's the most expensive item?",
    "Do you have gluten-free options?"
]

async def test_rag_pipeline():
    """Test the RAG pipeline functionality"""
    logger.info("Testing RAG Pipeline...")
    
    try:
        # Get RAG pipeline
        rag = get_rag_pipeline()
        
        # Test each query
        for i, query in enumerate(TEST_QUERIES, 1):
            logger.info(f"\n--- Test Query {i}: {query} ---")
            
            # Get context from RAG
            context = rag.get_context_for_query(query, k=3)
            
            print(f"Query: {query}")
            print(f"RAG Response:\n{context}")
            print("-" * 50)
            
        logger.info("RAG Pipeline tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"RAG Pipeline test failed: {e}")
        return False

async def test_langgraph_agent():
    """Test the LangGraph agent functionality"""
    logger.info("Testing LangGraph Agent...")
    
    try:
        # Get agent
        agent = get_concierge_agent()
        
        # Test conversation flow
        conversation_state = None
        
        # Test messages simulating a real conversation
        test_messages = [
            "Hi, I'd like to order some food",
            "My room number is 1205",
            "What pizzas do you have?",
            "I'd like to order a Margherita pizza",
            "Also add a Classic Lemonade",
            "What's my current order?",
            "Yes, please place the order"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info(f"\n--- Agent Test {i}: {message} ---")
            
            # Process message
            result = await agent.process_message(message, conversation_state)
            conversation_state = result
            
            # Get response
            if result.get("messages"):
                last_message = result["messages"][-1]
                response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                response = "No response"
            
            print(f"User: {message}")
            print(f"Agent: {response}")
            print(f"Room Number: {result.get('room_number')}")
            print(f"Order Summary: {result.get('order_summary')}")
            print("-" * 50)
            
        logger.info("LangGraph Agent tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"LangGraph Agent test failed: {e}")
        return False

async def test_integration():
    """Test full integration"""
    logger.info("Testing Full Integration...")
    
    try:
        # Test both components
        rag_success = await test_rag_pipeline()
        agent_success = await test_langgraph_agent()
        
        if rag_success and agent_success:
            logger.info("🎉 ALL TESTS PASSED! Integration successful!")
            return True
        else:
            logger.error("❌ Some tests failed")
            return False
            
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    logger.info("Checking environment variables...")
    
    required_vars = [
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "API_BASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Please set these variables in your .env file:")
        for var in missing_vars:
            logger.info(f"  {var}=your_api_key_here")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

async def main():
    """Main test function"""
    logger.info("🚀 Starting Hotel Concierge LangGraph Tests")
    
    # Check environment first
    if not check_environment():
        return
    
    # Run integration tests
    success = await test_integration()
    
    if success:
        logger.info("🎉 Migration to LangGraph completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Install dependencies: pip install -r requirements-langgraph.txt")
        logger.info("2. Run the new service: python hotel_concierge_langgraph.py")
        logger.info("3. Test with voice interface")
    else:
        logger.error("❌ Tests failed. Please check the logs and fix issues.")

if __name__ == "__main__":
    asyncio.run(main())