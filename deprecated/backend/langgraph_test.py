# langgraph_test.py
import os
import json
from dotenv import load_dotenv
from main_langgraph_agent import get_concierge_agent
from typing import Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

# Ensure required API keys are set
required_keys = ["GROQ_API_KEY", "MISTRAL_API_KEY"]
for key in required_keys:
    if not os.getenv(key):
        raise ValueError(f"{key} is not set in the environment.")

def toggle_cot(enable: bool = True, mode: str = "adaptive"):
    """Toggle COT reasoning on/off with specified mode"""
    os.environ["ENABLE_COT"] = "true" if enable else "false"
    os.environ["COT_MODE"] = mode
    print(f"🧠 COT {'ENABLED' if enable else 'DISABLED'} - Mode: {mode}")
    return enable

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

def run_cot_test_scenarios():
    """Run COT-specific test scenarios to validate reasoning"""
    
    print("🧠 Starting COT Reasoning Test Scenarios...")
    print("=" * 60)
    
    # Test COT with different modes
    cot_modes = ["simple", "structured", "adaptive"]
    
    for mode in cot_modes:
        print(f"\n🧪 TEST SCENARIO: COT Mode - {mode.upper()}")
        print("-" * 50)
        
        # Enable COT with current mode
        toggle_cot(True, mode)
        
        try:
            agent = get_concierge_agent()
            print(f"✅ Agent initialized with COT mode: {mode}")
        except Exception as e:
            print(f"❌ Agent initialization failed: {e}")
            continue
        
        # COT-triggering test messages (complex queries that should activate reasoning)
        cot_test_messages = [
            "Hello, I'm in room 507",
            "Compare the vegetarian and vegan options on your menu and recommend the healthiest choice",
            "I want to order 3 different items but I'm confused about portions and allergies"
        ]
        
        state = None
        for i, message in enumerate(cot_test_messages, 1):
            try:
                print(f"\n📝 Query {i}: {message}")
                state = agent.process_message_sync(message, state)
                
                # Get the last AI message
                ai_messages = [msg for msg in state.get("messages", []) if hasattr(msg, 'content')]
                if ai_messages:
                    last_response = ai_messages[-1].content
                    print(f"🤖 Response: {last_response}")
                    
                    # Check if COT reasoning is visible in response
                    if '<think>' in last_response:
                        think_start = last_response.find('<think>')
                        think_end = last_response.find('</think>')
                        if think_start != -1 and think_end != -1:
                            reasoning = last_response[think_start+7:think_end].strip()
                            print(f"💭 COT Reasoning Found: {reasoning[:100]}..." if len(reasoning) > 100 else f"💭 COT Reasoning: {reasoning}")
                    else:
                        print("⚠️  No visible COT reasoning in response (check logs)")
                else:
                    print("❌ No response generated")
                    
            except Exception as e:
                print(f"❌ Error in COT test {i}: {e}")
                break
        
        print(f"\n✅ COT Mode {mode} testing completed")
        print("-" * 50)
        
        # Clear the singleton to test next mode
        import main_langgraph_agent
        main_langgraph_agent._agent = None

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

def interactive_cot_mode():
    """Interactive mode with COT configuration options"""
    print("\n🧠 Interactive COT Mode - Chat with COT-Enhanced Agent")
    print("-" * 50)
    print("Commands:")
    print("- 'quit' to exit")
    print("- 'state' to see current state")
    print("- 'reset' to start over")
    print("- 'cot on/off' to toggle COT")
    print("- 'cot mode simple/structured/adaptive' to change COT mode")
    print("- 'logs' to see recent COT reasoning logs")
    
    # Start with COT enabled in adaptive mode
    toggle_cot(True, "adaptive")
    
    try:
        agent = get_concierge_agent()
        print("✅ Agent ready for COT-enhanced conversation")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return
    
    state = None
    turn_counter = 0
    recent_cot_logs = []
    
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
                recent_cot_logs = []
                # Clear singleton to reinitialize with current COT settings
                import main_langgraph_agent
                main_langgraph_agent._agent = None
                agent = get_concierge_agent()
                print("🔄 Conversation reset with current COT settings")
                continue
            elif user_input.lower() == 'logs':
                if recent_cot_logs:
                    print("\n🧠 Recent COT Reasoning:")
                    for i, log in enumerate(recent_cot_logs[-5:], 1):
                        print(f"{i}. {log}")
                else:
                    print("No COT logs available")
                continue
            elif user_input.lower().startswith('cot '):
                cot_command = user_input[4:].strip().lower()
                if cot_command in ['on', 'off']:
                    enable_cot = cot_command == 'on'
                    current_mode = os.getenv("COT_MODE", "adaptive")
                    toggle_cot(enable_cot, current_mode)
                    # Reinitialize agent
                    import main_langgraph_agent
                    main_langgraph_agent._agent = None
                    agent = get_concierge_agent()
                    continue
                elif cot_command.startswith('mode '):
                    mode = cot_command[5:].strip()
                    if mode in ['simple', 'structured', 'adaptive']:
                        current_enable = os.getenv("ENABLE_COT", "false").lower() == "true"
                        toggle_cot(current_enable, mode)
                        # Reinitialize agent
                        import main_langgraph_agent
                        main_langgraph_agent._agent = None
                        agent = get_concierge_agent()
                        continue
                    else:
                        print("❌ Invalid COT mode. Use: simple, structured, or adaptive")
                        continue
            elif not user_input:
                continue
            
            turn_counter += 1
            
            # Process message and capture any COT reasoning
            print(f"\n🤔 Processing with COT {'ENABLED' if os.getenv('ENABLE_COT', 'false').lower() == 'true' else 'DISABLED'} ({os.getenv('COT_MODE', 'adaptive')} mode)...")
            
            state = agent.process_message_sync(user_input, state)
            
            # Extract last AI response
            ai_messages = [msg for msg in state.get("messages", []) if hasattr(msg, 'content')]
            if ai_messages:
                last_ai_msg = ai_messages[-1]
                if hasattr(last_ai_msg, 'content'):
                    response = last_ai_msg.content
                    
                    # Extract and display COT reasoning if present
                    if '<think>' in response:
                        think_start = response.find('<think>')
                        think_end = response.find('</think>')
                        if think_start != -1 and think_end != -1:
                            reasoning = response[think_start+7:think_end].strip()
                            clean_response = response[:think_start] + response[think_end+8:]
                            clean_response = clean_response.strip()
                            
                            print(f"\n💭 COT Reasoning:\n{reasoning}")
                            print(f"\n🤖 Agent: {clean_response}")
                            recent_cot_logs.append(f"Turn {turn_counter}: {reasoning[:100]}...")
                        else:
                            print(f"🤖 Agent: {response}")
                    else:
                        print(f"🤖 Agent: {response}")
                        if os.getenv('ENABLE_COT', 'false').lower() == 'true':
                            print("⚠️  COT enabled but no reasoning found (may not have triggered)")
                else:
                    response = str(last_ai_msg)
                    print(f"🤖 Agent: {response}")
            else:
                print("❌ No response generated")
            
            # Show simplified state info
            print(f"\n📊 Quick State: Room={state.get('room_number', 'None')}, Phase={state.get('conversation_phase', 'Unknown')}, Orders={len(state.get('order_summary', {}))}")
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user (Ctrl+C). Exiting gracefully.")
            break
        except Exception as e:
            print(f"❌ Error processing message: {e}")

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
        print("1. Run automated test scenarios (standard)")
        print("2. Interactive mode (manual testing)")
        print("3. COT Reasoning Tests (automated)")
        print("4. Interactive COT Mode (manual with COT controls)")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            # Disable COT for standard tests
            toggle_cot(False)
            # Clear singleton to reinitialize
            import main_langgraph_agent
            main_langgraph_agent._agent = None
            run_test_scenarios()
        elif choice == '2':
            # Disable COT for standard interactive mode
            toggle_cot(False)
            # Clear singleton to reinitialize
            import main_langgraph_agent
            main_langgraph_agent._agent = None
            interactive_mode()
        elif choice == '3':
            run_cot_test_scenarios()
        elif choice == '4':
            interactive_cot_mode()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()