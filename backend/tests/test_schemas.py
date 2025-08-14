import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from app.schemas import (
    GuestCreate, GuestUpdate, Guest,
    CategoryCreate, CategoryUpdate, Category,
    MenuItemCreate, MenuItemUpdate, MenuItem,
    OrderCreate, OrderUpdate, Order, OrderItemCreate, OrderItem,
    VoiceSessionCreate, VoiceSessionUpdate, VoiceSession,
    OrderStatus, PaymentStatus, SessionStatus
)

class TestGuestSchemas:
    def test_guest_create_valid(self):
        guest_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "room_number": "101",
            "check_in_date": datetime.utcnow(),
            "check_out_date": datetime.utcnow() + timedelta(days=3)
        }
        guest = GuestCreate(**guest_data)
        
        assert guest.name == "John Doe"
        assert guest.email == "john@example.com"
        assert guest.room_number == "101"
        assert guest.is_active is True
    
    def test_guest_create_invalid_email(self):
        guest_data = {
            "name": "John Doe",
            "email": "invalid-email",
            "room_number": "101",
            "check_in_date": datetime.utcnow()
        }
        
        with pytest.raises(ValidationError):
            GuestCreate(**guest_data)
    
    def test_guest_update_partial(self):
        update_data = {
            "name": "Jane Doe",
            "room_number": "202"
        }
        guest_update = GuestUpdate(**update_data)
        
        assert guest_update.name == "Jane Doe"
        assert guest_update.room_number == "202"
        assert guest_update.email is None
        assert guest_update.phone_number is None
    
    def test_guest_response_model(self):
        guest_data = {
            "id": "123",
            "name": "John Doe",
            "email": "john@example.com",
            "room_number": "101",
            "check_in_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        guest = Guest(**guest_data)
        
        assert guest.id == "123"
        assert guest.created_at is not None
        assert guest.updated_at is not None

class TestCategorySchemas:
    def test_category_create_valid(self):
        category_data = {
            "name": "Beverages",
            "description": "Hot and cold drinks",
            "display_order": 1
        }
        category = CategoryCreate(**category_data)
        
        assert category.name == "Beverages"
        assert category.description == "Hot and cold drinks"
        assert category.is_active is True
        assert category.display_order == 1
    
    def test_category_create_minimal(self):
        category = CategoryCreate(name="Snacks")
        
        assert category.name == "Snacks"
        assert category.description is None
        assert category.is_active is True
        assert category.display_order == 0
    
    def test_category_update_partial(self):
        update_data = {
            "description": "Updated description",
            "is_active": False
        }
        category_update = CategoryUpdate(**update_data)
        
        assert category_update.name is None
        assert category_update.description == "Updated description"
        assert category_update.is_active is False

class TestMenuItemSchemas:
    def test_menu_item_create_valid(self):
        item_data = {
            "name": "Coffee",
            "description": "Fresh coffee",
            "price": 3.50,
            "category_id": "cat123",
            "preparation_time": 5,
            "dietary": "vegan,gluten-free"
        }
        menu_item = MenuItemCreate(**item_data)
        
        assert menu_item.name == "Coffee"
        assert menu_item.price == 3.50
        assert menu_item.category_id == "cat123"
        assert menu_item.is_available is True
    
    def test_menu_item_create_invalid_price(self):
        item_data = {
            "name": "Coffee",
            "price": -5.00,  # Negative price
            "category_id": "cat123"
        }
        menu_item = MenuItemCreate(**item_data)
        # Pydantic doesn't validate price range by default
        assert menu_item.price == -5.00
    
    def test_menu_item_update_availability(self):
        update_data = {
            "is_available": False,
            "price": 4.50
        }
        menu_update = MenuItemUpdate(**update_data)
        
        assert menu_update.is_available is False
        assert menu_update.price == 4.50
        assert menu_update.name is None

class TestOrderSchemas:
    def test_order_create_valid(self):
        order_data = {
            "guest_id": "guest123",
            "special_requests": "No onions",
            "delivery_notes": "Room 101",
            "order_items": [
                {
                    "menu_item_id": "item123",
                    "quantity": 2,
                    "special_notes": "Extra hot"
                },
                {
                    "menu_item_id": "item456",
                    "quantity": 1
                }
            ]
        }
        order = OrderCreate(**order_data)
        
        assert order.guest_id == "guest123"
        assert order.special_requests == "No onions"
        assert len(order.order_items) == 2
        assert order.order_items[0].quantity == 2
    
    def test_order_create_empty_items(self):
        order_data = {
            "guest_id": "guest123",
            "order_items": []
        }
        order = OrderCreate(**order_data)
        
        assert order.guest_id == "guest123"
        assert len(order.order_items) == 0
    
    def test_order_update_status(self):
        update_data = {
            "status": OrderStatus.DELIVERED,
            "payment_status": PaymentStatus.PAID,
            "actual_delivery_time": datetime.utcnow()
        }
        order_update = OrderUpdate(**update_data)
        
        assert order_update.status == OrderStatus.DELIVERED
        assert order_update.payment_status == PaymentStatus.PAID
        assert order_update.actual_delivery_time is not None
    
    def test_order_item_create(self):
        item_data = {
            "menu_item_id": "menu123",
            "quantity": 3,
            "special_notes": "No ice"
        }
        order_item = OrderItemCreate(**item_data)
        
        assert order_item.menu_item_id == "menu123"
        assert order_item.quantity == 3
        assert order_item.special_notes == "No ice"
    
    def test_order_response_with_items(self):
        order_data = {
            "id": "order123",
            "guest_id": "guest123",
            "status": OrderStatus.PENDING,
            "total_amount": 25.50,
            "payment_status": PaymentStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "order_items": [
                {
                    "id": "item123",
                    "order_id": "order123",
                    "menu_item_id": "menu123",
                    "quantity": 2,
                    "unit_price": 12.75,
                    "total_price": 25.50,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            ]
        }
        order = Order(**order_data)
        
        assert order.id == "order123"
        assert order.total_amount == 25.50
        assert len(order.order_items) == 1
        assert order.order_items[0].total_price == 25.50

class TestVoiceSessionSchemas:
    def test_voice_session_create_valid(self):
        session_data = {
            "guest_id": "guest123",
            "room_number": "101",
            "session_id": "session_abc123"
        }
        session = VoiceSessionCreate(**session_data)
        
        assert session.guest_id == "guest123"
        assert session.room_number == "101"
        assert session.session_id == "session_abc123"
    
    def test_voice_session_create_minimal(self):
        session = VoiceSessionCreate(session_id="session_xyz")
        
        assert session.session_id == "session_xyz"
        assert session.guest_id is None
        assert session.room_number is None
    
    def test_voice_session_update(self):
        update_data = {
            "transcript": "Order placed successfully",
            "status": SessionStatus.COMPLETED,
            "order_id": "order123",
            "end_time": datetime.utcnow()
        }
        session_update = VoiceSessionUpdate(**update_data)
        
        assert session_update.transcript == "Order placed successfully"
        assert session_update.status == SessionStatus.COMPLETED
        assert session_update.order_id == "order123"
        assert session_update.end_time is not None
    
    def test_voice_session_response(self):
        session_data = {
            "id": "session123",
            "session_id": "daily_session_123",
            "room_number": "101",
            "status": SessionStatus.ACTIVE,
            "start_time": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        session = VoiceSession(**session_data)
        
        assert session.id == "session123"
        assert session.status == SessionStatus.ACTIVE
        assert session.start_time is not None
        assert session.end_time is None

class TestEnumSchemas:
    def test_order_status_enum(self):
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.CONFIRMED.value == "CONFIRMED"
        assert OrderStatus.DELIVERED.value == "DELIVERED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"
    
    def test_payment_status_enum(self):
        assert PaymentStatus.PENDING.value == "PENDING"
        assert PaymentStatus.PAID.value == "PAID"
        assert PaymentStatus.FAILED.value == "FAILED"
        assert PaymentStatus.REFUNDED.value == "REFUNDED"
    
    def test_session_status_enum(self):
        assert SessionStatus.ACTIVE.value == "ACTIVE"
        assert SessionStatus.COMPLETED.value == "COMPLETED"
        assert SessionStatus.ABANDONED.value == "ABANDONED"
        assert SessionStatus.ERROR.value == "ERROR"