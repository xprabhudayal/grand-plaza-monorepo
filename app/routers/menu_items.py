from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas import MenuItem, MenuItemCreate, MenuItemUpdate
from ..models import MenuItem as MenuItemModel, Category as CategoryModel

router = APIRouter()

@router.get("/", response_model=List[MenuItem])
def get_menu_items(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[str] = None,
    is_available: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all menu items with optional filtering."""
    query = db.query(MenuItemModel)
    
    if category_id:
        query = query.filter(MenuItemModel.category_id == category_id)
    if is_available is not None:
        query = query.filter(MenuItemModel.is_available == is_available)
    
    menu_items = query.offset(skip).limit(limit).all()
    return menu_items

@router.get("/by-category/{category_id}", response_model=List[MenuItem])
def get_menu_items_by_category(category_id: str, db: Session = Depends(get_db)):
    """Get all menu items for a specific category."""
    # Verify category exists
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    menu_items = db.query(MenuItemModel).filter(
        MenuItemModel.category_id == category_id,
        MenuItemModel.is_available == True
    ).all()
    return menu_items

@router.get("/{menu_item_id}", response_model=MenuItem)
def get_menu_item(menu_item_id: str, db: Session = Depends(get_db)):
    """Get a specific menu item by ID."""
    menu_item = db.query(MenuItemModel).filter(MenuItemModel.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    return menu_item

@router.post("/", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
def create_menu_item(menu_item: MenuItemCreate, db: Session = Depends(get_db)):
    """Create a new menu item."""
    # Verify category exists
    category = db.query(CategoryModel).filter(CategoryModel.id == menu_item.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )
    
    db_menu_item = MenuItemModel(**menu_item.model_dump())
    db.add(db_menu_item)
    db.commit()
    db.refresh(db_menu_item)
    return db_menu_item

@router.put("/{menu_item_id}", response_model=MenuItem)
def update_menu_item(menu_item_id: str, menu_item: MenuItemUpdate, db: Session = Depends(get_db)):
    """Update a menu item."""
    db_menu_item = db.query(MenuItemModel).filter(MenuItemModel.id == menu_item_id).first()
    if not db_menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    # If category_id is being updated, verify new category exists
    if menu_item.category_id:
        category = db.query(CategoryModel).filter(CategoryModel.id == menu_item.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    update_data = menu_item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_menu_item, field, value)
    
    db.commit()
    db.refresh(db_menu_item)
    return db_menu_item

@router.delete("/{menu_item_id}")
def delete_menu_item(menu_item_id: str, db: Session = Depends(get_db)):
    """Delete a menu item."""
    db_menu_item = db.query(MenuItemModel).filter(MenuItemModel.id == menu_item_id).first()
    if not db_menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    db.delete(db_menu_item)
    db.commit()
    return {"message": "Menu item deleted successfully"}