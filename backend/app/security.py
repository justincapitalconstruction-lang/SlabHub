"""Simple role-based security helpers.

This module defines helper functions to extract a user's role from request
headers and enforce administrative permissions on endpoints. It assumes
clients send an `X-Role` header with values like `admin` or `user`.
"""
from fastapi import Depends, Header, HTTPException, status


def get_current_role(x_role: str | None = Header(default=None)) -> str:
    """Extract the current role from the X-Role header.

    If no role is provided, defaults to "user".
    """
    return x_role or "user"


def require_admin(role: str = Depends(get_current_role)) -> str:
    """Dependency that ensures the current role is admin.

    Raises:
        HTTPException: If the role is not 'admin'.

    Returns:
        str: The role (for further use if needed).
    """
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return role
