# langgraph_test.py
import os
import json
from dotenv import load_dotenv
from langgraph_agent import get_concierge_agent
from typing import Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

# Ensure required API keys are set
required_keys = ["GROQ_API_KEY", "MISTRAL_API_KEY"]
for key in required_keys:
    if not os.getenv(key):
        raise ValueError(f"{key} is not set in the environment.")

def print_state_info(state: Dict[str, Any]):
    """Print relevant state information for debugging"""
    print("\n--- Current State ---")
    print(f"Room Number: {state.get('room_number', 'Not set')}")
    print(f"Order Summary: {json.dumps(state.get('order_summary', {}), indent=2)}")
    print(f"Conversation Phase: {state.get('conversation_phase', 'Unknown')}")
    print(f"Intent: {state.get('intent', 'Unknown')}")
    print(f"Validation Status: {state.get('validation_status', 'Unknown')}")
    print("----------------------")

def print_conversation_turn(turn_num: int, user_msg: str, agent_response: str):
    """Print a formatted conversation turn"""
    print(f"\n{'='*50}")
    print(f"TURN {turn_num}")
    print(f"{'='*50}")
    print(f"👤 User: {user_msg}")
    print(f"🤖 Agent: {agent_response}")

def run_test_scenarios():
    """Run predefined test scenarios to validate agent behavior"""
    
    print("🚀 Starting LangGraph Agent Test Scenarios...")
    print("=" * 60)
    
    try:
        agent = get_concierge_agent()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return

    # Test Scenario 1: Full conversation flow
    print("\n🧪 TEST SCENARIO 1: Complete Order Flow")
    print("-" * 40)
    
    state = None
    test_messages = [
        "Hello there!",
        "I'm in room 1234",
        "What's on the breakfast menu?",
        "I'd like to order pancakes and coffee",
        "Actually, add some eggs too",
        "Yes, please confirm my order"
    ]
    
    for i, message in enumerate(test_messages, 1):
        try:
            state = agent.process_message_sync(message, state)
            
            # Get the last AI message
            ai_messages = [msg for msg in state.get("messages", []) if hasattr(msg, 'content') and not isinstance(msg, type(state.get("messages", [{}])[0]))]
            last_response = ai_messages[-1].content if ai_messages else "No response"
            
            print_conversation_turn(i, message, last_response)
            print_state_info(state)
            
        except Exception as e:
            print(f"❌ Error in turn {i}: {e}")
            break
    
    print("\n" + "=" * 60)
    print("🏁 Test scenarios completed!")

def interactive_mode():
    """Interactive mode for manual testing"""
    print("\n🎮 Interactive Mode - Chat with the Agent")
    print("-" * 40)
    print("Type 'quit' to exit, 'state' to see current state, 'reset' to start over")
    
    try:
        agent = get_concierge_agent()
        print("✅ Agent ready for conversation")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return
    
    state = None
    turn_counter = 0
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() == 'quit':
                print("👋 Goodbye!")
                break
            elif user_input.lower() == 'state':
                if state:
                    print_state_info(state)
                else:
                    print("No conversation state yet")
                continue
            elif user_input.lower() == 'reset':
                state = None
                turn_counter = 0
                print("🔄 Conversation reset")
                continue
            elif not user_input:
                continue
            
            turn_counter += 1
            state = agent.process_message_sync(user_input, state)
            
            # Extract last AI response
            ai_messages = [msg for msg in state.get("messages", []) if hasattr(msg, 'content')]
            if ai_messages:
                last_ai_msg = ai_messages[-1]
                if hasattr(last_ai_msg, 'content'):
                    response = last_ai_msg.content
                else:
                    response = str(last_ai_msg)
            else:
                response = "No response generated"
            
            print(f"🤖 Agent: {response}")
            
            # Show state info after each turn
            print_state_info(state)
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user (Ctrl+C). Exiting gracefully.")
            break
        except Exception as e:
            print(f"❌ Error processing message: {e}")

def main():
    """Main CLI interface"""
    print("🏨 LangGraph Hotel Concierge Agent Tester")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Run automated test scenarios")
        print("2. Interactive mode (manual testing)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            run_test_scenarios()
        elif choice == '2':
            interactive_mode()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()