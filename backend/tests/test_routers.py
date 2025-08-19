import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Guest, Category, MenuItem, Order, OrderStatus, PaymentStatus

class TestGuestsRouter:
    def test_get_guests(self, client: TestClient, sample_guest: Guest):
        response = client.get("/api/v1/guests/")
        assert response.status_code == 200
        guests = response.json()
        assert len(guests) >= 1
        assert any(g["id"] == sample_guest.id for g in guests)
    
    def test_get_guest_by_id(self, client: TestClient, sample_guest: Guest):
        response = client.get(f"/api/v1/guests/{sample_guest.id}")
        assert response.status_code == 200
        guest = response.json()
        assert guest["id"] == sample_guest.id
        assert guest["name"] == sample_guest.name
        assert guest["room_number"] == sample_guest.room_number
    
    def test_get_guest_not_found(self, client: TestClient):
        response = client.get("/api/v1/guests/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_create_guest(self, client: TestClient):
        guest_data = {
            "name": "New Guest",
            "email": "newguest@example.com",
            "room_number": "301",
            "check_in_date": datetime.utcnow().isoformat(),
            "check_out_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
        }
        response = client.post("/api/v1/guests", json=guest_data)
        assert response.status_code == 201
        guest = response.json()
        assert guest["name"] == "New Guest"
        assert guest["email"] == "newguest@example.com"
        assert guest["room_number"] == "301"
    
    def test_create_guest_duplicate_email(self, client: TestClient, sample_guest: Guest):
        guest_data = {
            "name": "Another Guest",
            "email": sample_guest.email,  # Duplicate email
            "room_number": "302",
            "check_in_date": datetime.utcnow().isoformat()
        }
        response = client.post("/api/v1/guests", json=guest_data)
        assert response.status_code == 400
    
    def test_update_guest(self, client: TestClient, sample_guest: Guest):
        update_data = {
            "name": "Updated Name",
            "room_number": "999"
        }
        response = client.put(f"/api/v1/guests/{sample_guest.id}", json=update_data)
        assert response.status_code == 200
        guest = response.json()
        assert guest["name"] == "Updated Name"
        assert guest["room_number"] == "999"
    
    def test_delete_guest(self, client: TestClient, db_session: Session):
        # Create a guest to delete
        guest = Guest(
            name="To Delete",
            email="delete@example.com",
            room_number="404"
        )
        db_session.add(guest)
        db_session.commit()
        
        response = client.delete(f"/api/v1/guests/{guest.id}")
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()
        
        # Verify guest is deactivated
        db_session.refresh(guest)
        assert guest.is_active is False

class TestCategoriesRouter:
    def test_get_categories(self, client: TestClient, sample_category: Category):
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) >= 1
        assert any(c["id"] == sample_category.id for c in categories)
    
    def test_get_category_by_id(self, client: TestClient, sample_category: Category):
        response = client.get(f"/api/v1/categories/{sample_category.id}")
        assert response.status_code == 200
        category = response.json()
        assert category["id"] == sample_category.id
        assert category["name"] == sample_category.name
    
    def test_create_category(self, client: TestClient):
        category_data = {
            "name": "Desserts",
            "description": "Sweet treats",
            "display_order": 3
        }
        response = client.post("/api/v1/categories", json=category_data)
        assert response.status_code == 201
        category = response.json()
        assert category["name"] == "Desserts"
        assert category["display_order"] == 3
    
    def test_update_category(self, client: TestClient, sample_category: Category):
        update_data = {
            "description": "Updated description",
            "display_order": 5
        }
        response = client.put(f"/api/v1/categories/{sample_category.id}", json=update_data)
        assert response.status_code == 200
        category = response.json()
        assert category["description"] == "Updated description"
        assert category["display_order"] == 5
    
    def test_delete_category(self, client: TestClient, db_session: Session):
        category = Category(name="To Delete")
        db_session.add(category)
        db_session.commit()
        
        response = client.delete(f"/api/v1/categories/{category.id}")
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()

class TestMenuItemsRouter:
    def test_get_menu_items(self, client: TestClient, sample_menu_item: MenuItem):
        response = client.get("/api/v1/menu-items")
        assert response.status_code == 200
        items = response.json()
        assert len(items) >= 1
        assert any(i["id"] == sample_menu_item.id for i in items)
    
    def test_get_menu_items_by_category(self, client: TestClient, sample_menu_item: MenuItem, sample_category: Category):
        response = client.get(f"/api/v1/menu-items?category_id={sample_category.id}")
        assert response.status_code == 200
        items = response.json()
        assert all(i["category_id"] == sample_category.id for i in items)
    
    def test_get_menu_items_available_only(self, client: TestClient, db_session: Session, sample_category: Category):
        # Create available and unavailable items
        available_item = MenuItem(
            name="Available Item",
            price=5.00,
            category_id=sample_category.id,
            is_available=True
        )
        unavailable_item = MenuItem(
            name="Unavailable Item",
            price=6.00,
            category_id=sample_category.id,
            is_available=False
        )
        db_session.add_all([available_item, unavailable_item])
        db_session.commit()
        
        response = client.get("/api/v1/menu-items?available_only=true")
        assert response.status_code == 200
        items = response.json()
        assert all(i["is_available"] for i in items)
        assert not any(i["name"] == "Unavailable Item" for i in items)
    
    def test_get_menu_item_by_id(self, client: TestClient, sample_menu_item: MenuItem):
        response = client.get(f"/api/v1/menu-items/{sample_menu_item.id}")
        assert response.status_code == 200
        item = response.json()
        assert item["id"] == sample_menu_item.id
        assert item["name"] == sample_menu_item.name
        assert item["price"] == sample_menu_item.price
    
    def test_create_menu_item(self, client: TestClient, sample_category: Category):
        item_data = {
            "name": "New Item",
            "description": "Delicious new item",
            "price": 9.99,
            "category_id": sample_category.id,
            "preparation_time": 15,
            "dietary": "vegan"
        }
        response = client.post("/api/v1/menu-items/", json=item_data)
        assert response.status_code == 201
        item = response.json()
        assert item["name"] == "New Item"
        assert item["price"] == 9.99
    
    def test_update_menu_item(self, client: TestClient, sample_menu_item: MenuItem):
        update_data = {
            "price": 4.99,
            "is_available": False
        }
        response = client.put(f"/api/v1/menu-items/{sample_menu_item.id}", json=update_data)
        assert response.status_code == 200
        item = response.json()
        assert item["price"] == 4.99
        assert item["is_available"] is False
    
    def test_delete_menu_item(self, client: TestClient, db_session: Session, sample_category: Category):
        item = MenuItem(
            name="To Delete",
            price=1.00,
            category_id=sample_category.id
        )
        db_session.add(item)
        db_session.commit()
        
        response = client.delete(f"/api/v1/menu-items/{item.id}")
        assert response.status_code == 200
        assert "unavailable" in response.json()["message"].lower()

class TestOrdersRouter:
    def test_get_orders(self, client: TestClient, sample_order: Order):
        response = client.get("/api/v1/orders/")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 1
        assert any(o["id"] == sample_order.id for o in orders)
    
    def test_get_orders_with_filters(self, client: TestClient, sample_order: Order, sample_guest: Guest):
        # Filter by guest_id
        response = client.get(f"/api/v1/orders?guest_id={sample_guest.id}")
        assert response.status_code == 200
        orders = response.json()
        assert all(o["guest_id"] == sample_guest.id for o in orders)
        
        # Filter by status
        response = client.get(f"/api/v1/orders?status=PENDING")
        assert response.status_code == 200
        orders = response.json()
        assert all(o["status"] == "PENDING" for o in orders)
    
    def test_get_guest_orders(self, client: TestClient, sample_order: Order, sample_guest: Guest):
        response = client.get(f"/api/v1/orders/guest/{sample_guest.id}")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 1
        assert all(o["guest_id"] == sample_guest.id for o in orders)
    
    def test_get_guest_orders_not_found(self, client: TestClient):
        response = client.get("/api/v1/orders/guest/nonexistent")
        assert response.status_code == 404
    
    def test_get_order_by_id(self, client: TestClient, sample_order: Order):
        response = client.get(f"/api/v1/orders/{sample_order.id}")
        assert response.status_code == 200
        order = response.json()
        assert order["id"] == sample_order.id
        assert order["total_amount"] == sample_order.total_amount
    
    def test_create_order(self, client: TestClient, sample_guest: Guest, sample_menu_item: MenuItem):
        order_data = {
            "guest_id": sample_guest.id,
            "special_requests": "Extra napkins",
            "delivery_notes": "Room 101",
            "order_items": [
                {
                    "menu_item_id": sample_menu_item.id,
                    "quantity": 2,
                    "special_notes": "No ice"
                }
            ]
        }
        response = client.post("/api/v1/orders/", json=order_data)
        assert response.status_code == 201
        order = response.json()
        assert order["guest_id"] == sample_guest.id
        assert order["total_amount"] == sample_menu_item.price * 2
        assert len(order["order_items"]) == 1
    
    def test_create_order_invalid_guest(self, client: TestClient, sample_menu_item: MenuItem):
        order_data = {
            "guest_id": "nonexistent",
            "order_items": [
                {
                    "menu_item_id": sample_menu_item.id,
                    "quantity": 1
                }
            ]
        }
        response = client.post("/api/v1/orders/", json=order_data)
        assert response.status_code == 400
        assert "Guest not found" in response.json()["detail"]
    
    def test_create_order_unavailable_item(self, client: TestClient, sample_guest: Guest, sample_menu_item: MenuItem, db_session: Session):
        # Make item unavailable
        sample_menu_item.is_available = False
        db_session.commit()
        
        order_data = {
            "guest_id": sample_guest.id,
            "order_items": [
                {
                    "menu_item_id": sample_menu_item.id,
                    "quantity": 1
                }
            ]
        }
        response = client.post("/api/v1/orders/", json=order_data)
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]
    
    def test_update_order(self, client: TestClient, sample_order: Order):
        update_data = {
            "status": "CONFIRMED",
            "payment_status": "PAID",
            "payment_method": "credit_card"
        }
        response = client.put(f"/api/v1/orders/{sample_order.id}", json=update_data)
        assert response.status_code == 200
        order = response.json()
        assert order["status"] == "CONFIRMED"
        assert order["payment_status"] == "PAID"
    
    def test_update_order_status(self, client: TestClient, sample_order: Order):
        response = client.patch(
            f"/api/v1/orders/{sample_order.id}/status/",
            json="DELIVERED"  # Send as JSON string
        )
        assert response.status_code == 200
        assert "DELIVERED" in response.json()["message"]
    
    def test_delete_order(self, client: TestClient, sample_order: Order):
        response = client.delete(f"/api/v1/orders/{sample_order.id}")
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

class TestVoiceSessionsRouter:
    def test_get_voice_sessions(self, client: TestClient, db_session: Session):
        # Create a voice session
        from app.models import VoiceSession, SessionStatus
        session = VoiceSession(
            session_id="test_session_001",
            room_number="101",
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        db_session.commit()
        
        response = client.get("/api/v1/voice-sessions/")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 1
        assert any(s["session_id"] == "test_session_001" for s in sessions)
    
    def test_create_voice_session(self, client: TestClient, sample_guest: Guest):
        session_data = {
            "guest_id": sample_guest.id,
            "room_number": "101",
            "session_id": "new_session_001"
        }
        response = client.post("/api/v1/voice-sessions/", json=session_data)
        assert response.status_code == 201
        session = response.json()
        assert session["session_id"] == "new_session_001"
        assert session["room_number"] == "101"
    
    def test_update_voice_session(self, client: TestClient, db_session: Session):
        from app.models import VoiceSession, SessionStatus
        session = VoiceSession(
            session_id="update_session_001",
            room_number="101"
        )
        db_session.add(session)
        db_session.commit()
        
        update_data = {
            "transcript": "Order completed",
            "status": "COMPLETED"
        }
        response = client.put(f"/api/v1/voice-sessions/{session.id}", json=update_data)
        assert response.status_code == 200
        updated = response.json()
        assert updated["transcript"] == "Order completed"
        assert updated["status"] == "COMPLETED"

class TestMainApp:
    def test_root_endpoint(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "active"
    
    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "hotel-voice-ai-concierge"
    
    def test_cors_headers(self, client: TestClient):
        response = client.options("/api/v1/guests/")
        assert response.status_code == 200
        # CORS headers should be present
        headers = response.headers
        assert "access-control-allow-origin" in headers or "Access-Control-Allow-Origin" in headers