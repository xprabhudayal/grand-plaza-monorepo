# Developer Quickstart Guide

## Setting Up the Development Environment

### 1. Clone the Repository
```bash
git clone <repository-url>
cd voice_ai_concierge
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\\Scripts\\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
# Create .env file from template
python setup_config.py create-env

# Edit the .env file with your API keys
# You can use any text editor, e.g.:
nano .env
```

### 4. Seed the Database
```bash
# Populate the database with menu data
python scripts/seed_database.py
```

## Running the Application

### Start the API Server
```bash
# In one terminal, start the API server
python launch.py api
```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

### Start the Voice Pipeline
```bash
# In another terminal, start the voice pipeline
python launch.py voice
```

Note: You'll need a Daily.co room URL configured in your `.env` file for the voice pipeline to work.

## Testing

### Run Integration Tests
```bash
# Make sure the API server is running, then:
python test_order_storage.py
```

### Manual API Testing
You can test the API using curl or the FastAPI documentation interface:

```bash
# Get all menu items
curl http://localhost:8000/api/v1/menu-items

# Get menu items by category
curl http://localhost:8000/api/v1/menu-items/by-category/{category_id}

# Create a guest
curl -X POST http://localhost:8000/api/v1/guests \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "room_number": "101",
    "check_in_date": "2025-08-14T15:00:00Z"
  }'
```

## Project Structure Overview

- `app/` - FastAPI application with routers, models, and schemas
- `data/` - Menu data and access functions
- `config/` - Configuration management
- `scripts/` - Utility scripts for database seeding and testing
- `hotel_room_service_simplified.py` - Main voice pipeline implementation

## Key API Endpoints

### Guests
- `GET /api/v1/guests` - List all guests
- `POST /api/v1/guests` - Create a new guest
- `GET /api/v1/guests/room/{room_number}` - Get guest by room number

### Menu
- `GET /api/v1/categories` - List all menu categories
- `GET /api/v1/menu-items` - List all menu items
- `GET /api/v1/menu-items/by-category/{category_id}` - List items in a category

### Orders
- `GET /api/v1/orders` - List all orders
- `POST /api/v1/orders` - Create a new order
- `GET /api/v1/orders/{order_id}` - Get order details
- `PATCH /api/v1/orders/{order_id}/status` - Update order status

## Voice Pipeline Development

The voice pipeline uses a state-based flow system:

1. **States**: Each conversation state (greeting, menu browsing, etc.)
2. **Functions**: Actions that can be taken in each state
3. **Transitions**: Movement between states based on user actions

To modify the conversation flow, edit the `hotel_room_service_flow` configuration in `hotel_room_service_simplified.py`.

## Common Development Tasks

### Adding a New Menu Category
1. Update `data/menu_data.py` to add the new category
2. Use the API to create the category in the database:
   ```bash
   curl -X POST http://localhost:8000/api/v1/categories \\
     -H "Content-Type: application/json" \\
     -d '{
       "name": "New Category",
       "description": "Description of new category"
     }'
   ```

### Adding a New Menu Item
1. Update `data/menu_data.py` to add the new item
2. Use the API to create the menu item in the database:
   ```bash
   curl -X POST http://localhost:8000/api/v1/menu-items \\
     -H "Content-Type: application/json" \\
     -d '{
       "name": "New Item",
       "description": "Description of new item",
       "price": 15.99,
       "category_id": "existing_category_id"
     }'
   ```

### Modifying Voice Flow
1. Edit the `hotel_room_service_flow` configuration in `hotel_room_service_simplified.py`
2. Add new functions if needed
3. Test the changes by running the voice pipeline

## Troubleshooting

### Database Issues
- If you need to reset the database, delete `database.db` and run `python scripts/seed_database.py`

### Voice Pipeline Not Starting
- Verify your Daily.co API key and room URL are correctly configured
- Check that all required environment variables are set

### API Errors
- Check the server logs for detailed error messages
- Verify the database is properly seeded with menu data

## Code Quality

### Linting
The project uses standard Python linting. Before committing changes, run:
```bash
# If you have flake8 installed
flake8 .

# Or if you have pylint installed
pylint app/
```

### Type Checking
The codebase includes type hints. You can check types with:
```bash
# If you have mypy installed
mypy .
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Add tests if applicable
4. Ensure all tests pass
5. Submit a pull request with a clear description of changes

## Documentation

- [API Reference](../docs/API_REFERENCE.md) - Complete API documentation
- [Backend Architecture](../docs/BACKEND_ARCHITECTURE.md) - Detailed architecture overview
- [Product Requirements](../docs/hotel_concierge_prd.md) - Product requirements document