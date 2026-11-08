"""
Correlation ID Middleware
Ensures every request has a traceable correlation ID for distributed logs
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import structlog

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Bind to structlog contextvars for this task
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
