from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas import Guest, GuestCreate, GuestUpdate
from ..models import Guest as GuestModel

router = APIRouter()

@router.get("/", response_model=List[Guest])
def get_guests(
    skip: int = 0,
    limit: int = 100,
    room_number: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all guests with optional filtering."""
    query = db.query(GuestModel)
    
    if room_number:
        query = query.filter(GuestModel.room_number == room_number)
    if is_active is not None:
        query = query.filter(GuestModel.is_active == is_active)
    
    guests = query.offset(skip).limit(limit).all()
    return guests

@router.get("/{guest_id}", response_model=Guest)
def get_guest(guest_id: str, db: Session = Depends(get_db)):
    """Get a specific guest by ID."""
    guest = db.query(GuestModel).filter(GuestModel.id == guest_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest not found"
        )
    return guest

@router.post("/", response_model=Guest, status_code=status.HTTP_201_CREATED)
def create_guest(guest: GuestCreate, db: Session = Depends(get_db)):
    """Create a new guest."""
    # Check if guest with same email already exists
    existing_guest = db.query(GuestModel).filter(GuestModel.email == guest.email).first()
    if existing_guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest with this email already exists"
        )
    
    db_guest = GuestModel(**guest.model_dump())
    db.add(db_guest)
    db.commit()
    db.refresh(db_guest)
    return db_guest

@router.put("/{guest_id}", response_model=Guest)
def update_guest(guest_id: str, guest: GuestUpdate, db: Session = Depends(get_db)):
    """Update a guest."""
    db_guest = db.query(GuestModel).filter(GuestModel.id == guest_id).first()
    if not db_guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest not found"
        )
    
    update_data = guest.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_guest, field, value)
    
    db.commit()
    db.refresh(db_guest)
    return db_guest

@router.delete("/{guest_id}")
def delete_guest(guest_id: str, db: Session = Depends(get_db)):
    """Delete a guest."""
    db_guest = db.query(GuestModel).filter(GuestModel.id == guest_id).first()
    if not db_guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest not found"
        )
    
    db.delete(db_guest)
    db.commit()
    return {"message": "Guest deleted successfully"}