# Hotel Voice AI Concierge - Monorepo

A full-stack hotel room service AI concierge system with voice interaction capabilities.

## 🏨 Project Overview

This system enables hotel guests to order room service through natural voice conversations with an AI concierge. The AI avatar provides a personalized, interactive experience for browsing menus, placing orders, and receiving confirmations.

### Key Features

- 🎙️ **Voice-First Interface**: Natural conversation with AI using Pipecat + Daily.co
- 🍽️ **Smart Menu System**: Dynamic menu browsing with categories and availability
- 📱 **Room-Based Authentication**: Seamless guest identification by room number
- 📊 **Real-Time Order Tracking**: Live status updates from order to delivery
- 👨‍💼 **Admin Dashboard**: Comprehensive order management for hotel staff
- 🔄 **RESTful API**: Complete backend API for all operations

## 🏗️ Monorepo Structure

```
voice_ai_concierge/
├── backend/                 # FastAPI backend application
│   ├── app/                # Main application code
│   │   ├── routers/        # API route handlers
│   │   ├── models.py       # Database models
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── main.py         # FastAPI app setup
│   ├── prisma/             # Database schema and migrations
│   ├── config/             # Configuration settings
│   ├── data/               # Seed data and fixtures
│   ├── scripts/            # Utility scripts
│   └── requirements.txt    # Python dependencies
├── frontend/               # React/Next.js frontend (planned)
│   ├── src/                # React components and pages
│   ├── public/             # Static assets
│   └── README.md           # Frontend-specific documentation
├── docs/                   # Project documentation
│   ├── API_REFERENCE.md    # Complete API documentation
│   ├── hotel_ai_architecture.md
│   ├── hotel_concierge_prd.md
│   └── DEVELOPMENT.md      # Development workflow guide
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend, when ready)
- Git

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd voice_ai_concierge
   ```

2. **Set up Python environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp ../.env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**:
   ```bash
   # If using Prisma
   npx prisma generate
   npx prisma db push
   
   # Or run database setup script
   python scripts/seed_database.py
   ```

6. **Start the backend server**:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup (When Ready)

```bash
cd frontend
npm install
npm run dev
```

## 📚 Documentation

- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation with examples
- **[Architecture](docs/hotel_ai_architecture.md)** - System architecture and design decisions
- **[Product Requirements](docs/hotel_concierge_prd.md)** - Product specifications and requirements
- **[Development Guide](docs/DEVELOPMENT.md)** - Development workflow and best practices

## 🔧 Development Workflow

### Running the Full Stack

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Start Frontend** (Terminal 2, when ready):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Applications**:
   - Backend API: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Frontend: `http://localhost:3000` (when ready)

### API Testing

Use the interactive API documentation at `http://localhost:8000/docs` or test with curl:

```bash
# Get all menu items
curl -X GET "http://localhost:8000/api/v1/menu-items?is_available=true"

# Create a new order
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "guest_id": "guest_123",
    "order_items": [
      {
        "menu_item_id": "menu_001",
        "quantity": 2
      }
    ]
  }'
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104.x
- **Database**: SQLite with Prisma ORM
- **Voice AI**: Pipecat-AI + Daily.co WebRTC
- **LLM**: OpenAI GPT models
- **TTS**: Cartesia or OpenAI TTS
- **STT**: Deepgram

### Frontend (Planned)
- **Framework**: Next.js 14.x
- **UI**: React 18.x + Tailwind CSS
- **WebRTC**: @daily-co/daily-js
- **State**: React Context or Zustand
- **TypeScript**: Full type safety

### Infrastructure
- **Deployment**: Railway (backend) + Vercel (frontend)
- **Database**: SQLite for development, PostgreSQL for production
- **Monitoring**: Built-in logging with Loguru

## 🌟 Key Features

### Voice AI Pipeline
- Natural language understanding for menu browsing
- Context-aware conversation flow
- Order confirmation and guest information collection
- Integration with hotel room management

### API Capabilities
- RESTful endpoints for all operations
- Real-time order status updates
- Guest management and room association
- Menu item management with categories
- Voice session tracking and transcription

### Data Models
- **Guests**: Room-based guest management
- **Menu**: Categorized items with pricing and availability
- **Orders**: Complete order lifecycle tracking
- **Voice Sessions**: Conversation logs and audio recordings

## 🔐 Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL="file:./database.db"

# API Keys
OPENAI_API_KEY="your-openai-key"
DAILY_API_KEY="your-daily-key"
DEEPGRAM_API_KEY="your-deepgram-key"
CARTESIA_API_KEY="your-cartesia-key"

# Daily.co Configuration
DAILY_DOMAIN="your-daily-domain.daily.co"

# Application Settings
DEBUG=true
LOG_LEVEL="INFO"
```

## 📝 API Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/guests` | GET, POST, PUT, DELETE | Guest management |
| `/api/v1/categories` | GET, POST, PUT, DELETE | Menu categories |
| `/api/v1/menu-items` | GET, POST, PUT, DELETE | Menu item management |
| `/api/v1/orders` | GET, POST, PUT, PATCH, DELETE | Order operations |
| `/api/v1/voice-sessions` | GET, POST, PUT, PATCH, DELETE | Voice session tracking |

See [API_REFERENCE.md](docs/API_REFERENCE.md) for complete documentation.

## 🧪 Testing

```bash
# Run backend tests
cd backend
python -m pytest

# Test specific endpoints
python test_order_storage.py
```

## 🚀 Deployment

### Backend (Railway)
1. Connect GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push to main branch

### Frontend (Vercel, when ready)
1. Connect GitHub repository to Vercel
2. Configure build settings for Next.js
3. Set environment variables in Vercel dashboard

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** following the coding standards
4. **Test thoroughly** with both unit and integration tests
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Coding Standards
- Follow FastAPI best practices for backend
- Use TypeScript for all frontend code
- Implement proper error handling
- Add comprehensive API documentation
- Write tests for new features

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection**: Ensure SQLite file has proper permissions
2. **API Keys**: Verify all required API keys are set in `.env`
3. **Port Conflicts**: Backend runs on port 8000, frontend on 3000
4. **CORS Issues**: Check CORS configuration in `app/main.py`

### Getting Help

- Check the [API Documentation](docs/API_REFERENCE.md)
- Review [Architecture Documentation](docs/hotel_ai_architecture.md)
- Create an issue in the GitHub repository

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent Python web framework
- Pipecat-AI for voice AI pipeline capabilities
- Daily.co for WebRTC infrastructure
- OpenAI for language model capabilities

---

**Note**: This is a proof-of-concept system designed for hotel room service automation. The frontend is currently under development, but the backend API is fully functional and documented.
