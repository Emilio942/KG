"""
Authentication module for KG-System
"""

from .auth_service import (
    AuthenticationService,
    User,
    TokenData,
    get_current_user,
    require_roles,
    require_admin,
    require_user,
    rate_limit_dependency,
    auth_service
)

__all__ = [
    'AuthenticationService',
    'User',
    'TokenData',
    'get_current_user',
    'require_roles',
    'require_admin',
    'require_user',
    'rate_limit_dependency',
    'auth_service'
]
