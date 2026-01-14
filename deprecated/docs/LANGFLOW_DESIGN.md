# Converting Hotel Concierge System to LangFlow

## Overview

This document outlines how to convert the current hotel concierge system into LangFlow-compatible nodes. The current implementation uses pipecat_flows, which has a similar structure to what we want to achieve in LangFlow. The conversion will enable better visualization, modularity, and evaluation capabilities that align with your employer's requirements.

## Current Flow Structure

The current implementation has the following nodes in the `hotel_room_service_flow`:

1. **greeting** - Initial greeting and room number request
2. **request_room** - Waits for guest to provide room number
3. **validate_room** - Validates room number and gets guest info
4. **invalid_room** - Handles invalid room numbers
5. **welcome_guest** - Welcomes guest and shows categories
6. **category_selection** - Allows guest to select a category
7. **category_not_found** - Handles unknown categories
8. **show_items** - Displays items in selected category
9. **item_not_found** - Handles unknown items
10. **item_added** - Confirms item added to order
11. **continue_ordering** - Asks if guest wants to add more items
12. **request_special** - Requests special requests and delivery notes
13. **confirm_order** - Shows order summary and asks for confirmation
14. **empty_order** - Handles empty orders
15. **order_failed** - Handles order placement failures
16. **order_complete** - Confirms successful order placement
17. **goodbye** - Ends the conversation

## LangFlow Node Mapping

### 1. Greeting Node
- **Type**: Custom Component
- **Inputs**: None
- **Outputs**: room_number_request (trigger)
- **Functionality**: 
  - Greets guest: "Good [morning/afternoon/evening], this is room service at Grand Plaza Hotel."
  - Requests room number: "May I have your room number, please?"

### 2. Room Number Validation Node
- **Type**: Custom Component
- **Inputs**: room_number (string)
- **Outputs**: valid_room (boolean), guest_info (object)
- **Functionality**:
  - Calls API to validate room number
  - Returns guest information if valid
  - Triggers invalid_room flow if not valid

### 3. Category Selection Node
- **Type**: Custom Component
- **Inputs**: guest_info (object)
- **Outputs**: selected_category (string)
- **Functionality**:
  - Shows available categories
  - Waits for guest to select a category

### 4. Menu Display Node
- **Type**: Custom Component
- **Inputs**: selected_category (string)
- **Outputs**: selected_item (object)
- **Functionality**:
  - Fetches menu items for category
  - Displays items with prices
  - Waits for guest to select an item

### 5. Order Management Node
- **Type**: Custom Component
- **Inputs**: selected_item (object), quantity (int), special_notes (string)
- **Outputs**: order_updated (boolean), order_summary (string)
- **Functionality**:
  - Adds items to order
  - Manages order state
  - Provides order summaries

### 6. Special Requests Node
- **Type**: Custom Component
- **Inputs**: None
- **Outputs**: special_requests (string), delivery_notes (string)
- **Functionality**:
  - Asks for special requests
  - Asks for delivery instructions

### 7. Order Confirmation Node
- **Type**: Custom Component
- **Inputs**: order_summary (string)
- **Outputs**: confirmation (boolean)
- **Functionality**:
  - Shows order summary
  - Requests confirmation

### 8. Order Placement Node
- **Type**: Custom Component
- **Inputs**: confirmed_order (boolean), guest_info (object), order_items (array)
- **Outputs**: order_success (boolean), order_id (string)
- **Functionality**:
  - Places order via API
  - Returns success status and order ID

### 9. Completion Node
- **Type**: Custom Component
- **Inputs**: order_success (boolean), order_id (string)
- **Outputs**: None
- **Functionality**:
  - Confirms order placement
  - Provides order details
  - Ends conversation

## Enhanced Features for Employer Requirements

To meet your employer's requirements, we'll enhance the LangFlow implementation with these features:

### RAG Integration
- **Vector Database Component**: For storing and retrieving menu item embeddings
- **Document Processing Component**: For parsing PDF menus and creating embeddings
- **Hybrid Search Component**: Combining keyword and semantic search for menu items

### Evaluation and Logging
- **Conversation Logger**: For storing transcripts and conversation metadata
- **Evaluation Metrics**: For calculating LLM performance metrics
- **Intent Classification**: For categorizing user intents with confidence scores

### Advanced Conversation Features
- **Emotional Intelligence Component**: For adjusting response tone and timing
- **Chain-of-Thought Reasoning**: For complex multi-step order processing
- **Dynamic Response Timing**: For natural conversation pauses

## Implementation Approach

### Step 1: Create Custom Components

For each node in the flow, we need to create a corresponding custom component in LangFlow:

1. **GuestValidator** - Validates room numbers against the database
2. **CategorySelector** - Manages menu categories
3. **MenuItemDisplayer** - Shows menu items for a category (with RAG)
4. **OrderManager** - Manages the order state
5. **OrderPlacer** - Places orders via API
6. **RAGRetriever** - Retrieves relevant menu items using vector similarity
7. **ConversationLogger** - Logs conversation turns for evaluation
8. **EvaluationMetrics** - Calculates performance metrics

### Step 2: Design the Flow Graph

The flow graph in LangFlow would look like:

```
[Greeting] -> [Room Validation] -> [Welcome & Categories] -> [Category Selection]
                                          |                    |
                                          v                    v
                                  [Invalid Room]      [Menu Display] -> [Add to Order]
                                          |                    |              |
                                          |                    v              v
                                          |           [Category Selection] <- [Continue Ordering]
                                          |                    |
                                          |                    v
                                          |          [Special Requests] -> [Order Confirmation]
                                          |                    |                  |
                                          |                    v                  v
                                          |         [Order Placement] <- [Confirmation Handler]
                                          |                    |
                                          v                    v
                                  [Error Handler]    [Completion & Goodbye]
```

With RAG integration, the Menu Display component would be enhanced:

```
[Category Selection] -> [RAG Retriever] -> [Menu Display]
                              |
                              v
                    [Similar Item Suggestions]
```

### Step 3: Data Flow Between Nodes

Each node will pass data through LangFlow's state management:

1. **Context Variables**:
   - guest_info: {id, name, room_number}
   - current_order: {items: [], special_requests, delivery_notes}
   - current_category: string
   - order_summary: string
   - conversation_history: [{role, content}]
   - evaluation_metrics: {intent_accuracy, response_relevance, ...}

2. **State Transitions**:
   - Each node updates the context with its outputs
   - Downstream nodes consume these context variables
   - Evaluation components collect metrics throughout the conversation

### Step 4: RAG Implementation Details

1. **Document Processing**:
   - Parse PDF menu documents
   - Extract menu items with descriptions and prices
   - Create structured data for embedding

2. **Embedding Creation**:
   - Use sentence transformers or OpenAI embeddings
   - Create embeddings for menu item names and descriptions
   - Store embeddings in vector database

3. **Retrieval Process**:
   - Convert user queries to embeddings
   - Search vector database for similar items
   - Apply hybrid search (keyword + semantic)
   - Rank results by relevance

## Advantages of LangFlow Implementation

1. **Visual Workflow**: Easy to understand and modify the conversation flow
2. **Modularity**: Each component can be tested and updated independently
3. **Reusability**: Components can be reused across different flows
4. **Observability**: Built-in logging and monitoring capabilities
5. **Collaboration**: Team members can work on different parts of the flow
6. **Evaluation**: Comprehensive logging for performance analysis
7. **RAG Integration**: Seamless integration of retrieval-augmented generation
8. **Flexibility**: Easy to add new features and conversation paths

## Next Steps

1. Set up LangFlow environment with Docker
2. Create custom components for each node
3. Design the flow graph in LangFlow UI
4. Implement RAG components with vector database
5. Add logging and evaluation capabilities
6. Test with different conversation paths
7. Integrate with existing API endpoints
8. Create evaluation dashboard for metrics tracking