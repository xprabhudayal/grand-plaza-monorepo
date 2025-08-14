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

#### GET /api/v1/guests
Get all guests with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `room_number` (string, optional): Filter by room number
- `is_active` (boolean, optional): Filter by active status

**Example Request:**
```bash
GET /api/v1/guests?room_number=101&is_active=true
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

#### POST /api/v1/guests
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

#### GET /api/v1/categories
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

#### POST /api/v1/categories
Create a new category.

#### PUT /api/v1/categories/{category_id}
Update an existing category.

#### DELETE /api/v1/categories/{category_id}
Delete a category.

---

### 3. Menu Items Management

#### GET /api/v1/menu-items
Get all menu items with optional filtering.

**Parameters:**
- `skip` (int, optional): Number of records to skip
- `limit` (int, optional): Maximum number of records to return
- `category_id` (string, optional): Filter by category ID
- `is_available` (boolean, optional): Filter by availability

**Example Request:**
```bash
GET /api/v1/menu-items?category_id=cat_appetizers_001&is_available=true
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

#### POST /api/v1/menu-items
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

#### GET /api/v1/orders
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

#### POST /api/v1/orders
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

#### GET /api/v1/voice-sessions
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

#### POST /api/v1/voice-sessions
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

## Voice Pipeline Integration

### Overview

The voice pipeline is built using Pipecat and integrates with the REST API to handle voice-based room service orders. The system uses:

- **Speech-to-Text:** Deepgram or Soniox
- **Text-to-Speech:** Cartesia
- **LLM:** Groq or OpenAI/Perplexity
- **Transport:** Daily.co

### Voice Pipeline Flow

1. **Greeting:** Welcome the guest and offer menu browsing or search
2. **Menu Navigation:** Browse categories or search for items
3. **Order Building:** Add items with quantities and special notes
4. **Order Review:** Confirm order details and total
5. **Order Placement:** Save order to database via API
6. **Confirmation:** Provide order confirmation and estimated delivery time

### Voice Functions

The voice pipeline implements several functions that are called by the LLM:

#### Menu Functions
- `browse_menu()` - Start browsing menu categories
- `search_items(query: str)` - Search for menu items
- `select_category(category_name: str)` - Browse items in a category

#### Order Functions
- `add_item_to_order(item_name: str, quantity: Union[str, int] = 1, special_notes: str = None)` - Add item to order
- `review_current_order()` - Review current order items
- `confirm_final_order()` - Place the order
- `modify_order()` - Make changes to order
- `cancel_order()` - Cancel the entire order

### Text-to-Number Conversion

The system includes a utility to convert spoken numbers to integers:
- "one" → 1
- "two" → 2
- "twenty-one" → 21
- "a" or "an" → 1

### Menu Data Structure

The hotel menu contains 7 categories:
1. **Breakfast** - Available 24/7
2. **Appetizers** - Light bites
3. **Salads** - Fresh options
4. **Main Courses** - Hearty entrees
5. **Sandwiches** - Gourmet options
6. **Desserts** - Sweet treats
7. **Beverages** - Hot & cold drinks

Each menu item includes:
- Name and description
- Price
- Preparation time
- Dietary information (vegetarian, vegan, gluten-free)
- Availability status

---

## Frontend Integration Guide

### Essential Data Models

#### Guest Model
```typescript
interface Guest {
  id: string;
  name: string;
  email: string;
  phone_number?: string;
  room_number: string;
  check_in_date: string;
  check_out_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

#### MenuItem Model
```typescript
interface MenuItem {
  id: string;
  name: string;
  description?: string;
  price: number;
  category_id: string;
  is_available: boolean;
  preparation_time: number;
  dietary?: string;
  image_url?: string;
  created_at: string;
  updated_at: string;
}
```

#### Order Model
```typescript
interface Order {
  id: string;
  guest_id: string;
  status: 'PENDING' | 'CONFIRMED' | 'PREPARING' | 'READY' | 'DELIVERED' | 'CANCELLED';
  total_amount: number;
  special_requests?: string;
  delivery_notes?: string;
  estimated_delivery_time?: string;
  actual_delivery_time?: string;
  payment_status: 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';
  payment_method?: string;
  order_items: OrderItem[];
  created_at: string;
  updated_at: string;
}

interface OrderItem {
  id: string;
  order_id: string;
  menu_item_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  special_notes?: string;
  created_at: string;
  updated_at: string;
}
```

### Common API Call Patterns

#### 1. Fetching Menu Items
```javascript
// Get all available menu items
const fetchMenuItems = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/menu-items?is_available=true`);
    if (!response.ok) throw new Error('Failed to fetch menu items');
    return await response.json();
  } catch (error) {
    console.error('Error fetching menu items:', error);
    throw error;
  }
};

// Get menu items by category
const fetchMenuItemsByCategory = async (categoryId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/menu-items/by-category/${categoryId}`);
    if (!response.ok) throw new Error('Failed to fetch menu items');
    return await response.json();
  } catch (error) {
    console.error('Error fetching menu items by category:', error);
    throw error;
  }
};
```

#### 2. Creating Orders
```javascript
const createOrder = async (orderData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderData)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to create order');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error creating order:', error);
    throw error;
  }
};

// Example usage
const orderData = {
  guest_id: "guest_123",
  special_requests: "Extra napkins",
  delivery_notes: "Ring doorbell twice",
  order_items: [
    {
      menu_item_id: "menu_001",
      quantity: 2,
      special_notes: "No croutons"
    }
  ]
};
```

#### 3. Guest Management
```javascript
// Find guest by room number
const findGuestByRoom = async (roomNumber) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/guests/room/${roomNumber}`);
    if (!response.ok) {
      if (response.status === 404) {
        return null; // No active guest in room
      }
      throw new Error('Failed to fetch guest');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching guest by room:', error);
    throw error;
  }
};
```

#### 4. Real-time Order Updates
```javascript
// Poll for order status updates
const pollOrderStatus = async (orderId, callback) => {
  const poll = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}`);
      if (response.ok) {
        const order = await response.json();
        callback(order);
      }
    } catch (error) {
      console.error('Error polling order status:', error);
    }
  };
  
  const intervalId = setInterval(poll, 30000); // Poll every 30 seconds
  return () => clearInterval(intervalId); // Return cleanup function
};
```

### Error Handling

All API endpoints return standard HTTP status codes and error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

**Common Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

### CORS Configuration

The API is configured with permissive CORS settings for development:
- **Allowed Origins:** `*` (all origins)
- **Allowed Methods:** `*` (all methods)
- **Allowed Headers:** `*` (all headers)
- **Credentials:** Enabled

**⚠️ Production Note:** In production, configure specific allowed origins instead of `*`.

### Environment Variables

Frontend applications should configure these environment variables:

```bash
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_API_VERSION=v1

# Daily.co Configuration (for voice integration)
REACT_APP_DAILY_DOMAIN=your-daily-domain.daily.co
REACT_APP_DAILY_API_KEY=your-daily-api-key

# Optional: Enable API request logging
REACT_APP_DEBUG_API=true
```

### Best Practices

1. **Always handle errors gracefully** - API calls can fail due to network issues or server errors
2. **Implement loading states** - Show loading indicators during API calls
3. **Cache menu data** - Menu items change infrequently, consider caching
4. **Validate input client-side** - Reduce server round-trips by validating required fields
5. **Use TypeScript** - Leverage the provided type definitions for better development experience
6. **Implement retry logic** - For critical operations like order creation
7. **Show user-friendly error messages** - Convert API error messages to user-friendly text

### Sample API Client Setup

```javascript
class HotelAPIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Guest methods
  async getGuests(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/api/v1/guests?${queryString}`);
  }

  async getGuestByRoom(roomNumber) {
    return this.request(`/api/v1/guests/room/${roomNumber}`);
  }

  // Menu methods
  async getMenuItems(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/api/v1/menu-items?${queryString}`);
  }

  async getCategories() {
    return this.request('/api/v1/categories?is_active=true');
  }

  // Order methods
  async createOrder(orderData) {
    return this.request('/api/v1/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }

  async getOrder(orderId) {
    return this.request(`/api/v1/orders/${orderId}`);
  }

  async updateOrderStatus(orderId, status) {
    return this.request(`/api/v1/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }
}

// Usage
const apiClient = new HotelAPIClient('http://localhost:8000');
export default apiClient;
```

---

## Rate Limiting

Currently, there are no rate limits implemented. Future versions may include rate limiting for production use.

## Versioning

The API uses URL versioning with the `/api/v1/` prefix. Future API versions will use `/api/v2/`, etc.

## Support

For API support or questions, please refer to the project documentation or contact the development team.