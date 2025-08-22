
import sys
import logging
from loguru import logger

def configure_logging():
    """
    Configures Loguru to capture logs from the entire application,
    including pipecat, langgraph, and RAG modules.
    """
    logger.remove()  # Remove default handler to avoid duplicate outputs

    # This format shows where the log is coming from, which is crucial for debugging.
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Configure console logger for real-time, colorized output
    logger.add(
        sys.stderr,
        level="DEBUG",
        format=log_format,
        colorize=True,
        backtrace=True,  # Show full stack trace on exceptions
        diagnose=True    # Add exception variable values for debugging
    )

    # Configure file logger to save all logs for later inspection
    logger.add(
        "logs/app.log",
        level="DEBUG",
        format=log_format,
        rotation="10 MB",    # Rotates the log file when it reaches 10 MB
        retention="7 days",  # Keeps log files for 7 days
        enqueue=True,        # Makes logging thread-safe and non-blocking
        backtrace=True,
        diagnose=True,
        serialize=False      # Keep logs in human-readable format
    )

    # Intercept standard logging messages from other libraries (like pipecat)
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

    # This forces other libraries to push their logs through our interceptor
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    logger.info("Logging configured successfully. All logs will be captured and saved to logs/app.log")
