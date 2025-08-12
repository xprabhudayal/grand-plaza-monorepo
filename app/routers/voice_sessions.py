from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas import VoiceSession, VoiceSessionCreate, VoiceSessionUpdate, SessionStatus
from ..models import VoiceSession as VoiceSessionModel

router = APIRouter()

@router.get("/", response_model=List[VoiceSession])
def get_voice_sessions(
    skip: int = 0,
    limit: int = 100,
    guest_id: Optional[str] = None,
    room_number: Optional[str] = None,
    status: Optional[SessionStatus] = None,
    db: Session = Depends(get_db)
):
    """Get all voice sessions with optional filtering."""
    query = db.query(VoiceSessionModel)
    
    if guest_id:
        query = query.filter(VoiceSessionModel.guest_id == guest_id)
    if room_number:
        query = query.filter(VoiceSessionModel.room_number == room_number)
    if status:
        query = query.filter(VoiceSessionModel.status == status)
    
    sessions = query.order_by(VoiceSessionModel.start_time.desc()).offset(skip).limit(limit).all()
    return sessions

@router.get("/{session_id}", response_model=VoiceSession)
def get_voice_session(session_id: str, db: Session = Depends(get_db)):
    """Get a specific voice session by ID."""
    session = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    return session

@router.get("/by-session-id/{session_id}", response_model=VoiceSession)
def get_voice_session_by_session_id(session_id: str, db: Session = Depends(get_db)):
    """Get a voice session by external session ID."""
    session = db.query(VoiceSessionModel).filter(VoiceSessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    return session

@router.post("/", response_model=VoiceSession, status_code=status.HTTP_201_CREATED)
def create_voice_session(session: VoiceSessionCreate, db: Session = Depends(get_db)):
    """Create a new voice session."""
    # Check if session with same session_id already exists
    existing_session = db.query(VoiceSessionModel).filter(VoiceSessionModel.session_id == session.session_id).first()
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice session with this session ID already exists"
        )
    
    db_session = VoiceSessionModel(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.put("/{session_id}", response_model=VoiceSession)
def update_voice_session(session_id: str, session: VoiceSessionUpdate, db: Session = Depends(get_db)):
    """Update a voice session."""
    db_session = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    update_data = session.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)
    
    db.commit()
    db.refresh(db_session)
    return db_session

@router.patch("/{session_id}/status")
def update_session_status(session_id: str, status: SessionStatus, db: Session = Depends(get_db)):
    """Update voice session status."""
    db_session = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    db_session.status = status
    db.commit()
    return {"message": f"Voice session status updated to {status.value}"}

@router.delete("/{session_id}")
def delete_voice_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a voice session."""
    db_session = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    db.delete(db_session)
    db.commit()
    return {"message": "Voice session deleted successfully"}