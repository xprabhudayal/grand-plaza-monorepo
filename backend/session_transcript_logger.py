"""
Session-based CSV transcript logger for Pipecat conversations
Creates a new CSV file for each conversation session with timestamp naming
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


class SessionTranscriptLogger:
    """
    Creates a separate CSV file for each conversation session.
    Files are named: conversation_YYYYMMDD_HHMMSS.csv
    """
    
    def __init__(self, log_dir: str = "backend/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename based on session start time
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = f"conversation_{timestamp}.csv"
        self.filepath = self.log_dir / self.filename
        
        self.csv_file = None
        self.csv_writer = None
        self.session_started = False
        
        # CSV headers
        self.headers = [
            'timestamp',
            'role',
            'content', 
            'session_id',
            'room_number',
            'confidence_score',
            'processing_time_ms'
        ]
        
        logger.info(f"SessionTranscriptLogger initialized: {self.filepath}")
    
    def start_session(self, session_id: str):
        """Start logging session and create CSV file"""
        try:
            # Open CSV file for writing
            self.csv_file = open(self.filepath, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.headers)
            
            # Write header row
            self.csv_writer.writeheader()
            self.csv_file.flush()
            
            self.session_started = True
            logger.info(f"Started transcript logging to: {self.filepath}")
            
        except Exception as e:
            logger.error(f"Failed to start session logging: {e}")
    
    def log_message(
        self,
        role: str,
        content: str,
        session_id: str = "",
        room_number: Optional[str] = None,
        confidence_score: Optional[float] = None,
        processing_time_ms: Optional[float] = None
    ):
        """Log a single message to the CSV file"""
        if not self.session_started or not self.csv_writer:
            logger.warning("Session not started, cannot log message")
            return
        
        try:
            row = {
                'timestamp': datetime.now().isoformat(),
                'role': role,
                'content': content,
                'session_id': session_id,
                'room_number': room_number or '',
                'confidence_score': confidence_score or '',
                'processing_time_ms': processing_time_ms or ''
            }
            
            self.csv_writer.writerow(row)
            self.csv_file.flush()  # Ensure immediate write
            
            logger.debug(f"[CSV] {role}: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
    
    def end_session(self):
        """Close the CSV file and end the session"""
        if self.csv_file:
            try:
                self.csv_file.close()
                self.session_started = False
                
                # Log final stats
                if self.filepath.exists():
                    with open(self.filepath, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        message_count = sum(1 for row in reader)
                    
                    logger.info(f"Session ended. Logged {message_count} messages to: {self.filepath}")
                
            except Exception as e:
                logger.error(f"Failed to close session log: {e}")
    
    def get_filepath(self) -> Path:
        """Get the path to the current session CSV file"""
        return self.filepath
    
    def __del__(self):
        """Ensure file is closed when object is deleted"""
        if self.csv_file and not self.csv_file.closed:
            self.end_session()


# Utility function to read a session CSV
def read_session_transcript(csv_filepath: str) -> list:
    """
    Read a session transcript CSV file and return messages as list of dicts
    """
    messages = []
    
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                messages.append(row)
        
        logger.info(f"Read {len(messages)} messages from {csv_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to read transcript file {csv_filepath}: {e}")
    
    return messages


# Utility function to list all session files
def list_session_files(log_dir: str = "backend/logs") -> list:
    """
    List all conversation CSV files in the log directory
    """
    log_path = Path(log_dir)
    csv_files = []
    
    if log_path.exists():
        csv_files = sorted(log_path.glob("conversation_*.csv"), reverse=True)
    
    logger.info(f"Found {len(csv_files)} session files in {log_dir}")
    return [str(f) for f in csv_files]