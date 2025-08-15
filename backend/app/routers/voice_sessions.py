from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import threading
import subprocess
import os
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

@router.get("/active", response_model=List[VoiceSession])
def get_active_voice_sessions(db: Session = Depends(get_db)):
    """Get all currently active voice sessions."""
    sessions = db.query(VoiceSessionModel).filter(
        VoiceSessionModel.status == SessionStatus.ACTIVE
    ).all()
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

# Global dictionary to store active voice processes
active_voice_processes = {}

import atexit
import signal
import sys

def cleanup_active_processes():
    """Clean up all active voice processes on shutdown"""
    for session_id, process_info in list(active_voice_processes.items()):
        try:
            process = process_info["process"]
            if process.poll() is None:  # Process is still running
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception as e:
            pass  # Ignore errors during cleanup

# Register cleanup function to run on exit
atexit.register(cleanup_active_processes)

# Also handle SIGTERM and SIGINT
def signal_handler(sig, frame):
    cleanup_active_processes()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

@router.post("/start-call", response_model=VoiceSession, status_code=status.HTTP_201_CREATED)
def start_voice_call(
    room_number: str, 
    guest_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Start a new voice call session for a guest in a specific room.
    This endpoint triggers the voice AI pipeline on-demand.
    """
    try:
        import time
        import subprocess
        import sys
        from pathlib import Path
        
        # Create a new voice session record
        db_session = VoiceSessionModel(
            room_number=room_number,
            guest_id=guest_id,
            session_id=f"session_{room_number}_{int(time.time())}",
            status=SessionStatus.ACTIVE
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Start the voice pipeline in a separate process
        try:
            # Get the path to the voice pipeline script
            backend_path = Path(__file__).parent.parent.parent
            pipeline_script = backend_path / "hotel_room_service_tavus.py"
            
            # Set environment variables for the subprocess
            env = os.environ.copy()
            env["GUEST_ROOM_NUMBER"] = room_number
            env["VOICE_SESSION_ID"] = db_session.id
            
            # Start the voice pipeline as a subprocess
            process = subprocess.Popen([
                sys.executable, 
                str(pipeline_script)
            ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Store the process for later management
            active_voice_processes[db_session.id] = {
                "process": process,
                "session_id": db_session.id,
                "start_time": time.time()
            }
            
        except Exception as e:
            # Update session status to ERROR if pipeline fails to start
            try:
                db_session.status = SessionStatus.ERROR
                db.commit()
            except Exception as db_error:
                pass  # Ignore database errors in this error handler
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start voice pipeline: {str(e)}"
            )
        
        return db_session
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start voice call: {str(e)}"
        )

@router.post("/end-call/{session_id}")
def end_voice_call(session_id: str, db: Session = Depends(get_db)):
    """
    End a voice call session and terminate the associated process.
    """
    try:
        # Check if we have an active process for this session
        if session_id in active_voice_processes:
            process_info = active_voice_processes[session_id]
            process = process_info["process"]
            
            # Terminate the process
            if process.poll() is None:  # Process is still running
                process.terminate()
                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if it doesn't terminate gracefully
            
            # Remove from active processes
            del active_voice_processes[session_id]
        
        # Update session status in database
        db_session = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == session_id).first()
        if db_session:
            db_session.status = SessionStatus.COMPLETED
            db.commit()
        
        return {"message": "Voice call ended successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end voice call: {str(e)}"
        )