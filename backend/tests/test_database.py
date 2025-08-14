import pytest
from sqlalchemy.orm import Session
from app.database import get_db, create_tables, engine, Base
from app.models import Guest, Category, MenuItem, Order, OrderItem

class TestDatabase:
    def test_get_db_generator(self):
        db_gen = get_db()
        db = next(db_gen)
        
        assert isinstance(db, Session)
        assert db.is_active
        
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        assert not db.is_active
    
    def test_create_tables(self):
        # Drop all tables first
        Base.metadata.drop_all(bind=engine)
        
        # Create tables
        create_tables()
        
        # Check if tables exist
        inspector = engine.inspect(engine)
        table_names = inspector.get_table_names()
        
        assert "guests" in table_names
        assert "categories" in table_names
        assert "menu_items" in table_names
        assert "orders" in table_names
        assert "order_items" in table_names
        assert "voice_sessions" in table_names
    
    def test_database_transaction_commit(self, db_session: Session):
        guest = Guest(
            name="Test User",
            email="test@example.com",
            room_number="100"
        )
        db_session.add(guest)
        db_session.commit()
        
        retrieved_guest = db_session.query(Guest).filter(Guest.email == "test@example.com").first()
        assert retrieved_guest is not None
        assert retrieved_guest.name == "Test User"
    
    def test_database_transaction_rollback(self, db_session: Session):
        guest = Guest(
            name="Rollback User",
            email="rollback@example.com",
            room_number="999"
        )
        db_session.add(guest)
        db_session.rollback()
        
        retrieved_guest = db_session.query(Guest).filter(Guest.email == "rollback@example.com").first()
        assert retrieved_guest is None
    
    def test_database_cascade_operations(self, db_session: Session, sample_guest: Guest, sample_category: Category):
        # Create menu item
        menu_item = MenuItem(
            name="Test Item",
            price=10.00,
            category_id=sample_category.id
        )
        db_session.add(menu_item)
        db_session.flush()
        
        # Create order with items
        order = Order(
            guest_id=sample_guest.id,
            total_amount=20.00
        )
        db_session.add(order)
        db_session.flush()
        
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=2,
            unit_price=10.00,
            total_price=20.00
        )
        db_session.add(order_item)
        db_session.commit()
        
        # Delete order and check cascade
        db_session.delete(order)
        db_session.commit()
        
        remaining_items = db_session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        assert len(remaining_items) == 0
    
    def test_database_query_filtering(self, db_session: Session, multiple_menu_items):
        # Test price filtering
        expensive_items = db_session.query(MenuItem).filter(MenuItem.price > 3.00).all()
        assert len(expensive_items) == 2  # Juice (4.00) and Sandwich (8.50)
        
        # Test name filtering
        tea = db_session.query(MenuItem).filter(MenuItem.name == "Tea").first()
        assert tea is not None
        assert tea.price == 2.50
        
        # Test availability filtering
        available_items = db_session.query(MenuItem).filter(MenuItem.is_available == True).all()
        assert len(available_items) == len(multiple_menu_items)
    
    def test_database_relationships(self, db_session: Session, sample_order: Order):
        db_session.refresh(sample_order)
        
        # Test order -> guest relationship
        assert sample_order.guest is not None
        assert sample_order.guest.name == "John Doe"
        
        # Test order -> order_items relationship
        assert len(sample_order.order_items) > 0
        
        # Test order_item -> menu_item relationship
        order_item = sample_order.order_items[0]
        assert order_item.menu_item is not None
        assert order_item.menu_item.name == "Coffee"