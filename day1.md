# Day 1: Backend Infrastructure & Core Voice Pipeline

## Overview
Day 1 focuses on building the foundational backend infrastructure, database setup, and core voice pipeline functionality. By end of day, you'll have a working voice AI that can handle basic hotel room service conversations.

## Core Tasks

### 1. Database & API Setup (2-3 hours)
- **Prisma Schema Setup**: Modify existing schema for hotel room service
  - Update Order model with hotel-specific fields (roomNumber, bookingName, items as JSON)
  - Add menu items table for dynamic menu management
  - Generate Prisma client and push schema to SQLite

- **FastAPI Backend**: Create REST API endpoints
  - GET /menu - Return available room service items with prices
  - POST /order - Store completed orders with reference ID
  - GET /admin/orders - Admin dashboard endpoint with basic auth
  - Add CORS middleware for frontend integration

### 2. Voice Pipeline Modification (3-4 hours)
- **Adapt food_ordering_direct_functions.py** for hotel room service:
  - Replace pizza/sushi flow with hotel room service menu
  - Update flow states: start → menu_browsing → item_selection → guest_details → confirm → end
  - Modify pricing logic for room service items
  - Add guest information collection (room number, booking name)
  - Integrate order submission to FastAPI backend

- **Core Functions to Implement**:
  ```python
  async def browse_menu(flow_manager: FlowManager) -> tuple[None, str]
  async def select_items(flow_manager: FlowManager, items: list, quantities: list) -> tuple[OrderResult, str]
  async def collect_guest_info(flow_manager: FlowManager, room_number: str, booking_name: str) -> tuple[GuestInfo, str]
  async def confirm_order(flow_manager: FlowManager) -> tuple[None, str]
  async def submit_order(flow_manager: FlowManager) -> tuple[None, str]
  ```

### 3. Menu Data Structure (1 hour)
- **Static Menu Configuration**: Create comprehensive room service menu
  - Appetizers, Main courses, Desserts, Beverages
  - Include pricing, dietary restrictions, preparation time
  - Structure for easy LLM processing and natural conversation

### 4. Environment & Configuration (1 hour)
- **Environment Setup**: Configure all required API keys
  - Daily.co room management
  - OpenAI/LLM service keys
  - Deepgram STT service
  - Cartesia TTS service
  - Database connection strings

- **Railway Deployment Prep**: Prepare for backend deployment
  - Dockerfile creation
  - Environment variable configuration
  - Database persistence setup

### 5. Testing & Validation (1-2 hours)
- **Voice Pipeline Testing**: Test modified conversation flow
  - Verify STT/TTS functionality
  - Test menu browsing and item selection
  - Validate order data collection
  - Confirm database integration

- **API Endpoint Testing**: Validate REST endpoints
  - Test menu retrieval
  - Test order creation and storage
  - Verify admin dashboard data access

## Key Files to Create/Modify

### Backend Files
- `app/main.py` - FastAPI application setup
- `app/services.py` - Business logic for order processing
- `app/pipeline.py` - Modified hotel room service pipeline (based on food_ordering_direct_functions.py)
- `prisma/schema.prisma` - Updated database schema
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration

### Configuration Files
- `menu_data.py` - Static menu items and pricing
- `flow_config.py` - Hotel room service conversation flow

## Expected Deliverables
- ✅ Working FastAPI backend with database integration
- ✅ Modified voice pipeline for hotel room service conversations
- ✅ Complete menu data structure
- ✅ Functional order processing from voice to database
- ✅ Environment setup for all required services
- ✅ Backend ready for Railway deployment

## Success Criteria
- Voice AI can have natural conversation about room service menu
- Orders are successfully captured with guest details
- Database stores complete order information
- API endpoints return correct data for frontend integration
- All services properly configured and authenticated

## Technical Notes
- Use existing `food_ordering_direct_functions.py` as template
- Maintain Pipecat flow structure and patterns
- Ensure async/await patterns throughout
- Follow FastAPI best practices for API design
- Keep database schema simple but extensible