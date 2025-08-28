"""
Intent Training Data for Semantic Intent Classification
Provides focused training examples for the hotel concierge voice AI's core capabilities.
"""

from typing import Dict, List

# Consolidated and focused intent training data
INTENT_EXAMPLES = {
    "menu_inquiry": [
        # General menu questions
        "show me the menu",
        "what food do you have",
        "what are my options",
        "tell me about your menu",
        # Specific category inquiries
        "what vegetarian options do you have",
        "show me pizza menu",
        "what salads are available",
        "do you have any pasta dishes",
        "what's on your breakfast menu",
        "tell me about your appetizers",
        "what kind of sandwiches do you serve",
        "show me dessert options",
        "what beverages do you offer",
        # Ingredient and dietary questions (handled by RAG)
        "do you have gluten-free items",
        "what's in the veggie supreme pizza",
        "does the classic club sandwich have bacon",
        "is the lentil soup vegan",
        "are there nuts in the green smoothie",
        # Price questions (handled by RAG)
        "how much does the pizza cost",
        "what's the price of the burger",
        "how expensive is the wine",
        # Availability questions (handled by RAG)
        "is the grilled salmon available now",
        "is room service still open",
        "what time do you stop serving dinner"
    ],
    
    "order_placement": [
        # Direct ordering of specific items
        "I want to order a margherita pizza",
        "add a classic lemonade to my order",
        "get me the philly cheesesteak",
        "I'll have the quinoa salad",
        "I want the fish and chips",
        "order me an iced mocha",
        "I'll take the spicy tofu banh mi",
        # Initiating an order without a specific item
        "can I order room service",
        "I'd like to place an order",
        "I want to order some food",
        "can you bring me breakfast",
        "I'd like to order dinner",
        # Ordering with quantity
        "I'll have two classic club sandwiches",
        "get me three orders of the chili cheese dog",
        # Ordering with simple modifications
        "I want a margherita pizza but make it extra spicy",
        "can I get the classic club with no mayonnaise",
        "add a coffee to my order, no sugar please"
    ],

    "order_modification": [
        # Removing items
        "actually, can you remove the pizza",
        "take the salad off my order",
        "I don't want the lemonade anymore",
        "cancel the sandwich",
        # Changing quantities
        "can I get two of those instead of one",
        "change that to three burgers",
        "I only need one order of fries",
        # Swapping items
        "instead of the pepperoni pizza, I'd like the margherita",
        "can I swap the iced mocha for a green smoothie",
        "I changed my mind, I want the veggie dog not the classic",
        # General modification requests
        "I need to change my order",
        "can I make a modification to my order",
        "I want to update my cart"
    ],

    "order_confirmation": [
        # Explicit confirmation
        "yes, that's correct",
        "everything looks right, please place the order",
        "confirm my order",
        "yes, go ahead and place it",
        "that's all, finalize the order",
        "checkout now",
        "yes, I'm ready to order",
        "looks good, send it",
        "that's correct, thank you"
    ],
    
    "general_assistance": [
        # General help
        "can you help me",
        "I need some assistance",
        # Recommendations
        "what do you recommend",
        "I'm not sure what to order",
        "can you suggest something",
        "what's popular here",
        "what's the chef's special",
        # Agent capabilities
        "what can you do",
        "what services do you offer",
        "tell me what you can help with"
    ]
}

# Corresponding intent descriptions
INTENT_DESCRIPTIONS = {
    "menu_inquiry": "User wants to know about menu items, prices, ingredients, or availability.",
    "order_placement": "User wants to place a new order or add items to their current order.",
    "order_modification": "User wants to change, remove, or update items in their current order.",
    "order_confirmation": "User is confirming their order is correct and ready to be placed.",
    "general_assistance": "User needs help, advice, recommendations, or is asking about the AI's capabilities."
}

# Simplified confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high_confidence": 0.80,
    "medium_confidence": 0.65,
    "low_confidence": 0.50
}

# Simplified priority mapping
INTENT_PRIORITIES = {
    "order_confirmation": 5,
    "order_modification": 4,
    "order_placement": 3,
    "menu_inquiry": 2,
    "general_assistance": 1
}

def get_intent_examples() -> Dict[str, List[str]]:
    """Get intent training examples"""
    return INTENT_EXAMPLES

def get_intent_descriptions() -> Dict[str, str]:
    """Get intent descriptions for semantic understanding"""
    return INTENT_DESCRIPTIONS

def get_confidence_thresholds() -> Dict[str, float]:
    """Get confidence thresholds for classification"""
    return CONFIDENCE_THRESHOLDS

def get_intent_priorities() -> Dict[str, int]:
    """Get intent priorities for routing"""
    return INTENT_PRIORITIES

def get_all_intents() -> List[str]:
    """Get list of all available intents"""
    return list(INTENT_EXAMPLES.keys())

def validate_intent_data() -> bool:
    """Validate that all intent data is consistent"""
    intents_in_examples = set(INTENT_EXAMPLES.keys())
    intents_in_descriptions = set(INTENT_DESCRIPTIONS.keys())
    intents_in_priorities = set(INTENT_PRIORITIES.keys())
    
    if intents_in_examples ==intents_in_descriptions == intents_in_priorities:
        return True
    else:
        missing_in_descriptions = intents_in_examples - intents_in_descriptions
        missing_in_priorities = intents_in_examples - intents_in_priorities
        
        if missing_in_descriptions:
            print(f"Missing descriptions for intents: {missing_in_descriptions}")
        if missing_in_priorities:
            print(f"Missing priorities for intents: {missing_in_priorities}")
        
        return False

# Validate data on import
if __name__ == "__main__":
    if validate_intent_data():
        print("Intent training data is valid and consistent.")
        print(f"Total intents: {len(get_all_intents())}")
        total_examples = sum(len(examples) for examples in INTENT_EXAMPLES.values())
        print(f"Total training examples: {total_examples}")
    else:
        print("Intent training data validation failed.")
