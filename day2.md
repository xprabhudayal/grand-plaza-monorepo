# Day 2: Frontend Development & Full Integration

## Overview
Day 2 focuses on building the React/Next.js frontend, integrating Daily.co WebRTC, Tavus AI avatar, and creating a complete end-to-end hotel room service experience. By end of day, you'll have a fully functional hotel AI concierge system.

## Core Tasks

### 1. Frontend Foundation (2-3 hours)
- **Next.js Project Setup**: Initialize React application with Tailwind CSS
  - Configure pages/index.js for guest interface
  - Create pages/admin.js for hotel staff dashboard
  - Setup Tailwind CSS with hotel branding colors
  - Configure environment variables for API connections

- **Core Components Creation**:
  ```javascript
  components/VideoAvatar.js      // Daily.co integration with Tavus avatar
  components/TranscriptionView.js // Live conversation display
  components/OrderSummaryCard.js  // Current order status
  components/AdminDashboard.js    // Staff order management
  components/MenuDisplay.js       // Visual menu for reference
  ```

### 2. Daily.co WebRTC Integration (2-3 hours)
- **Video Call Setup**: Implement @daily-co/daily-js integration
  - Create Daily room on component mount
  - Join room as participant
  - Configure audio/video settings for guest interaction
  - Handle participant events and connection status

- **Tavus Avatar Integration**: Connect AI avatar to video stream
  - Configure Tavus avatar service connection
  - Stream avatar video through Daily.co room
  - Sync avatar animations with TTS output
  - Handle avatar loading and error states

### 3. Real-time Features (2 hours)
- **Live Transcription Display**: Show conversation in real-time
  - Capture and display STT output
  - Show guest speech and AI responses
  - Auto-scroll and conversation history
  - Visual indicators for speech activity

- **Order Status Updates**: Real-time order tracking
  - Display current items being discussed
  - Show order total and pricing
  - Visual confirmation when order is placed
  - Reference ID display for guest

### 4. Admin Dashboard (1-2 hours)
- **Order Management Interface**: Hotel staff dashboard
  - List all orders with timestamps
  - Filter by room number, status, time range
  - Order details view with guest information
  - Basic authentication implementation
  - Export functionality for kitchen/housekeeping

### 5. Backend API Integration (1-2 hours)
- **API Client Setup**: Connect frontend to FastAPI backend
  - Fetch menu data for display
  - Submit orders from voice pipeline
  - Retrieve order history for admin
  - Error handling and loading states

- **Data Flow Integration**: Complete voice-to-database pipeline
  - Voice input → Pipecat processing → Order creation → Database storage → Admin display
  - Real-time updates between voice pipeline and frontend
  - Webhook handling for order status changes

### 6. Styling & UX Polish (1-2 hours)
- **Hotel Branding**: Professional hotel interface design
  - Clean, modern design suitable for hotel tablets
  - Accessible font sizes and contrast
  - Responsive design for different screen sizes
  - Loading animations and smooth transitions

- **User Experience Optimization**:
  - Clear call-to-action buttons
  - Visual feedback for all interactions
  - Error state handling and user messaging
  - Intuitive navigation between states

### 7. Deployment & Testing (1-2 hours)
- **Vercel Deployment**: Deploy frontend application
  - Configure environment variables
  - Test production build and deployment
  - Verify API connectivity from deployed frontend

- **Railway Backend Deployment**: Deploy complete backend
  - Configure production environment
  - Test database persistence
  - Verify all API endpoints in production

- **End-to-End Testing**: Complete system validation
  - Test full conversation flow from start to finish
  - Verify order placement and admin dashboard updates
  - Test error scenarios and edge cases
  - Performance testing under load

## Key Files to Create

### Frontend Files
- `pages/index.js` - Main guest interface with video call
- `pages/admin.js` - Hotel staff dashboard
- `components/VideoAvatar.js` - Daily.co + Tavus integration
- `components/TranscriptionView.js` - Live conversation display
- `components/OrderSummaryCard.js` - Order tracking component
- `components/AdminDashboard.js` - Staff order management
- `components/MenuDisplay.js` - Visual menu reference
- `styles/globals.css` - Tailwind configuration and hotel branding
- `lib/dailyClient.js` - Daily.co service configuration
- `lib/apiClient.js` - Backend API integration
- `package.json` - Dependencies and scripts

### Integration Files
- `utils/orderUtils.js` - Order processing helpers
- `hooks/useDaily.js` - Custom hook for Daily.co management
- `hooks/useOrders.js` - Custom hook for order data management

## Expected Deliverables
- ✅ Complete React/Next.js frontend application
- ✅ Working Daily.co WebRTC video call integration
- ✅ Tavus AI avatar streaming in video call
- ✅ Live transcription and conversation display
- ✅ Admin dashboard for hotel staff
- ✅ Full backend API integration
- ✅ Production deployment on Vercel and Railway
- ✅ End-to-end tested system

## Success Criteria
- Guest can initiate video call and see AI avatar
- Voice conversation flows naturally through complete ordering process
- Orders appear in real-time on admin dashboard
- System handles multiple concurrent users
- All components responsive and professional appearance
- Production deployment stable and accessible

## Technical Integration Points
- Frontend connects to Daily.co room created by backend
- Pipecat pipeline sends order data to FastAPI endpoints
- Admin dashboard polls for new orders via REST API
- Real-time updates through WebSocket or polling
- Tavus avatar synchronized with Pipecat TTS output

## Performance Considerations
- Optimize video streaming quality for hotel WiFi
- Minimize API calls with efficient caching
- Lazy load components for faster initial render
- Implement proper error boundaries and fallbacks
- Monitor and optimize bundle size for mobile devices