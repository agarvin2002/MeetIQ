import logging
import os
import structlog
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON structured logging.

    - Console: human-readable in development
    - File: JSON format, daily rotation, 7-day retention
    - trace_id: automatically injected into every log line via contextvars
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # File handler: rotates daily, keeps 7 days of logs
    file_handler = TimedRotatingFileHandler(
        filename="logs/meetiq.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Console handler for development visibility
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[file_handler, console_handler],
        force=True,
    )

    structlog.configure(
        processors=[
            # Pulls trace_id (and anything else bound via bind_contextvars) into every log line
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # In development: pretty colored output on console
            # In production: JSON (comment out KeyValueRenderer, uncomment JSONRenderer)
            structlog.dev.ConsoleRenderer(),
            # structlog.processors.JSONRenderer(),   # ← use this in production
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Module-level logger — import this everywhere
# Usage: from meetiq.core.logging import logger
# Then:  logger.info("event_name", key="value", another_key=123)
logger = structlog.get_logger()
