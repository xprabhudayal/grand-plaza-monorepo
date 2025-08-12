from sqlalchemy import Column, String, Text, Numeric, Boolean, Integer, DateTime, ForeignKey, Enum as SQLEnum, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

Base = declarative_base()

# Enums
class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class SessionStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERROR = "ERROR"

class Guest(Base):
    __tablename__ = "guests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String)
    room_number = Column(String, nullable=False, index=True)
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="guest")

class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = relationship("MenuItem", back_populates="category")

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=False, index=True)
    is_available = Column(Boolean, default=True, index=True)
    preparation_time = Column(Integer, default=15)
    dietary = Column(ARRAY(String), default=[])
    image_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="menu_items")
    order_items = relationship("OrderItem", back_populates="menu_item")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_id = Column(String, ForeignKey("guests.id"), nullable=False, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    special_requests = Column(Text)
    delivery_notes = Column(Text)
    estimated_delivery_time = Column(DateTime)
    actual_delivery_time = Column(DateTime)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    guest = relationship("Guest", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(String, ForeignKey("menu_items.id"), nullable=False, index=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    special_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("MenuItem", back_populates="order_items")

class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_id = Column(String, index=True)
    room_number = Column(String, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    transcript = Column(Text)
    audio_url = Column(String)
    order_id = Column(String)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)