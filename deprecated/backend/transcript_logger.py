"""
Simple CSV-based transcript logger with daily rotation for scalability
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
from threading import Lock
from loguru import logger


class TranscriptLogger:
    """
    Logs conversation transcripts to CSV files with daily rotation.
    Creates files like: logs/transcripts_2025_01_21.csv
    """
    
    def __init__(self, log_dir: str = "backend/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_date = None
        self.current_file = None
        self.csv_writer = None
        self.file_handle = None
        self.write_lock = Lock()  # Thread-safe writes
        
        # CSV headers
        self.headers = [
            'timestamp',
            'session_id', 
            'room_number',
            'role',
            'content',
            'confidence_score',
            'processing_time_ms'
        ]
        
        logger.info(f"TranscriptLogger initialized, logs will be saved to: {self.log_dir}")
    
    def _get_log_filename(self) -> Path:
        """Generate daily log filename"""
        date_str = datetime.now().strftime("%Y_%m_%d")
        return self.log_dir / f"transcripts_{date_str}.csv"
    
    def _rotate_if_needed(self):
        """Check if we need to rotate to a new daily file"""
        today = datetime.now().date()
        
        if self.current_date != today:
            # Close previous file if exists
            if self.file_handle:
                self.file_handle.close()
                logger.info(f"Closed log file for date: {self.current_date}")
            
            # Open new file
            self.current_date = today
            self.current_file = self._get_log_filename()
            
            # Check if file exists to determine if we need headers
            file_exists = self.current_file.exists()
            
            # Open in append mode
            self.file_handle = open(self.current_file, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(self.file_handle, fieldnames=self.headers)
            
            # Write headers only if new file
            if not file_exists:
                self.csv_writer.writeheader()
                logger.info(f"Created new transcript log: {self.current_file}")
            else:
                logger.info(f"Appending to existing log: {self.current_file}")
    
    def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        room_number: Optional[str] = None,
        confidence_score: Optional[float] = None,
        processing_time_ms: Optional[float] = None
    ):
        """
        Log a single message to CSV file.
        Thread-safe and handles daily rotation.
        """
        with self.write_lock:
            try:
                self._rotate_if_needed()
                
                row = {
                    'timestamp': datetime.now().isoformat(),
                    'session_id': session_id,
                    'room_number': room_number or '',
                    'role': role,
                    'content': content,
                    'confidence_score': confidence_score or '',
                    'processing_time_ms': processing_time_ms or ''
                }
                
                self.csv_writer.writerow(row)
                self.file_handle.flush()  # Ensure immediate write
                
            except Exception as e:
                logger.error(f"Failed to log transcript: {e}")
    
    async def alog_message(self, *args, **kwargs):
        """Async wrapper for log_message"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.log_message, *args, **kwargs)
    
    def get_session_transcripts(self, session_id: str) -> list:
        """
        Retrieve all transcripts for a given session.
        Searches through all log files.
        """
        transcripts = []
        
        try:
            # Search all CSV files in log directory
            for csv_file in sorted(self.log_dir.glob("transcripts_*.csv")):
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['session_id'] == session_id:
                            transcripts.append(row)
            
            logger.info(f"Retrieved {len(transcripts)} messages for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to retrieve transcripts: {e}")
        
        return transcripts
    
    def get_daily_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific day's transcripts.
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y_%m_%d")
        log_file = self.log_dir / f"transcripts_{date_str}.csv"
        
        stats = {
            'date': date_str,
            'total_messages': 0,
            'unique_sessions': set(),
            'user_messages': 0,
            'assistant_messages': 0,
            'unique_rooms': set()
        }
        
        if not log_file.exists():
            return stats
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats['total_messages'] += 1
                    stats['unique_sessions'].add(row['session_id'])
                    
                    if row['role'] == 'user':
                        stats['user_messages'] += 1
                    elif row['role'] == 'assistant':
                        stats['assistant_messages'] += 1
                    
                    if row['room_number']:
                        stats['unique_rooms'].add(row['room_number'])
            
            # Convert sets to counts for JSON serialization
            stats['unique_sessions'] = len(stats['unique_sessions'])
            stats['unique_rooms'] = len(stats['unique_rooms'])
            
            logger.info(f"Daily stats for {date_str}: {stats}")
            
        except Exception as e:
            logger.error(f"Failed to calculate daily stats: {e}")
        
        return stats
    
    def close(self):
        """Clean up resources"""
        if self.file_handle:
            self.file_handle.close()
            logger.info("TranscriptLogger closed")
    
    def __del__(self):
        """Ensure file is closed on deletion"""
        self.close()


# Utility function for archiving old logs
def archive_old_logs(log_dir: str = "backend/logs", days_to_keep: int = 30):
    """
    Archive logs older than specified days to a compressed format.
    This can be run as a scheduled job.
    """
    import zipfile
    from datetime import timedelta
    
    log_path = Path(log_dir)
    archive_dir = log_path / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for csv_file in log_path.glob("transcripts_*.csv"):
        # Parse date from filename
        try:
            date_str = csv_file.stem.replace("transcripts_", "")
            file_date = datetime.strptime(date_str, "%Y_%m_%d")
            
            if file_date < cutoff_date:
                # Archive the file
                archive_name = archive_dir / f"{csv_file.stem}.zip"
                with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(csv_file, csv_file.name)
                
                # Remove original file
                csv_file.unlink()
                logger.info(f"Archived old log: {csv_file.name}")
                
        except Exception as e:
            logger.error(f"Failed to archive {csv_file}: {e}")