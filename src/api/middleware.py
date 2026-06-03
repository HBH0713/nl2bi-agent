import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger("api.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)

        elapsed = (time.time() - start) * 1000

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed),
        )

        response.headers["X-Request-ID"] = request_id
        return response
