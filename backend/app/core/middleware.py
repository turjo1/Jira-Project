import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import api_request_latency_ms


class RequestLatencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        api_request_latency_ms.labels(
            method=request.method,
            route=route_path,
            status=str(response.status_code),
        ).observe(elapsed_ms)
        return response
