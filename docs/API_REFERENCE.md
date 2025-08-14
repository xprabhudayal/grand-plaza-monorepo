# Hotel Voice AI Concierge - API Reference

## Overview

This document provides comprehensive API documentation for the Hotel Voice AI Concierge system. The API is built using FastAPI and provides endpoints for managing guests, menu items, orders, and voice sessions for a hotel room service system.

**Base URL:** `http://localhost:8000/api/v1`  
**API Version:** 1.0.0  
**Content-Type:** `application/json`

## Authentication

Currently, the API does not require authentication for most endpoints. Future versions may implement JWT-based authentication.

---

## API Endpoints

### 1. Guests Management

#### GET /api/v1/guests/
Get all guests with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `room_number` (string, optional): Filter by room number
- `is_active` (boolean, optional): Filter by active status

**Example Request:**
```bash
GET /api/v1/guests/?room_number=101&is_active=true
```

**Example Response:**
```json
[
  {
    "id": "cljd8f7gh000008l2a3b4c5d6",
    "name": "John Doe",
    "email": "john.doe@email.com",
    "phone_number": "+1234567890",
    "room_number": "101",
    "check_in_date": "2025-08-13T15:00:00Z",
    "check_out_date": "2025-08-15T11:00:00Z",
    "is_active": true,
    "created_at": "2025-08-13T14:30:00Z",
    "updated_at": "2025-08-13T14:30:00Z"
  }
]
```

#### GET /api/v1/guests/room/{room_number}
Get active guest by room number.

**Example Request:**
```bash
GET /api/v1/guests/room/101
```

#### GET /api/v1/guests/{guest_id}
Get a specific guest by ID.

#### POST /api/v1/guests/
Create a new guest.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone_number": "+1234567890",
  "room_number": "101",
  "check_in_date": "2025-08-13T15:00:00Z",
  "check_out_date": "2025-08-15T11:00:00Z",
  "is_active": true
}
```

#### PUT /api/v1/guests/{guest_id}
Update an existing guest.

#### DELETE /api/v1/guests/{guest_id}
Delete a guest.

---

### 2. Categories Management

#### GET /api/v1/categories/
Get all menu categories.

**Parameters:**
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return
- `is_active` (boolean, optional): Filter by active status

**Example Response:**
```json
[
  {
    "id": "cat_appetizers_001",
    "name": "Appetizers",
    "description": "Start your meal with our delicious appetizers",
    "is_active": true,
    "display_order": 1,
    "created_at": "2025-08-13T10:00:00Z",
    "updated_at": "2025-08-13T10:00:00Z"
  }
]
```

#### GET /api/v1/categories/{category_id}
Get a specific category by ID.

#### POST /api/v1/categories/
Create a new category.

#### PUT /api/v1/categories/{category_id}
Update an existing category.

#### DELETE /api/v1/categories/{category_id}
Delete a category.

---

### 3. Menu Items Management

#### GET /api/v1/menu-items/
Get all menu items with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return
- `category_id` (string, optional): Filter by category ID
- `is_available` (boolean, optional): Filter by availability

**Example Request:**
```bash
GET /api/v1/menu-items/?category_id=cat_appetizers_001&is_available=true
```

**Example Response:**
```json
[
  {
    "id": "menu_001",
    "name": "Caesar Salad",
    "description": "Fresh romaine lettuce with Caesar dressing, croutons, and parmesan",
    "price": 18.50,
    "category_id": "cat_appetizers_001",
    "is_available": true,
    "preparation_time": 10,
    "dietary": "vegetarian",
    "image_url": "https://example.com/caesar-salad.jpg",
    "created_at": "2025-08-13T10:00:00Z",
    "updated_at": "2025-08-13T10:00:00Z"
  }
]
```

#### GET /api/v1/menu-items/by-category/{category_id}
Get all available menu items for a specific category.

#### GET /api/v1/menu-items/{menu_item_id}
Get a specific menu item by ID.

#### POST /api/v1/menu-items/
Create a new menu item.

**Request Body:**
```json
{
  "name": "Caesar Salad",
  "description": "Fresh romaine lettuce with Caesar dressing",
  "price": 18.50,
  "category_id": "cat_appetizers_001",
  "is_available": true,
  "preparation_time": 10,
  "dietary": "vegetarian",
  "image_url": "https://example.com/caesar-salad.jpg"
}
```

#### PUT /api/v1/menu-items/{menu_item_id}
Update an existing menu item.

#### DELETE /api/v1/menu-items/{menu_item_id}
Delete a menu item.

---

### 4. Orders Management

#### GET /api/v1/orders/
Get all orders with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return
- `guest_id` (string, optional): Filter by guest ID
- `status` (OrderStatus, optional): Filter by order status

**Order Status Enum:**
- `PENDING`
- `CONFIRMED`
- `PREPARING`
- `READY`
- `DELIVERED`
- `CANCELLED`

**Example Response:**
```json
[
  {
    "id": "order_001",
    "guest_id": "guest_001",
    "status": "CONFIRMED",
    "total_amount": 45.50,
    "special_requests": "Extra napkins please",
    "delivery_notes": "Ring doorbell twice",
    "estimated_delivery_time": "2025-08-13T19:00:00Z",
    "actual_delivery_time": null,
    "payment_status": "PENDING",
    "payment_method": null,
    "order_items": [
      {
        "id": "item_001",
        "order_id": "order_001",
        "menu_item_id": "menu_001",
        "quantity": 2,
        "unit_price": 18.50,
        "total_price": 37.00,
        "special_notes": "No croutons",
        "created_at": "2025-08-13T18:00:00Z",
        "updated_at": "2025-08-13T18:00:00Z"
      }
    ],
    "created_at": "2025-08-13T18:00:00Z",
    "updated_at": "2025-08-13T18:00:00Z"
  }
]
```

#### GET /api/v1/orders/guest/{guest_id}
Get all orders for a specific guest.

#### GET /api/v1/orders/{order_id}
Get a specific order by ID.

#### POST /api/v1/orders/
Create a new order with order items.

**Request Body:**
```json
{
  "guest_id": "guest_001",
  "special_requests": "Extra napkins please",
  "delivery_notes": "Ring doorbell twice",
  "order_items": [
    {
      "menu_item_id": "menu_001",
      "quantity": 2,
      "special_notes": "No croutons"
    },
    {
      "menu_item_id": "menu_002",
      "quantity": 1,
      "special_notes": null
    }
  ]
}
```

**Response:** Returns the created order with all calculated fields (total_amount, unit_price, total_price per item).

#### PUT /api/v1/orders/{order_id}
Update an existing order.

#### PATCH /api/v1/orders/{order_id}/status
Update order status only.

**Request Body:**
```json
{
  "status": "PREPARING"
}
```

#### DELETE /api/v1/orders/{order_id}
Cancel an order (sets status to CANCELLED).

---

### 5. Voice Sessions Management

#### GET /api/v1/voice-sessions/
Get all voice sessions with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return
- `guest_id` (string, optional): Filter by guest ID
- `room_number` (string, optional): Filter by room number
- `status` (SessionStatus, optional): Filter by session status

**Session Status Enum:**
- `ACTIVE`
- `COMPLETED`
- `ABANDONED`
- `ERROR`

**Example Response:**
```json
[
  {
    "id": "session_001",
    "guest_id": "guest_001",
    "room_number": "101",
    "session_id": "daily_session_abc123",
    "start_time": "2025-08-13T18:00:00Z",
    "end_time": "2025-08-13T18:15:00Z",
    "transcript": "Hello, I'd like to order room service...",
    "audio_url": "https://recordings.daily.co/abc123.mp3",
    "order_id": "order_001",
    "status": "COMPLETED",
    "created_at": "2025-08-13T18:00:00Z",
    "updated_at": "2025-08-13T18:15:00Z"
  }
]
```

#### GET /api/v1/voice-sessions/{session_id}
Get a specific voice session by internal ID.

#### GET /api/v1/voice-sessions/by-session-id/{session_id}
Get a voice session by external session ID (Daily.co session ID).

#### POST /api/v1/voice-sessions/
Create a new voice session.

**Request Body:**
```json
{
  "guest_id": "guest_001",
  "room_number": "101",
  "session_id": "daily_session_abc123"
}
```

#### PUT /api/v1/voice-sessions/{session_id}
Update an existing voice session.

#### PATCH /api/v1/voice-sessions/{session_id}/status
Update voice session status only.

#### DELETE /api/v1/voice-sessions/{session_id}
Delete a voice session.

---

## Rate Limiting

Currently, there are no rate limits implemented. Future versions may include rate limiting for production use.

## Versioning

The API uses URL versioning with the `/api/v1/` prefix. Future API versions will use `/api/v2/`, etc.

## Support

For API support or questions, please refer to the project documentation or contact the development team.