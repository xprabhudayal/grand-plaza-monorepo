# LangFlow Implementation Plan for Hotel Concierge System

## Overview

This document provides a detailed plan for converting the current hotel concierge system to LangFlow-compatible components. The goal is to create a visual, modular, and maintainable workflow that aligns with the employer's requirements for RAG, vector databases, and evaluation capabilities.

## Phase 1: Environment Setup and Core Components

### 1.1 LangFlow Environment Setup
- Install LangFlow: `pip install langflow`
- Set up Docker environment for LangFlow server
- Configure environment variables for API connections
- Set up development environment with debugging tools

### 1.2 Custom Component Development Framework
- Create a base class for custom LangFlow components
- Implement error handling and logging framework
- Set up testing infrastructure for components
- Create component documentation template

## Phase 2: Core Service Components

### 2.1 Guest Management Component
**File**: `components/guest_manager.py`

```python
from langflow import CustomComponent
from typing import Optional, Dict, Any
import aiohttp
import os

class GuestManager(CustomComponent):
    display_name = "Guest Manager"
    description = "Manages guest validation and information retrieval"
    
    def build_config(self):
        return {
            "room_number": {"display_name": "Room Number", "type": "str"},
            "api_base_url": {"display_name": "API Base URL", "type": "str", "default": "http://localhost:8000"},
        }
    
    async def validate_guest(self, room_number: str, api_base_url: str = "http://localhost:8000") -> Optional[Dict[str, Any]]:
        """Validate room number and get guest information"""
        api_endpoint = f"{api_base_url}/api/v1/guests/room/{room_number}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_endpoint) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"Error validating room number: {str(e)}")
            return None
```

### 2.2 Menu Management Component
**File**: `components/menu_manager.py`

```python
from langflow import CustomComponent
from typing import List, Dict, Any, Optional
import aiohttp
import os

class MenuManager(CustomComponent):
    display_name = "Menu Manager"
    description = "Manages menu categories and items retrieval"
    
    def build_config(self):
        return {
            "api_base_url": {"display_name": "API Base URL", "type": "str", "default": "http://localhost:8000"},
        }
    
    async def get_categories(self, api_base_url: str = "http://localhost:8000") -> List[Dict[str, Any]]:
        """Get all active categories"""
        api_endpoint = f"{api_base_url}/api/v1/categories/?is_active=true"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_endpoint) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return []
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return []
    
    async def get_menu_items(self, api_base_url: str = "http://localhost:8000") -> List[Dict[str, Any]]:
        """Get all available menu items"""
        api_endpoint = f"{api_base_url}/api/v1/menu-items/?is_available=true"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_endpoint) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return []
        except Exception as e:
            print(f"Error fetching menu items: {str(e)}")
            return []
    
    def find_menu_item_by_name(self, item_name: str, menu_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find a menu item by name with fuzzy matching"""
        item_name_lower = item_name.lower()
        
        # Try exact match first
        for item in menu_items:
            if item["name"].lower() == item_name_lower:
                return item
        
        # Try partial match
        for item in menu_items:
            if item_name_lower in item["name"].lower() or item["name"].lower() in item_name_lower:
                return item
        
        # Try word-based matching
        item_words = set(item_name_lower.split())
        for item in menu_items:
            menu_words = set(item["name"].lower().split())
            if len(item_words.intersection(menu_words)) >= len(item_words) * 0.7:  # 70% word match
                return item
        
        return None
```

### 2.3 Order Management Component
**File**: `components/order_manager.py`

```python
from langflow import CustomComponent
from typing import List, Dict, Any, Optional
import aiohttp
import os

class OrderManagerComponent(CustomComponent):
    display_name = "Order Manager"
    description = "Manages order creation and state"
    
    def build_config(self):
        return {
            "guest_id": {"display_name": "Guest ID", "type": "str"},
            "order_items": {"display_name": "Order Items", "type": "list"},
            "special_requests": {"display_name": "Special Requests", "type": "str", "optional": True},
            "delivery_notes": {"display_name": "Delivery Notes", "type": "str", "optional": True},
            "api_base_url": {"display_name": "API Base URL", "type": "str", "default": "http://localhost:8000"},
        }
    
    async def create_order(self, 
                          guest_id: str, 
                          order_items: List[Dict[str, Any]], 
                          special_requests: Optional[str] = None,
                          delivery_notes: Optional[str] = None,
                          api_base_url: str = "http://localhost:8000") -> Optional[Dict[str, Any]]:
        """Create an order via API"""
        api_endpoint = f"{api_base_url}/api/v1/orders/"
        
        # Format order items for API
        formatted_items = []
        for item in order_items:
            formatted_items.append({
                "menu_item_id": item["menu_item_id"],
                "quantity": item["quantity"],
                "special_notes": item.get("special_notes")
            })
        
        order_data = {
            "guest_id": guest_id,
            "order_items": formatted_items
        }
        
        if special_requests:
            order_data["special_requests"] = special_requests
        
        if delivery_notes:
            order_data["delivery_notes"] = delivery_notes
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_endpoint, json=order_data) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        error_content = await response.text()
                        print(f"Failed to create order: {response.status}, {error_content}")
                        return None
        except Exception as e:
            print(f"Error creating order via API: {str(e)}")
            return None
```

## Phase 3: Conversation Flow Components

### 3.1 Greeting Component
**File**: `components/greeting_component.py`

```python
from langflow import CustomComponent
from datetime import datetime

class GreetingComponent(CustomComponent):
    display_name = "Greeting Component"
    description = "Provides time-appropriate greeting"
    
    def build_config(self):
        return {
            "guest_name": {"display_name": "Guest Name", "type": "str", "optional": True},
        }
    
    def get_greeting(self, guest_name: str = None) -> str:
        """Generate time-appropriate greeting"""
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_greeting = "Good morning"
        elif current_hour < 18:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
        
        if guest_name:
            return f"{time_greeting}, {guest_name}. This is room service at Grand Plaza Hotel."
        else:
            return f"{time_greeting}, this is room service at Grand Plaza Hotel."
```

### 3.2 Text Processing Utilities
**File**: `components/text_utils.py`

```python
from langflow import CustomComponent
from typing import Union
import re

class TextUtils(CustomComponent):
    display_name = "Text Utilities"
    description = "Utility functions for text processing"
    
    def build_config(self):
        return {
            "text": {"display_name": "Text", "type": "str"},
        }
    
    def convert_text_to_number(self, text: Union[str, int]) -> int:
        """Convert text numbers to integers (e.g., 'two' -> 2)"""
        if isinstance(text, int):
            return text
        
        if isinstance(text, str) and text.isdigit():
            return int(text)
        
        text_to_num = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
            'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90, 'hundred': 100
        }
        
        if not isinstance(text, str):
            return 1
        
        text = text.lower().strip()
        
        if text in text_to_num:
            return text_to_num[text]
        
        # Handle compound numbers
        if '-' in text:
            parts = text.split('-')
            if len(parts) == 2 and parts[0] in text_to_num and parts[1] in text_to_num:
                return text_to_num[parts[0]] + text_to_num[parts[1]]
        
        # Handle "a" or "an" as 1
        if text in ['a', 'an']:
            return 1
        
        # Try to extract numbers from text
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        
        return 1
```

## Phase 4: RAG Integration Components

### 4.1 Vector Database Component
**File**: `components/vector_db_component.py`

```python
from langflow import CustomComponent
from typing import List, Dict, Any
import numpy as np
# Import your chosen vector database library (e.g., pinecone, chroma, weaviate)
# For now, we'll create a placeholder

class VectorDBComponent(CustomComponent):
    display_name = "Vector Database Component"
    description = "Manages vector database operations for RAG"
    
    def build_config(self):
        return {
            "query_text": {"display_name": "Query Text", "type": "str"},
            "top_k": {"display_name": "Top K Results", "type": "int", "default": 5},
        }
    
    def initialize_vector_db(self):
        """Initialize connection to vector database"""
        # Implementation depends on chosen vector database
        # Example with Pinecone:
        # import pinecone
        # pinecone.init(api_key="YOUR_API_KEY", environment="YOUR_ENVIRONMENT")
        # index = pinecone.Index("hotel-menu-items")
        pass
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for texts"""
        # Implementation depends on chosen embedding model
        # Example with OpenAI:
        # import openai
        # response = openai.Embedding.create(input=texts, model="text-embedding-ada-002")
        # return [item['embedding'] for item in response['data']]
        pass
    
    def search_similar_items(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar menu items using vector similarity"""
        # 1. Create embedding for query text
        # 2. Search vector database for similar embeddings
        # 3. Return top_k results with metadata
        pass
```

### 4.2 Document Processing Component
**File**: `components/document_processor.py`

```python
from langflow import CustomComponent
from typing import List, Dict, Any
import PyPDF2
# Add other document processing libraries as needed

class DocumentProcessor(CustomComponent):
    display_name = "Document Processor"
    description = "Processes PDF menus and extracts menu items for vector database"
    
    def build_config(self):
        return {
            "pdf_path": {"display_name": "PDF Path", "type": "str"},
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF menu"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
        return text
    
    def parse_menu_items(self, text: str) -> List[Dict[str, Any]]:
        """Parse menu items from extracted text"""
        # This would use NLP techniques to identify menu items, prices, descriptions
        # For now, returning a placeholder structure
        menu_items = []
        # Implementation would depend on the format of your PDFs
        return menu_items
```

## Phase 5: Evaluation and Logging Components

### 5.1 Conversation Logger
**File**: `components/conversation_logger.py`

```python
from langflow import CustomComponent
from typing import Dict, Any
import json
from datetime import datetime

class ConversationLogger(CustomComponent):
    display_name = "Conversation Logger"
    description = "Logs conversation transcripts and metadata for evaluation"
    
    def build_config(self):
        return {
            "session_id": {"display_name": "Session ID", "type": "str"},
            "log_data": {"display_name": "Log Data", "type": "dict"},
        }
    
    def log_conversation_turn(self, 
                             session_id: str, 
                             user_input: str, 
                             assistant_response: str,
                             intent: str = None,
                             confidence: float = None) -> bool:
        """Log a single conversation turn"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_input": user_input,
            "assistant_response": assistant_response,
            "intent": intent,
            "confidence": confidence
        }
        
        # In a real implementation, you would save this to a database
        # For now, we'll just print it
        print(f"Conversation Log: {json.dumps(log_entry, indent=2)}")
        return True
    
    def log_order_process(self, 
                         session_id: str,
                         order_data: Dict[str, Any],
                         success: bool,
                         error_message: str = None) -> bool:
        """Log order processing results"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "event_type": "order_process",
            "order_data": order_data,
            "success": success,
            "error_message": error_message
        }
        
        print(f"Order Process Log: {json.dumps(log_entry, indent=2)}")
        return True
```

### 5.2 Evaluation Metrics Component
**File**: `components/evaluation_metrics.py`

```python
from langflow import CustomComponent
from typing import Dict, Any, List
import numpy as np

class EvaluationMetrics(CustomComponent):
    display_name = "Evaluation Metrics"
    description = "Calculates evaluation metrics for LLM performance"
    
    def build_config(self):
        return {
            "predicted": {"display_name": "Predicted Values", "type": "list"},
            "actual": {"display_name": "Actual Values", "type": "list"},
        }
    
    def calculate_intent_accuracy(self, predicted_intents: List[str], actual_intents: List[str]) -> float:
        """Calculate accuracy of intent classification"""
        if len(predicted_intents) != len(actual_intents):
            raise ValueError("Predicted and actual lists must have the same length")
        
        correct = sum(1 for p, a in zip(predicted_intents, actual_intents) if p == a)
        return correct / len(predicted_intents)
    
    def calculate_slot_filling_metrics(self, 
                                     predicted_slots: List[Dict[str, Any]], 
                                     actual_slots: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate precision, recall, and F1 for slot filling"""
        # Implementation would depend on your slot filling evaluation needs
        pass
    
    def calculate_response_relevance(self, 
                                   user_query: str, 
                                   assistant_response: str) -> float:
        """Calculate relevance of response to user query"""
        # This could use embedding similarity or other techniques
        pass
```

## Phase 6: Advanced Features for Employer Requirements

### 6.1 Intent Classification Component
**File**: `components/intent_classifier.py`

```python
from langflow import CustomComponent
from typing import Dict, Any, Tuple

class IntentClassifier(CustomComponent):
    display_name = "Intent Classifier"
    description = "Classifies user intents with confidence scores"
    
    def build_config(self):
        return {
            "user_input": {"display_name": "User Input", "type": "str"},
        }
    
    def classify_intent(self, user_input: str) -> Tuple[str, float]:
        """Classify user intent and return confidence score"""
        # This would use a trained intent classification model
        # For now, returning placeholder values
        intent = "order_food"
        confidence = 0.95
        return intent, confidence
```

### 6.2 Emotional Intelligence Component
**File**: `components/emotional_intelligence.py`

```python
from langflow import CustomComponent
from typing import Dict, Any

class EmotionalIntelligence(CustomComponent):
    display_name = "Emotional Intelligence"
    description = "Adds emotional intelligence to responses"
    
    def build_config(self):
        return {
            "user_input": {"display_name": "User Input", "type": "str"},
            "assistant_response": {"display_name": "Assistant Response", "type": "str"},
        }
    
    def adjust_response_emotionally(self, user_input: str, assistant_response: str) -> str:
        """Adjust response based on emotional analysis of user input"""
        # This would use sentiment analysis and emotional response generation
        # For now, returning the original response
        return assistant_response
```

### 6.3 Chain-of-Thought Reasoning Component
**File**: `components/cot_reasoning.py`

```python
from langflow import CustomComponent
from typing import List, Dict, Any

class ChainOfThoughtReasoning(CustomComponent):
    display_name = "Chain-of-Thought Reasoning"
    description = "Implements chain-of-thought reasoning for complex tasks"
    
    def build_config(self):
        return {
            "task_description": {"display_name": "Task Description", "type": "str"},
        }
    
    def reason_through_task(self, task_description: str) -> List[str]:
        """Generate reasoning steps for a complex task"""
        # This would implement chain-of-thought prompting
        # For now, returning placeholder reasoning steps
        return [
            "Step 1: Understand the user request",
            "Step 2: Identify required information",
            "Step 3: Retrieve relevant data",
            "Step 4: Process and validate information",
            "Step 5: Formulate response"
        ]
```

## Phase 7: Flow Design in LangFlow UI

### 7.1 Main Conversation Flow

The main flow in LangFlow would consist of these connected components:

1. **Start Node** - Initiates the conversation
2. **Greeting Component** - Provides time-appropriate greeting
3. **Room Number Request** - Asks for and captures room number
4. **Guest Manager** - Validates room number and retrieves guest info
5. **Category Display** - Shows menu categories
6. **Category Selection** - Captures guest's category choice
7. **RAG Retriever** - Retrieves relevant menu items using vector search
8. **Menu Item Display** - Shows items in selected category (using RAG)
9. **Item Selection** - Captures guest's item choice
10. **Quantity Request** - Asks for quantity
11. **Special Notes Request** - Asks for special notes
12. **Order Update** - Adds item to order
13. **Continue Ordering** - Asks if guest wants more items
14. **Special Requests** - Asks for order-level special requests
15. **Delivery Instructions** - Asks for delivery notes
16. **Order Summary** - Shows complete order with chain-of-thought reasoning
17. **Confirmation Request** - Asks for order confirmation
18. **Order Placement** - Places order via API
19. **Completion Message** - Confirms order and provides details
20. **End Node** - Ends conversation

### 7.2 Conditional Paths

The flow would include these conditional paths:

1. **Invalid Room Number** - Loops back to room number request
2. **Unknown Category** - Shows available categories again
3. **Unknown Menu Item** - Uses RAG to find similar items
4. **Order Modification** - Allows guest to modify order
5. **Order Cancellation** - Cancels order and restarts
6. **System Error** - Handles API failures gracefully
7. **Complex Request** - Uses chain-of-thought reasoning for complex queries

### 7.3 Evaluation and Logging Integration

Each component will integrate with the evaluation and logging framework:

1. **Intent Classification** - Logs classified intents with confidence scores
2. **Response Generation** - Logs generated responses for relevance analysis
3. **Order Processing** - Logs order creation success/failure
4. **Conversation Flow** - Logs state transitions and decision points

## Phase 8: Integration with Existing System

### 8.1 API Integration
- All custom components will use the existing FastAPI endpoints
- No changes needed to the backend API
- Components will be drop-in replacements for current functions

### 8.2 Data Persistence
- Continue using SQLite database for guest, menu, and order data
- Add new tables for conversation logs and evaluation metrics
- Vector database for RAG implementation
- Create database migration scripts for new tables

### 8.3 Voice Integration
- Continue using pipecat for voice processing
- LangFlow handles the conversation logic
- Voice components remain as transport layer
- Implement transcript storage for evaluation

### 8.4 RAG Implementation
- Set up vector database (Chroma for local development, Pinecone for production)
- Create document processing pipeline for PDF menus
- Implement embedding creation and storage
- Build retrieval mechanism for menu items

## Phase 9: Testing and Evaluation

### 9.1 Component Testing
- Unit tests for each custom component
- Integration tests for component interactions
- Mock API responses for testing
- Test coverage reporting

### 9.2 Flow Testing
- Test all conversation paths
- Validate error handling
- Check data flow between components
- Performance testing with simulated load

### 9.3 Evaluation Framework
- Implement logging for all conversation turns
- Create evaluation dashboard with metrics visualization
- Set up automated evaluation metrics collection
- Implement A/B testing for different model versions

### 9.4 User Acceptance Testing
- Test with sample conversations
- Validate intent classification accuracy
- Check response relevance scores
- Gather feedback on conversation flow

## Implementation Timeline

### Week 1: Environment Setup and Core Components
- Set up LangFlow environment with Docker
- Create GuestManager, MenuManager, and OrderManager components
- Implement basic API integration
- Set up development and testing environments

### Week 2: Conversation Flow Components
- Create greeting, text processing, and utility components
- Design main conversation flow in LangFlow UI
- Implement conditional paths
- Create initial test cases

### Week 3: RAG Integration
- Set up vector database (Chroma for development)
- Create document processing and vector database components
- Integrate RAG into menu item search
- Test retrieval accuracy

### Week 4: Evaluation and Logging
- Implement conversation logging components
- Create evaluation metrics components
- Set up evaluation dashboard
- Implement intent classification

### Week 5: Advanced Features
- Implement emotional intelligence components
- Add chain-of-thought reasoning
- Create hybrid search functionality
- Implement transcript storage

### Week 6: Testing and Refinement
- Test all conversation paths
- Refine component interactions
- Optimize RAG performance
- Conduct user acceptance testing

### Week 7: Documentation and Deployment
- Document all components and flows
- Create user guides and developer documentation
- Prepare for production deployment
- Create deployment scripts and procedures

## Benefits of LangFlow Implementation

1. **Visual Development**: Easy to understand and modify conversation flows
2. **Modularity**: Components can be reused and tested independently
3. **Observability**: Built-in logging and monitoring capabilities
4. **Collaboration**: Multiple team members can work on different components
5. **Scalability**: Easy to add new features and conversation paths
6. **Evaluation**: Built-in support for logging and metrics collection
7. **RAG Integration**: Natural integration point for vector database and retrieval
8. **Employer Requirements Alignment**: Addresses all key requirements including:
   - RAG-based system with vector databases
   - Transcript storage and logging
   - Evaluation tools for LLM performance
   - Intent classification with metadata
   - Chain-of-thought reasoning
   - Hybrid search capabilities
   - Iteration support for model versions

## Future Enhancements

1. **n8n Workflow Integration**: Connect LangFlow to n8n for workflow automation
2. **Langflow Integration**: Use Langflow for visual workflow design
3. **Advanced TTS Models**: Integrate expressive TTS models with emotional capabilities
4. **Multi-model Support**: Implement support for different LLM versions
5. **Real-time Analytics Dashboard**: Create real-time monitoring of conversation metrics
6. **Automated Retraining Pipeline**: Implement feedback loop for continuous model improvement