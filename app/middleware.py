import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.context import request_id_ctx


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)

        try:
            request.state.request_id = request_id
            response: Response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)