"""
Correlation ID Middleware
Ensures every request has a traceable correlation ID for distributed logs
"""

import uuid
from time import perf_counter
from app.core.metrics import system_metrics
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
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            route = request.scope.get("route")
            # Route templates prevent high-cardinality IDs and financial data in metrics.
            system_metrics.observe(request.method, getattr(route, "path", "unmatched"),
                                   status_code, perf_counter() - started)
            structlog.contextvars.clear_contextvars()
