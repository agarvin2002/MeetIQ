import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Generates a short unique ID for every HTTP request.

    This ID is:
    - Bound into structlog's context so every log line includes trace_id
    - Returned in the X-Trace-ID response header (useful for debugging)

    Example log output:
        info  calendar_fetch_complete  trace_id=a1b2c3d4  meeting_count=5
        info  company_extracted        trace_id=a1b2c3d4  domain=linear.app
    All lines from the same request share the same trace_id.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())[:8]

        # Bind trace_id to structlog context for this request
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            path=request.url.path,
        )

        response = await call_next(request)

        # Expose trace_id in response headers for debugging
        response.headers["X-Trace-ID"] = trace_id

        # Clear context so it doesn't leak into next request
        structlog.contextvars.clear_contextvars()

        return response
