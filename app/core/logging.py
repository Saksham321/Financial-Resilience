"""
Structured Logging Configuration
Powered by structlog for production-grade observability
"""

import logging
import re
import sys

import structlog

from app.core.config import settings


class FinancialAccessFilter(logging.Filter):
    """Redact source identifiers and query parameters from server access logs."""
    def filter(self,record):
        if isinstance(record.args,tuple):
            record.args=tuple(re.sub(r'(/api/v1/(?:source-review|datasets/accounts)/)[^/? ]+',r'\1[redacted]',value).split('?')[0]
                if isinstance(value,str) and '/api/v1/' in value else value for value in record.args)
        return True


logging.getLogger('uvicorn.access').addFilter(FinancialAccessFilter())

def setup_logging():
    """
    Configures structured logging for both standard library and structlog.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.LOG_FORMAT.lower() == "json" and not settings.DEBUG:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

logger = structlog.get_logger("financial_resilience_engine")
