import sys
import logging
from loguru import logger

def configure_logging():
    """Configures Loguru for concise and relevant logging."""
    
    # Define a filter to control what gets logged
    def log_filter(record):
        # Allow all logs from our application modules
        if record["name"].startswith(("langgraph_agent", "rag_pipeline", "__main__", "hotel_concierge_langgraph")):
            return True
        
        # Allow INFO and above from STT/TTS services
        if "pipecat.services" in record["name"] and ("stt" in record["name"] or "tts" in record["name"]):
            return record["level"].no >= logger.level("INFO").no
            
        # Suppress DEBUG logs from other libraries (like pipecat core, httpcore)
        if record["level"].name == "DEBUG" and not record["name"].startswith(("langgraph_agent", "rag_pipeline", "__main__")):
            return False
            
        # Allow INFO and above from everything else
        return record["level"].no >= logger.level("INFO").no

    # Remove default handler and add a new one with the filter
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",  # Capture all levels, let the filter decide
        filter=log_filter,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{line}</cyan> - <level>{message}</level>"
    )

    # Intercept standard logging to route it through Loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)