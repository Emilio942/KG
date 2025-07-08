"""
Authentication and Authorization System for KG-System
Implements JWT-based authentication with role-based access control
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis
import json
from ..utils.config import get_config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

class User(BaseModel):
    """User model for authentication"""
    id: str
    username: str
    email: str
    roles: List[str]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

class TokenData(BaseModel):
    """Token payload structure"""
    user_id: str
    username: str
    roles: List[str]
    exp: int
    iat: int

class AuthConfig:
    """Authentication configuration"""
    def __init__(self):
        self.config = get_config()
        self.SECRET_KEY = secrets.token_hex(32)  # Generate a random secret key
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        self.REFRESH_TOKEN_EXPIRE_DAYS = 30
        self.REDIS_URL = f"redis://{self.config.redis_host}:{self.config.redis_port}"
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.REDIS_URL)
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None

auth_config = AuthConfig()

class AuthenticationService:
    """Main authentication service"""
    
    def __init__(self):
        self.config = auth_config
        self.users_db = {}  # In production, use proper database
        self.refresh_tokens = {}
        
        # Create default admin user
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user"""
        admin_user = User(
            id="admin",
            username="admin",
            email="admin@kg-system.com",
            roles=["admin", "user"],
            created_at=datetime.utcnow()
        )
        
        # Hash password
        password_hash = self._hash_password("admin123")
        self.users_db["admin"] = {
            "user": admin_user,
            "password_hash": password_hash
        }
        
        logger.info("Default admin user created")
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash_check.hex() == hash_value
        except Exception:
            return False
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "roles": user.roles,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM)
        
        # Store in Redis for validation
        if self.config.redis_client:
            try:
                self.config.redis_client.setex(
                    f"token:{token}",
                    self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    json.dumps({"user_id": user.id, "active": True})
                )
            except Exception as e:
                logger.warning(f"Failed to store token in Redis: {e}")
        
        return token
    
    def create_refresh_token(self, user: User) -> str:
        """Create refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "user_id": user.id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM)
        self.refresh_tokens[token] = user.id
        
        return token
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            # Check if token is blacklisted
            if self.config.redis_client:
                try:
                    token_data = self.config.redis_client.get(f"token:{token}")
                    if not token_data:
                        return None
                    
                    token_info = json.loads(token_data)
                    if not token_info.get("active", False):
                        return None
                except Exception as e:
                    logger.warning(f"Redis token check failed: {e}")
            
            # Decode token
            payload = jwt.decode(token, self.config.SECRET_KEY, algorithms=[self.config.ALGORITHM])
            
            if payload.get("type") != "access":
                return None
            
            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                roles=payload["roles"],
                exp=payload["exp"],
                iat=payload["iat"]
            )
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        user_data = self.users_db.get(username)
        if not user_data:
            return None
        
        if not self._verify_password(password, user_data["password_hash"]):
            return None
        
        user = user_data["user"]
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        logger.info(f"User authenticated: {username}")
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        for user_data in self.users_db.values():
            if user_data["user"].id == user_id:
                return user_data["user"]
        return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke access token"""
        if self.config.redis_client:
            try:
                self.config.redis_client.setex(
                    f"token:{token}",
                    self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    json.dumps({"user_id": "", "active": False})
                )
                return True
            except Exception as e:
                logger.error(f"Failed to revoke token: {e}")
        return False

# Global authentication service instance
auth_service = AuthenticationService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    token_data = auth_service.verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def require_roles(*required_roles: str):
    """Decorator to require specific roles"""
    def decorator(current_user: User = Depends(get_current_user)):
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    return decorator

# Role-based dependencies
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user

async def require_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user role (basic authenticated user)"""
    if "user" not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="User access required"
        )
    return current_user

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limit"""
        client_ip = request.client.host
        current_time = datetime.utcnow()
        
        # Clean old requests
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

async def rate_limit_dependency(request: Request):
    """Rate limiting dependency"""
    if not await rate_limiter.check_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    return True
