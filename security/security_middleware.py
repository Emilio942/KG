
import jwt
import redis
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

class EnterpriseSecurityMiddleware:
    """
    Enterprise-grade security middleware for KG-System
    Implements multi-tenant isolation, rate limiting, and audit logging
    """
    
    def __init__(self, redis_client, auth0_domain: str, api_audience: str):
        self.redis = redis_client
        self.auth0_domain = auth0_domain
        self.api_audience = api_audience
        self.logger = logging.getLogger(__name__)
        
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and extract tenant context"""
        try:
            # Verify token with Auth0 public key
            unverified_header = jwt.get_unverified_header(token)
            
            # Get public key from Auth0
            public_key = self._get_auth0_public_key(unverified_header['kid'])
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=self.api_audience,
                issuer=f'https://{self.auth0_domain}/'
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {str(e)}")
            return None
    
    def check_rate_limit(self, user_id: str, tenant_id: str) -> bool:
        """Check rate limits for user and tenant"""
        current_time = datetime.utcnow()
        window_start = current_time.replace(second=0, microsecond=0)
        
        # User-level rate limiting (1000 requests per minute)
        user_key = f"rate_limit:user:{user_id}:{window_start.isoformat()}"
        user_count = self.redis.incr(user_key)
        self.redis.expire(user_key, 60)
        
        if user_count > 1000:
            return False
            
        # Tenant-level rate limiting (10000 requests per minute)
        tenant_key = f"rate_limit:tenant:{tenant_id}:{window_start.isoformat()}"
        tenant_count = self.redis.incr(tenant_key)
        self.redis.expire(tenant_key, 60)
        
        if tenant_count > 10000:
            return False
            
        return True
    
    def enforce_tenant_isolation(self, token_payload: Dict, resource_tenant_id: str) -> bool:
        """Ensure users can only access their tenant's resources"""
        token_tenant_id = token_payload.get('https://kg-system.com/tenant_id')
        
        if not token_tenant_id:
            self.logger.warning("No tenant_id in token")
            return False
            
        if token_tenant_id != resource_tenant_id:
            self.logger.warning(f"Tenant isolation violation: token={token_tenant_id}, resource={resource_tenant_id}")
            return False
            
        return True
    
    def log_audit_event(self, event_type: str, user_id: str, tenant_id: str, details: Dict):
        """Log security and audit events"""
        audit_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'tenant_id': tenant_id,
            'sweet_spot_mode': 'high_performance_enterprise',
            'details': details
        }
        
        # Store in Redis for real-time monitoring
        self.redis.lpush('audit_events', json.dumps(audit_event))
        self.redis.expire('audit_events', 86400)  # 24 hours
        
        # Log for permanent storage
        self.logger.info(f"AUDIT: {json.dumps(audit_event)}")
    
    def validate_sweet_spot_access(self, token_payload: Dict) -> bool:
        """Validate access to Sweet Spot features"""
        sweet_spot_mode = token_payload.get('https://kg-system.com/sweet_spot_mode')
        
        if sweet_spot_mode != 'high_performance_enterprise':
            self.logger.warning("Access denied: Invalid sweet spot mode")
            return False
            
        return True
