# Development Workflow Guide

This guide covers how to set up, develop, and maintain the Hotel Voice AI Concierge system.

## 🚀 Initial Setup

### Prerequisites

- **Python 3.11+** (recommended: 3.11.7)
- **Node.js 18+** (for frontend when ready)
- **Git** for version control
- **VS Code** or your preferred IDE

### Environment Setup

1. **Clone and Navigate**:
   ```bash
   git clone <repository-url>
   cd voice_ai_concierge
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Database Setup**:
   ```bash
   # Option 1: Using SQLAlchemy (current setup)
   python scripts/seed_database.py
   
   # Option 2: If using Prisma (alternative)
   cd backend
   npx prisma generate
   npx prisma db push
   npx prisma db seed
   ```

## 🏃‍♂️ Running the Development Environment

### Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access Points:**
- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend Development (When Ready)

```bash
cd frontend
npm install
npm run dev
```

**Access Point:**
- Frontend: `http://localhost:3000`

### Running Both Simultaneously

**Terminal 1 (Backend):**
```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend && npm run dev
```

## 🗄️ Database Management

### Current Setup (SQLAlchemy + SQLite)

```bash
# Create/update database schema
cd backend
python scripts/seed_database.py

# Reset database (destructive)
rm database.db
python scripts/seed_database.py

# View database contents
sqlite3 database.db
.tables
.schema orders
SELECT * FROM orders LIMIT 5;
.quit
```

### Alternative Setup (Prisma)

```bash
cd backend

# Generate Prisma client
npx prisma generate

# Push schema to database
npx prisma db push

# Seed database with sample data
npx prisma db seed

# View database in browser
npx prisma studio
```

### Database Migrations

For production deployments with schema changes:

```bash
# Create migration
npx prisma migrate dev --name add_new_field

# Apply migrations in production
npx prisma migrate deploy
```

## 🧪 Testing

### Backend Testing

```bash
cd backend
source venv/bin/activate

# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_order_storage.py

# Run with coverage
python -m pytest --cov=app

# Test specific functionality
python test_order_storage.py
```

### API Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test menu items
curl http://localhost:8000/api/v1/menu-items

# Test order creation
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "guest_id": "test_guest",
    "order_items": [
      {
        "menu_item_id": "test_item",
        "quantity": 1
      }
    ]
  }'
```

### Frontend Testing (When Ready)

```bash
cd frontend

# Run unit tests
npm test

# Run integration tests
npm run test:e2e

# Run linting
npm run lint
```

## 🛠️ Development Tools

### Code Quality

```bash
# Backend formatting and linting
cd backend
black app/
flake8 app/
mypy app/

# Frontend formatting and linting
cd frontend
npm run format
npm run lint
npm run type-check
```

### Pre-commit Hooks

Set up pre-commit hooks to ensure code quality:

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🔧 Common Development Tasks

### Adding New API Endpoints

1. **Create Router** (in `backend/app/routers/`):
   ```python
   from fastapi import APIRouter, Depends
   from ..database import get_db
   
   router = APIRouter()
   
   @router.get("/")
   def get_items():
       return {"items": []}
   ```

2. **Add Schema** (in `backend/app/schemas.py`):
   ```python
   class ItemBase(BaseModel):
       name: str
       description: Optional[str] = None
   ```

3. **Add Model** (in `backend/app/models.py`):
   ```python
   class Item(Base):
       __tablename__ = "items"
       id = Column(String, primary_key=True)
       name = Column(String, nullable=False)
   ```

4. **Register Router** (in `backend/app/main.py`):
   ```python
   from .routers import items
   app.include_router(items.router, prefix="/api/v1/items", tags=["items"])
   ```

### Adding Database Models

1. **Define Model** (in `backend/app/models.py`)
2. **Create Schema** (in `backend/app/schemas.py`)
3. **Update Database**:
   ```bash
   # If using Prisma
   npx prisma db push
   
   # If using SQLAlchemy
   python scripts/seed_database.py
   ```

### Environment Management

```bash
# Activate environment
cd backend
source venv/bin/activate

# Install new package
pip install package-name
pip freeze > requirements.txt

# Deactivate environment
deactivate
```

## 🐛 Debugging

### Backend Debugging

1. **Enable Debug Mode**:
   ```bash
   export DEBUG=true
   uvicorn app.main:app --reload --log-level debug
   ```

2. **Add Logging**:
   ```python
   from loguru import logger
   
   logger.info("Processing order: {}", order_id)
   logger.error("Failed to create order: {}", str(e))
   ```

3. **Use Debugger**:
   ```python
   import pdb; pdb.set_trace()  # Add breakpoint
   ```

### API Debugging

```bash
# Check API health
curl -v http://localhost:8000/health

# Test with verbose output
curl -v -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"guest_id": "test"}'

# Check logs
tail -f backend/logs/app.log
```

### Database Debugging

```bash
# SQLite debugging
sqlite3 backend/database.db
.tables
.schema table_name
SELECT * FROM table_name WHERE condition;

# Prisma debugging
npx prisma studio  # Visual database browser
```

## 📦 Deployment Preparation

### Backend Deployment

1. **Environment Variables**:
   ```bash
   # Set production environment variables
   export ENVIRONMENT=production
   export DATABASE_URL=postgresql://...
   ```

2. **Dependencies**:
   ```bash
   pip freeze > requirements.txt
   ```

3. **Database Migration**:
   ```bash
   npx prisma migrate deploy  # If using Prisma
   ```

### Frontend Deployment (When Ready)

```bash
cd frontend
npm run build
npm run start
```

## 🔄 Git Workflow

### Branch Strategy

```bash
# Feature development
git checkout -b feature/new-feature
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# Create pull request via GitHub

# After merge
git checkout main
git pull origin main
git branch -d feature/new-feature
```

### Commit Convention

Follow conventional commits:
```bash
feat: add voice session tracking
fix: resolve order total calculation
docs: update API documentation
refactor: reorganize database models
test: add order creation tests
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**:
   ```bash
   lsof -ti:8000 | xargs kill -9
   uvicorn app.main:app --reload --port 8001
   ```

2. **Database Lock Issues**:
   ```bash
   # Stop all processes using database
   pkill -f "uvicorn"
   rm database.db  # Nuclear option
   python scripts/seed_database.py
   ```

3. **Import Errors**:
   ```bash
   # Ensure you're in the right directory
   cd backend
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

4. **API Key Issues**:
   ```bash
   # Check environment variables
   echo $OPENAI_API_KEY
   
   # Reload environment
   source .env
   ```

### Performance Issues

```bash
# Profile API endpoints
pip install py-spy
py-spy top --pid $(pgrep uvicorn)

# Database query analysis
# Add query logging in SQLAlchemy
```

## 📝 Documentation

### API Documentation

The API is automatically documented via FastAPI:
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI spec: `http://localhost:8000/openapi.json`

### Code Documentation

```python
def create_order(order_data: OrderCreate) -> Order:
    """
    Create a new order with validation.
    
    Args:
        order_data: Order creation data including items
        
    Returns:
        Created order with calculated totals
        
    Raises:
        HTTPException: If guest or menu items not found
    """
```

## 🔐 Security Considerations

### Development Environment

- Use `.env` files for sensitive data
- Never commit API keys to version control
- Use HTTPS in production
- Implement rate limiting for production

### Code Security

```bash
# Security scanning
pip install safety
safety check

# Dependency vulnerabilities
pip-audit
```

## 📊 Monitoring

### Development Monitoring

```bash
# API response times
curl -w "@curl-format.txt" -o /dev/null http://localhost:8000/api/v1/menu-items

# Resource usage
htop
```

### Production Monitoring

- Set up Sentry for error tracking
- Use application logs for debugging
- Monitor database performance
- Track API response times

## 🎯 Best Practices

### Code Organization

- Keep routers focused on HTTP concerns
- Put business logic in service layers
- Use dependency injection for database connections
- Implement proper error handling

### Database

- Use transactions for multi-step operations
- Implement proper indexing
- Validate data at both API and database levels
- Use connection pooling in production

### API Design

- Follow RESTful conventions
- Use appropriate HTTP status codes
- Implement proper pagination
- Version your APIs

### Testing

- Write tests for business logic
- Test API endpoints with various inputs
- Use fixtures for test data
- Mock external services

---

This development guide should be updated as the project evolves. Keep it current with any new tools, processes, or deployment procedures.
