// API Response types based on the backend API reference

export interface Guest {
  id: string
  name: string
  email: string
  phone_number?: string
  room_number: string
  check_in_date: string
  check_out_date?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Category {
  id: string
  name: string
  description?: string
  is_active: boolean
  display_order: number
  created_at: string
  updated_at: string
}

export interface MenuItem {
  id: string
  name: string
  description?: string
  price: number
  category_id: string
  is_available: boolean
  preparation_time: number
  dietary?: string
  image_url?: string
  created_at: string
  updated_at: string
}

export interface OrderItem {
  id: string
  order_id: string
  menu_item_id: string
  quantity: number
  unit_price: number
  total_price: number
  special_notes?: string
  created_at: string
  updated_at: string
}

export type OrderStatus = 
  | 'PENDING'
  | 'CONFIRMED' 
  | 'PREPARING'
  | 'READY'
  | 'DELIVERED'
  | 'CANCELLED'

export type PaymentStatus = 
  | 'PENDING'
  | 'PAID'
  | 'FAILED'
  | 'REFUNDED'

export interface Order {
  id: string
  guest_id: string
  status: OrderStatus
  total_amount: number
  special_requests?: string
  delivery_notes?: string
  estimated_delivery_time?: string
  actual_delivery_time?: string
  payment_status: PaymentStatus
  payment_method?: string
  order_items: OrderItem[]
  created_at: string
  updated_at: string
}

export type SessionStatus = 
  | 'ACTIVE'
  | 'COMPLETED'
  | 'ABANDONED'
  | 'ERROR'

export interface VoiceSession {
  id: string
  guest_id: string
  room_number: string
  session_id: string
  start_time: string
  end_time?: string
  transcript?: string
  audio_url?: string
  order_id?: string
  status: SessionStatus
  created_at: string
  updated_at: string
}

// Frontend-only types for UI state management

export interface CartItem {
  menu_item_id: string
  menu_item: MenuItem
  quantity: number
  special_notes?: string
}

export interface Cart {
  items: CartItem[]
  total: number
  guest_id?: string
}

export interface TranscriptMessage {
  id: string
  speaker: 'Guest' | 'AI'
  text: string
  timestamp: Date
}

export interface CallState {
  isConnected: boolean
  isJoining: boolean
  hasError: boolean
  errorMessage?: string
  participants: unknown[]
  localParticipant?: unknown
}

// API Request types

export interface CreateOrderRequest {
  guest_id: string
  special_requests?: string
  delivery_notes?: string
  order_items: {
    menu_item_id: string
    quantity: number
    special_notes?: string
  }[]
}

export interface CreateGuestRequest {
  name: string
  email: string
  phone_number?: string
  room_number: string
  check_in_date: string
  check_out_date?: string
  is_active?: boolean
}

export interface UpdateOrderStatusRequest {
  status: OrderStatus
}

export interface CreateVoiceSessionRequest {
  guest_id: string
  room_number: string
  session_id: string
}

// Error types

export interface ApiError {
  detail: string
  status?: number
}

export interface ApiResponse<T = unknown> {
  data?: T
  error?: ApiError
  loading: boolean
}
