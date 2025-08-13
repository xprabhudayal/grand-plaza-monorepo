# Hotel AI Concierge Frontend

A modern, responsive frontend for the Hotel Room Service AI Concierge application built with Next.js, React, and Tailwind CSS.

## Features

- **Guest Interface**: Interactive video call interface with AI avatar for room service ordering
- **Admin Dashboard**: Real-time order management and monitoring for hotel staff
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Real-time Updates**: Live order status updates and conversation transcription
- **Video Integration**: Daily.co WebRTC integration for seamless video calls

## Tech Stack

- **Frontend Framework**: Next.js 15 with TypeScript
- **Styling**: Tailwind CSS with custom hotel theme
- **State Management**: React Hooks and Context
- **Video Calls**: Daily.co SDK (@daily-co/daily-js)
- **HTTP Client**: Axios for API communication
- **Icons**: Heroicons and Lucide React
- **Package Manager**: Bun

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Access to the backend API (running on port 8000)
- Daily.co account and room URL

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   bun install
   ```

3. Copy environment variables:
   ```bash
   cp .env.local.example .env.local
   ```

4. Update environment variables in `.env.local`:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   NEXT_PUBLIC_DAILY_DOMAIN=your-daily-domain.daily.co
   NEXT_PUBLIC_DAILY_ROOM_URL=https://your-daily-domain.daily.co/room-name
   NEXT_PUBLIC_HOTEL_NAME=Your Hotel Name
   ```

### Development

Start the development server:
```bash
bun run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Build for Production

```bash
bun run build
bun start
```

## Project Structure

```
src/
├── app/                    # Next.js app router pages
│   ├── admin/             # Admin dashboard page
│   ├── globals.css        # Global styles and Tailwind
│   ├── layout.tsx         # Root layout component
│   └── page.tsx           # Guest interface (home page)
├── components/            # Reusable React components
│   ├── AdminDashboard.tsx # Admin order management interface
│   ├── MenuDisplay.tsx    # Interactive menu component
│   ├── OrderSummaryCard.tsx # Order details and cart display
│   ├── TranscriptionView.tsx # Conversation chat interface
│   └── VideoAvatar.tsx    # Daily.co video call component
├── hooks/                 # Custom React hooks
│   ├── useCart.ts         # Shopping cart state management
│   ├── useDaily.ts        # Daily.co video call integration
│   ├── useMenu.ts         # Menu data fetching
│   └── useOrders.ts       # Order management and polling
├── lib/                   # Utility libraries
│   ├── apiClient.ts       # HTTP client for backend API
│   └── utils.ts           # Helper functions and utilities
└── types/                 # TypeScript type definitions
    └── index.ts           # API and component type definitions
```

## Key Components

### Guest Interface (`/`)

The main guest-facing interface featuring:
- **Video Avatar**: AI concierge video call interface
- **Menu Display**: Interactive menu browser with categories
- **Conversation View**: Real-time chat transcription
- **Order Summary**: Shopping cart and order tracking

### Admin Dashboard (`/admin`)

Hotel staff interface featuring:
- **Order Management**: Real-time order monitoring and status updates
- **Search & Filtering**: Advanced order search and filtering options
- **Statistics Dashboard**: Order volume and revenue metrics
- **Authentication**: Simple login system (demo credentials: admin/hotel123)

### Video Integration

The `VideoAvatar` component integrates with Daily.co for video calls:
- Automatic room joining and participant management
- Audio/video controls (mute, camera toggle)
- Error handling and connection status
- Mock conversation simulation for demo purposes

## API Integration

The frontend communicates with the backend API through:
- **REST API**: Full CRUD operations for guests, orders, menu items
- **Real-time Polling**: Order status updates every 15-30 seconds
- **Error Handling**: Comprehensive error handling with user feedback

### Key API Endpoints

- `GET /api/v1/menu-items` - Fetch menu items
- `GET /api/v1/categories` - Fetch menu categories
- `POST /api/v1/orders` - Create new orders
- `GET /api/v1/orders` - List orders (admin)
- `PATCH /api/v1/orders/{id}/status` - Update order status

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_DAILY_DOMAIN` | Daily.co domain | - |
| `NEXT_PUBLIC_DAILY_ROOM_URL` | Daily.co room URL | - |
| `NEXT_PUBLIC_HOTEL_NAME` | Hotel brand name | `Grand Plaza Hotel` |

## Development

Start the development server:
```bash
bun run dev
```

## Deployment

Build for production:
```bash
bun run build
bun start
```
