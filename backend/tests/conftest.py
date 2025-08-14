import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import tempfile
import os
from datetime import datetime, timedelta

from app.database import Base, get_db
from app.main import app
from app.models import Guest, Category, MenuItem, Order, OrderItem, VoiceSession

# Create a temporary database for testing
@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name
    
    DATABASE_URL = f"sqlite:///{test_db_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal
    
    # Cleanup
    app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(test_db_path)

@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def db_session(test_db):
    """Create a database session for testing."""
    session = test_db()
    yield session
    session.close()

@pytest.fixture
def sample_guest(db_session):
    """Create a sample guest."""
    guest = Guest(
        name="John Doe",
        email="john.doe@example.com",
        phone_number="+1234567890",
        room_number="101",
        check_in_date=datetime.utcnow(),
        check_out_date=datetime.utcnow() + timedelta(days=3)
    )
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    return guest

@pytest.fixture
def sample_category(db_session):
    """Create a sample category."""
    category = Category(
        name="Appetizers",
        description="Start your meal with our delicious appetizers",
        display_order=1
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category

@pytest.fixture
def sample_menu_items(db_session, sample_category):
    """Create sample menu items."""
    items = [
        MenuItem(
            name="Caesar Salad",
            description="Fresh romaine lettuce with Caesar dressing",
            price=12.99,
            category_id=sample_category.id,
            preparation_time=10,
            dietary="vegetarian"
        ),
        MenuItem(
            name="Chicken Wings",
            description="Crispy chicken wings with buffalo sauce",
            price=14.99,
            category_id=sample_category.id,
            preparation_time=15
        ),
        MenuItem(
            name="Mozzarella Sticks",
            description="Breaded mozzarella with marinara sauce",
            price=9.99,
            category_id=sample_category.id,
            preparation_time=10,
            dietary="vegetarian",
            is_available=False
        )
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    for item in items:
        db_session.refresh(item)
    return items

@pytest.fixture
def sample_order(db_session, sample_guest, sample_menu_items):
    """Create a sample order with items."""
    order = Order(
        guest_id=sample_guest.id,
        total_amount=27.98,
        special_requests="No onions please"
    )
    db_session.add(order)
    db_session.flush()
    
    # Add order items
    order_items = [
        OrderItem(
            order_id=order.id,
            menu_item_id=sample_menu_items[0].id,
            quantity=1,
            unit_price=sample_menu_items[0].price,
            total_price=sample_menu_items[0].price
        ),
        OrderItem(
            order_id=order.id,
            menu_item_id=sample_menu_items[1].id,
            quantity=1,
            unit_price=sample_menu_items[1].price,
            total_price=sample_menu_items[1].price
        )
    ]
    for item in order_items:
        db_session.add(item)
    
    db_session.commit()
    db_session.refresh(order)
    return order

@pytest.fixture
def sample_voice_session(db_session, sample_guest):
    """Create a sample voice session."""
    session = VoiceSession(
        guest_id=sample_guest.id,
        room_number=sample_guest.room_number,
        session_id="session_123",
        transcript="I would like to order room service"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session