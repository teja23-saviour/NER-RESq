from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.models.user import User


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token"
        )

    return payload


def require_roles(*allowed_roles: str):
    """
    Allow access only to users whose JWT role
    matches one of the allowed roles.
    """

    allowed = {
        role.upper()
        for role in allowed_roles
    }

    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        user_role = str(
            current_user.get("role", "")
        ).upper()

        if user_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker


def require_admin(
    current_user: dict = Depends(get_current_user)
):
    role = str(
        current_user.get("role", "")
    ).upper()

    if role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required"
        )

    return current_user


def require_operator_or_admin(
    current_user: dict = Depends(get_current_user)
):
    role = str(
        current_user.get("role", "")
    ).upper()

    if role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(
            status_code=403,
            detail="Operator or administrator access required"
        )

    return current_user


def require_authenticated_user(
    current_user: dict = Depends(get_current_user)
):
    return current_user


def verify_driver_vehicle_access(
    user: User,
    vehicle_id: str
):
    """
    Allow ADMIN and OPERATOR to access any vehicle.
    Allow DRIVER only when the vehicle belongs to that driver.
    """

    role = str(user.role or "").upper()

    if role in {"ADMIN", "OPERATOR"}:
        return True

    if role == "DRIVER" and user.vehicle_id == vehicle_id:
        return True

    return False