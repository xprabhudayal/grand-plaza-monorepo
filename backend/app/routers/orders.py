from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from ..database import get_db
from ..schemas import Order, OrderCreate, OrderUpdate, OrderStatus
from ..models import Order as OrderModel, OrderItem as OrderItemModel, MenuItem as MenuItemModel, Guest as GuestModel

router = APIRouter()

@router.get("/", response_model=List[Order])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    guest_id: Optional[str] = None,
    status: Optional[OrderStatus] = None,
    db: Session = Depends(get_db)
):
    """Get all orders with optional filtering."""
    query = db.query(OrderModel)
    
    if guest_id:
        query = query.filter(OrderModel.guest_id == guest_id)
    if status:
        query = query.filter(OrderModel.status == status)
    
    orders = query.order_by(OrderModel.created_at.desc()).offset(skip).limit(limit).all()
    return orders

@router.get("/guest/{guest_id}", response_model=List[Order])
def get_guest_orders(guest_id: str, db: Session = Depends(get_db)):
    """Get all orders for a specific guest."""
    # Verify guest exists
    guest = db.query(GuestModel).filter(GuestModel.id == guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest not found"
        )
    
    orders = db.query(OrderModel).filter(OrderModel.guest_id == guest_id).order_by(OrderModel.created_at.desc()).all()
    return orders

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get a specific order by ID."""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order

@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order with order items."""
    # Verify guest exists
    guest = db.query(GuestModel).filter(GuestModel.id == order.guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest not found"
        )
    
    # Calculate total amount and create order items
    total_amount = Decimal('0.00')
    order_items_data = []
    
    for item_data in order.order_items:
        # Verify menu item exists and is available
        menu_item = db.query(MenuItemModel).filter(MenuItemModel.id == item_data.menu_item_id).first()
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item {item_data.menu_item_id} not found"
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item {menu_item.name} is not available"
            )
        
        unit_price = menu_item.price
        total_price = unit_price * item_data.quantity
        total_amount += Decimal(str(total_price))
        
        order_items_data.append({
            "menu_item_id": item_data.menu_item_id,
            "quantity": item_data.quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "special_notes": item_data.special_notes
        })
    
    # Create order
    db_order = OrderModel(
        guest_id=order.guest_id,
        total_amount=total_amount,
        special_requests=order.special_requests,
        delivery_notes=order.delivery_notes
    )
    db.add(db_order)
    db.flush()  # Get the order ID without committing
    
    # Create order items
    for item_data in order_items_data:
        db_order_item = OrderItemModel(
            order_id=db_order.id,
            **item_data
        )
        db.add(db_order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@router.put("/{order_id}", response_model=Order)
def update_order(order_id: str, order: OrderUpdate, db: Session = Depends(get_db)):
    """Update an order."""
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    update_data = order.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@router.patch("/{order_id}/status")
def update_order_status(order_id: str, status: OrderStatus, db: Session = Depends(get_db)):
    """Update order status."""
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    db_order.status = status
    db.commit()
    return {"message": f"Order status updated to {status.value}"}

@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db)):
    """Delete an order (soft delete by setting status to CANCELLED)."""
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    db_order.status = OrderStatus.CANCELLED
    db.commit()
    return {"message": "Order cancelled successfully"}