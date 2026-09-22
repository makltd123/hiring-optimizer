import logging

from fastapi import Depends, HTTPException, Request
from deps import get_current_user
from models.models import User

logger = logging.getLogger("rbac")

PERMISSIONS: dict[str, list[str]] = {
    "admin": ["*"],
    "org_admin": [
        "projects:read_all", "projects:write",
        "candidates:read_all", "results:read_all",
        "users:manage", "reports:export", "audit:read",
    ],
    "dept_manager": [
        "projects:read_dept", "projects:write",
        "candidates:read_dept", "results:read_dept",
    ],
    "hr_manager": [
        "projects:read_own", "projects:write_own",
        "candidates:write", "results:read_own",
    ],
    "viewer": [
        "results:read_own",
    ],
}


def require_permission(permission: str):
    """FastAPI Depends-совместимая проверка разрешения."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        user_permissions = PERMISSIONS.get(current_user.role, [])
        if "*" not in user_permissions and permission not in user_permissions:
            logger.warning(
                "ACCESS_DENIED user_id=%s role=%s required=%s",
                current_user.id, current_user.role, permission,
            )
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return checker
