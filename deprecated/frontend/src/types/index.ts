export interface MenuItem {
  id: string;
  name: string;
  description?: string;
  price: number;
  category_id: string;
  is_available: boolean;
  dietary?: string;
  preparation_time: number;
  image_url?: string;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  menu_item_id: string;
  menu_item: MenuItem;
  quantity: number;
}

export interface Cart {
  items: CartItem[];
  total: number;
}

export interface TranscriptMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Guest {
  id: string;
  name: string;
  email?: string;
  phone_number?: string;
  room_number: string;
  check_in_date: string;
  check_out_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
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

export interface Order {
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