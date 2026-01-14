# Backend Test Suite

## Overview
Comprehensive test suite for the Hotel Voice AI Concierge backend API.

## Test Structure
```
backend/tests/
├── __init__.py
├── conftest.py           # Shared fixtures and test configuration
├── test_models.py        # Database model tests
├── test_schemas.py       # Pydantic schema validation tests
├── test_database.py      # Database operations tests
├── test_order_service.py # Order service business logic tests
└── test_routers.py       # API endpoint tests
```

## Running Tests

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=term-missing
```

### Run Specific Test Files
```bash
pytest tests/test_models.py
pytest tests/test_routers.py
```

### Run Tests by Marker
```bash
pytest -m unit          # Run unit tests only
pytest -m integration   # Run integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Verbose Output
```bash
pytest -v
```

## Test Coverage

The test suite covers:

- **Models (test_models.py)**
  - All SQLAlchemy models
  - Relationships and cascades
  - Constraints and validations
  - Timestamps and enums

- **Schemas (test_schemas.py)**
  - Pydantic model validation
  - Request/response schemas
  - Enum values
  - Optional and required fields

- **Database (test_database.py)**
  - Database connections
  - Transactions and rollbacks
  - Query operations
  - Cascade operations

- **Order Service (test_order_service.py)**
  - Order creation from voice data
  - Guest management
  - Menu item lookup
  - Error handling

- **API Routers (test_routers.py)**
  - All CRUD operations
  - Query parameters and filters
  - Error responses
  - Data validation

## Test Fixtures

Key fixtures in `conftest.py`:

- `db_session`: Fresh database session for each test
- `client`: FastAPI test client
- `sample_guest`: Pre-configured guest
- `sample_category`: Pre-configured category
- `sample_menu_item`: Pre-configured menu item
- `sample_order`: Pre-configured order with items
- `multiple_menu_items`: Multiple menu items for testing

## Configuration

### pytest.ini
Test discovery and execution configuration

### pyproject.toml
Coverage settings and pytest options

## Writing New Tests

1. Create test classes prefixed with `Test`
2. Create test methods prefixed with `test_`
3. Use fixtures for common setup
4. Mark async tests with `@pytest.mark.asyncio`
5. Use meaningful assertions

Example:
```python
class TestNewFeature:
    def test_feature_success(self, client, sample_data):
        response = client.post("/api/endpoint", json=data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
```

## CI/CD Integration

Add to your CI pipeline:
```yaml
- name: Run Tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml
```

## Troubleshooting

### Database Issues
- Tests use SQLite in-memory database
- Each test gets a fresh database
- Check `conftest.py` for database setup

### Async Tests
- Use `@pytest.mark.asyncio` decorator
- Use `AsyncMock` for async function mocks
- Check `asyncio_mode = auto` in pytest.ini

### Import Errors
- Ensure backend directory is in PYTHONPATH
- Check `sys.path` manipulation in conftest.py