import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Guest, Category, MenuItem, Order, OrderItem, VoiceSession, OrderStatus, PaymentStatus, SessionStatus

class TestGuestModel:
    def test_create_guest(self, db_session: Session):
        guest = Guest(
            name="Jane Smith",
            email="jane.smith@example.com",
            phone_number="+9876543210",
            room_number="202",
            check_in_date=datetime.utcnow(),
            check_out_date=datetime.utcnow() + timedelta(days=5),
            is_active=True
        )
        db_session.add(guest)
        db_session.commit()
        
        assert guest.id is not None
        assert guest.name == "Jane Smith"
        assert guest.email == "jane.smith@example.com"
        assert guest.room_number == "202"
        assert guest.is_active is True
        assert guest.created_at is not None
        assert guest.updated_at is not None
    
    def test_guest_relationships(self, db_session: Session, sample_guest: Guest, sample_menu_item: MenuItem):
        order = Order(
            guest_id=sample_guest.id,
            total_amount=10.50,
            special_requests="No onions"
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(sample_guest)
        
        assert len(sample_guest.orders) == 1
        assert sample_guest.orders[0].id == order.id
    
    def test_guest_unique_email(self, db_session: Session, sample_guest: Guest):
        duplicate_guest = Guest(
            name="Another Person",
            email=sample_guest.email,  # Same email
            room_number="303",
            check_in_date=datetime.utcnow()
        )
        db_session.add(duplicate_guest)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()

class TestCategoryModel:
    def test_create_category(self, db_session: Session):
        category = Category(
            name="Appetizers",
            description="Starters and small bites",
            is_active=True,
            display_order=2
        )
        db_session.add(category)
        db_session.commit()
        
        assert category.id is not None
        assert category.name == "Appetizers"
        assert category.description == "Starters and small bites"
        assert category.display_order == 2
    
    def test_category_relationships(self, db_session: Session, sample_category: Category, sample_menu_item: MenuItem):
        db_session.refresh(sample_category)
        assert len(sample_category.menu_items) == 1
        assert sample_category.menu_items[0].id == sample_menu_item.id
    
    def test_category_unique_name(self, db_session: Session, sample_category: Category):
        duplicate_category = Category(
            name=sample_category.name,  # Same name
            description="Different description"
        )
        db_session.add(duplicate_category)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()

class TestMenuItemModel:
    def test_create_menu_item(self, db_session: Session, sample_category: Category):
        menu_item = MenuItem(
            name="Burger",
            description="Beef burger with fries",
            price=12.99,
            category_id=sample_category.id,
            is_available=True,
            preparation_time=20,
            dietary="contains-dairy",
            image_url="https://example.com/burger.jpg"
        )
        db_session.add(menu_item)
        db_session.commit()
        
        assert menu_item.id is not None
        assert menu_item.name == "Burger"
        assert menu_item.price == 12.99
        assert menu_item.preparation_time == 20
        assert menu_item.dietary == "contains-dairy"
    
    def test_menu_item_relationships(self, db_session: Session, sample_menu_item: MenuItem, sample_category: Category):
        db_session.refresh(sample_menu_item)
        assert sample_menu_item.category.id == sample_category.id
        assert sample_menu_item.category.name == sample_category.name
    
    def test_menu_item_availability(self, db_session: Session, sample_menu_item: MenuItem):
        sample_menu_item.is_available = False
        db_session.commit()
        db_session.refresh(sample_menu_item)
        
        assert sample_menu_item.is_available is False

class TestOrderModel:
    def test_create_order(self, db_session: Session, sample_guest: Guest):
        order = Order(
            guest_id=sample_guest.id,
            status=OrderStatus.PENDING,
            total_amount=25.50,
            special_requests="Extra napkins",
            delivery_notes="Leave at door",
            payment_status=PaymentStatus.PENDING
        )
        db_session.add(order)
        db_session.commit()
        
        assert order.id is not None
        assert order.guest_id == sample_guest.id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == 25.50
    
    def test_order_status_transitions(self, db_session: Session, sample_order: Order):
        sample_order.status = OrderStatus.CONFIRMED
        db_session.commit()
        db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.CONFIRMED
        
        sample_order.status = OrderStatus.PREPARING
        db_session.commit()
        db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.PREPARING
        
        sample_order.status = OrderStatus.DELIVERED
        sample_order.actual_delivery_time = datetime.utcnow()
        db_session.commit()
        db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.DELIVERED
        assert sample_order.actual_delivery_time is not None
    
    def test_order_payment_status(self, db_session: Session, sample_order: Order):
        sample_order.payment_status = PaymentStatus.PAID
        sample_order.payment_method = "credit_card"
        db_session.commit()
        db_session.refresh(sample_order)
        
        assert sample_order.payment_status == PaymentStatus.PAID
        assert sample_order.payment_method == "credit_card"
    
    def test_order_cascade_delete(self, db_session: Session, sample_order: Order):
        order_id = sample_order.id
        order_items_count = len(sample_order.order_items)
        
        assert order_items_count > 0
        
        db_session.delete(sample_order)
        db_session.commit()
        
        # Check that order items are also deleted
        remaining_items = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        assert len(remaining_items) == 0

class TestOrderItemModel:
    def test_create_order_item(self, db_session: Session, sample_order: Order, sample_menu_item: MenuItem):
        order_item = OrderItem(
            order_id=sample_order.id,
            menu_item_id=sample_menu_item.id,
            quantity=3,
            unit_price=5.00,
            total_price=15.00,
            special_notes="Extra hot"
        )
        db_session.add(order_item)
        db_session.commit()
        
        assert order_item.id is not None
        assert order_item.quantity == 3
        assert order_item.unit_price == 5.00
        assert order_item.total_price == 15.00
    
    def test_order_item_relationships(self, db_session: Session, sample_order: Order):
        db_session.refresh(sample_order)
        order_item = sample_order.order_items[0]
        
        assert order_item.order.id == sample_order.id
        assert order_item.menu_item is not None

class TestVoiceSessionModel:
    def test_create_voice_session(self, db_session: Session, sample_guest: Guest):
        session = VoiceSession(
            guest_id=sample_guest.id,
            room_number="101",
            session_id="session_123",
            status=SessionStatus.ACTIVE,
            transcript="Hello, I would like to order room service"
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.guest_id == sample_guest.id
        assert session.session_id == "session_123"
        assert session.status == SessionStatus.ACTIVE
        assert session.start_time is not None
    
    def test_voice_session_completion(self, db_session: Session, sample_guest: Guest, sample_order: Order):
        session = VoiceSession(
            guest_id=sample_guest.id,
            room_number="101",
            session_id="session_456",
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        db_session.commit()
        
        # Complete the session
        session.status = SessionStatus.COMPLETED
        session.end_time = datetime.utcnow()
        session.order_id = sample_order.id
        session.transcript = "Order completed successfully"
        db_session.commit()
        db_session.refresh(session)
        
        assert session.status == SessionStatus.COMPLETED
        assert session.end_time is not None
        assert session.order_id == sample_order.id
    
    def test_voice_session_unique_session_id(self, db_session: Session):
        session1 = VoiceSession(
            session_id="unique_session_001",
            room_number="201"
        )
        db_session.add(session1)
        db_session.commit()
        
        session2 = VoiceSession(
            session_id="unique_session_001",  # Same session_id
            room_number="202"
        )
        db_session.add(session2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()

class TestModelTimestamps:
    def test_auto_timestamps(self, db_session: Session, sample_guest: Guest):
        created_at = sample_guest.created_at
        updated_at = sample_guest.updated_at
        
        assert created_at is not None
        assert updated_at is not None
        assert created_at == updated_at
        
        # Update the guest
        sample_guest.name = "Updated Name"
        db_session.commit()
        db_session.refresh(sample_guest)
        
        assert sample_guest.created_at == created_at
        assert sample_guest.updated_at > updated_at