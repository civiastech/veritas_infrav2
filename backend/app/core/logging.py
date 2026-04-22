import json
import time
from starlette.middleware.base import BaseHTTPMiddleware

class JsonLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log = {
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'latency_ms': duration_ms,
            'client_ip': request.client.host if request.client else None,
        }
        print(json.dumps(log), flush=True)
        return response
