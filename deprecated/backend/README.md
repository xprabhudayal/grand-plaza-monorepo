# Hotel Voice AI Concierge - Backend

## Overview

The backend of the Hotel Voice AI Concierge system provides a complete solution for hotel room service ordering through both web and voice interfaces. It includes a FastAPI REST API for data management and a Pipecat-based voice pipeline for conversational ordering.

## Key Components

### FastAPI REST API
- **Guest Management**: CRUD operations for hotel guests
- **Menu Management**: Categories and menu items with pricing/dietary info
- **Order Processing**: Complete order lifecycle management
- **Voice Sessions**: Recording and management of voice conversations
- **Database**: SQLite with SQLAlchemy ORM

### Voice Pipeline
- **Pipecat Integration**: Real-time voice processing
- **Conversation Flow**: State-based ordering process
- **Speech Services**: Deepgram/Soniox STT, Cartesia TTS
- **LLM Integration**: Groq/OpenAI/Perplexity for conversation intelligence

## Quick Start

### Prerequisites
- Python 3.8+
- Pipecat AI dependencies
- API keys for voice services

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
python setup_config.py setup

# Seed database with menu data
python scripts/seed_database.py
```

### Running Services
```bash
# Start API server
python launch.py api

# Start voice pipeline
python launch.py voice

# Run tests
python test_order_storage.py
```

## Project Structure
```
backend/
├── app/                 # FastAPI application
│   ├── routers/         # API endpoints
│   ├── models.py        # Database models
│   ├── schemas.py       # Pydantic schemas
│   └── ...
├── data/                # Menu data
├── config/              # Configuration management
├── scripts/             # Utility scripts
├── hotel_room_service_simplified.py  # Voice pipeline
└── ...
```

## Documentation

- [API Reference](../docs/API_REFERENCE.md) - Complete API documentation
- [Backend Architecture](../docs/BACKEND_ARCHITECTURE.md) - Detailed architecture overview
- [Development Guide](../docs/DEVELOPMENT.md) - Setup and development instructions

## Environment Variables

Create a `.env` file with the following keys:
```bash
# Voice Services
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
GROQ_API_KEY=your_groq_key  # or OPENAI_API_KEY=your_openai_key

# Daily.co Transport
DAILY_API_KEY=your_daily_key
DAILY_ROOM_URL=your_daily_room_url

# Database
DATABASE_URL=sqlite:///./database.db

# Hotel Configuration
HOTEL_NAME="Grand Plaza Hotel"
HOTEL_PHONE="+1-555-0123"
```

## Testing

Run integration tests to verify the system:
```bash
# Start the API server first in another terminal
python launch.py api

# Then run tests
python test_order_storage.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the BSD 2-Clause License.