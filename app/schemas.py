from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERROR = "ERROR"

# Guest schemas
class GuestBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    room_number: str
    check_in_date: datetime
    check_out_date: Optional[datetime] = None
    is_active: bool = True

class GuestCreate(GuestBase):
    pass

class GuestUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    room_number: Optional[str] = None
    check_out_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class Guest(GuestBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Category schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class Category(CategoryBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# MenuItem schemas
class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category_id: str
    is_available: bool = True
    preparation_time: int = 15
    dietary: List[str] = []
    image_url: Optional[str] = None

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category_id: Optional[str] = None
    is_available: Optional[bool] = None
    preparation_time: Optional[int] = None
    dietary: Optional[List[str]] = None
    image_url: Optional[str] = None

class MenuItem(MenuItemBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# OrderItem schemas
class OrderItemBase(BaseModel):
    menu_item_id: str
    quantity: int = 1
    unit_price: Decimal
    total_price: Decimal
    special_notes: Optional[str] = None

class OrderItemCreate(BaseModel):
    menu_item_id: str
    quantity: int = 1
    special_notes: Optional[str] = None

class OrderItem(OrderItemBase):
    id: str
    order_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Order schemas
class OrderBase(BaseModel):
    guest_id: str
    status: OrderStatus = OrderStatus.PENDING
    total_amount: Decimal
    special_requests: Optional[str] = None
    delivery_notes: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[str] = None

class OrderCreate(BaseModel):
    guest_id: str
    special_requests: Optional[str] = None
    delivery_notes: Optional[str] = None
    order_items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    special_requests: Optional[str] = None
    delivery_notes: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    payment_status: Optional[PaymentStatus] = None
    payment_method: Optional[str] = None

class Order(OrderBase):
    id: str
    order_items: List[OrderItem]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# VoiceSession schemas
class VoiceSessionBase(BaseModel):
    guest_id: Optional[str] = None
    room_number: Optional[str] = None
    session_id: str
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    order_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE

class VoiceSessionCreate(BaseModel):
    guest_id: Optional[str] = None
    room_number: Optional[str] = None
    session_id: str

class VoiceSessionUpdate(BaseModel):
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    order_id: Optional[str] = None
    status: Optional[SessionStatus] = None
    end_time: Optional[datetime] = None

class VoiceSession(VoiceSessionBase):
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True