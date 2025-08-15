# Hotel Voice AI Concierge - Simple Frontend

A minimalistic frontend for the Hotel Voice AI Concierge system.

## Features

- Video call interface for voice ordering
- Menu display with items from the backend API
- Order management (add/remove items, clear order)
- Order placement with confirmation

## Setup

1. Make sure the backend API is running on `http://localhost:8000`
2. Serve the frontend files using any static file server

## Running the Frontend

You can use Python's built-in HTTP server:

```bash
cd simple-frontend
python -m http.server 8080
```

Then open your browser to http://localhost:8080

## Usage

1. Click "Start Voice Call" to initiate a voice session
2. Browse the menu items loaded from the backend
3. Click "Add to Order" on any menu item to add it to your order
4. View your order summary and total
5. Click "Place Order" to submit your order to the backend
6. Use "Clear Order" to reset your current order

## API Endpoints Used

- `GET http://localhost:8000/api/v1/menu-items/` - Load menu items
- `POST http://localhost:8000/api/v1/voice-sessions/start-call?room_number=101` - Start voice call
- `POST http://localhost:8000/api/v1/orders/` - Place order

## Technologies

- HTML5/CSS3
- JavaScript (Vanilla)
- Tailwind CSS with daisyUI components
- Daily.co JavaScript SDK (for video calling)