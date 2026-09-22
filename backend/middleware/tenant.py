from fastapi import Request
from jose import jwt, JWTError
from config import settings


class TenantMiddleware:
    """
    Извлекает org_id из JWT и устанавливает переменную сессии PostgreSQL
    app.current_org_id для Row Level Security. Для SQLite — no-op.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            token = self._extract_token(request)
            if token:
                org_id = self._get_org_id(token)
                if org_id:
                    scope["state"] = scope.get("state", {})
                    scope["state"]["org_id"] = org_id
        await self.app(scope, receive, send)

    def _extract_token(self, request: Request) -> str | None:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _get_org_id(self, token: str) -> int | None:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True},
            )
            return payload.get("org_id")
        except JWTError:
            return None
