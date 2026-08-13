import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api-gateway")

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID to request context and response headers, with latency logging."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
        request.state.request_id = req_id
        
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        
        # Log sanitized telemetry (NO code or prompt content)
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} "
            f"[{elapsed_ms:.2f}ms] req_id={req_id}"
        )
        return response
