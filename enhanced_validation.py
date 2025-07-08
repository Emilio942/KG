#!/usr/bin/env python3
"""
KG-System Enhanced Data Validation
Implements comprehensive input validation and security measures.
"""

from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, validator
import re
from enum import Enum

if TYPE_CHECKING:
    from datetime import datetime

class ValidationLevel(str, Enum):
    """Validation security levels"""
    BASIC = "basic"
    STRICT = "strict"
    ENTERPRISE = "enterprise"

class EnhancedHypothesisRequest(BaseModel):
    """Enhanced hypothesis request with comprehensive validation"""
    
    targetProfile: List[str] = Field(..., min_items=1, max_items=10)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    context: str = Field(default="Default hypothesis request")
    validation_level: ValidationLevel = Field(default=ValidationLevel.BASIC)
    exclude: List[str] = Field(default_factory=list)
    signal: str = Field(default="CREATE_NEW")
    priority: str = Field(default="NORMAL")
    userID: Optional[str] = Field(default=None)
    timestamp: Optional[str] = Field(default=None)
    
    @validator('targetProfile')
    def validate_target_profile(cls, v):
        """Validate target profile contains only allowed taste profiles"""
        allowed_profiles = {
            'SÜSS', 'SAUER', 'BITTER', 'SALZIG', 'UMAMI',
            'FRUCHTIG', 'ERDIG', 'BLUMIG', 'WÜRZIG', 'MINZIG'
        }
        
        for profile in v:
            if profile.upper() not in allowed_profiles:
                raise ValueError(f"Invalid taste profile: {profile}. Allowed: {allowed_profiles}")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate taste profiles not allowed")
            
        return [p.upper() for p in v]
    
    @validator('constraints')
    def validate_constraints(cls, v):
        """Validate constraints are within acceptable ranges"""
        if not v:  # If empty, set defaults
            v = {'maxComponents': 5, 'noveltyThreshold': 0.8}
            
        required_fields = {'maxComponents', 'noveltyThreshold'}
        
        # Check required fields
        missing_fields = required_fields - set(v.keys())
        if missing_fields:
            raise ValueError(f"Missing required constraint fields: {missing_fields}")
        
        # Validate maxComponents
        max_components = v.get('maxComponents')
        if not isinstance(max_components, int) or max_components < 1 or max_components > 20:
            raise ValueError("maxComponents must be integer between 1 and 20")
        
        # Validate noveltyThreshold
        novelty = v.get('noveltyThreshold')
        if not isinstance(novelty, (int, float)) or novelty < 0 or novelty > 1:
            raise ValueError("noveltyThreshold must be float between 0 and 1")
        
        # Additional optional validations
        if 'timeLimit' in v:
            time_limit = v['timeLimit']
            if not isinstance(time_limit, (int, float)) or time_limit < 1 or time_limit > 3600:
                raise ValueError("timeLimit must be between 1 and 3600 seconds")
        
        return v
    
    @validator('context')
    def validate_context(cls, v):
        """Validate context string for security and content"""
        # Remove potential script injection
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'exec\s*\('
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Context contains potentially dangerous content")
        
        # Basic content validation
        if len(v.strip()) < 3:
            raise ValueError("Context must contain meaningful content")
        
        return v.strip()

class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests = {}
        self.limits = {
            'per_minute': 60,
            'per_hour': 1000,
            'per_day': 10000
        }
    
    def check_rate_limit(self, client_id: str, endpoint: str) -> Dict[str, Any]:
        """Check if request is within rate limits"""
        import time
        
        current_time = time.time()
        key = f"{client_id}:{endpoint}"
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests (older than 1 day)
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if current_time - req_time < 86400
        ]
        
        # Check limits
        recent_requests = self.requests[key]
        minute_requests = len([t for t in recent_requests if current_time - t < 60])
        hour_requests = len([t for t in recent_requests if current_time - t < 3600])
        day_requests = len(recent_requests)
        
        if minute_requests >= self.limits['per_minute']:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded: too many requests per minute",
                "retry_after": 60
            }
        
        if hour_requests >= self.limits['per_hour']:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded: too many requests per hour",
                "retry_after": 3600
            }
        
        if day_requests >= self.limits['per_day']:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded: too many requests per day",
                "retry_after": 86400
            }
        
        # Add current request
        self.requests[key].append(current_time)
        
        return {
            "allowed": True,
            "remaining": {
                "per_minute": self.limits['per_minute'] - minute_requests - 1,
                "per_hour": self.limits['per_hour'] - hour_requests - 1,
                "per_day": self.limits['per_day'] - day_requests - 1
            }
        }

class SecurityValidator:
    """Enhanced security validation for API requests"""
    
    @staticmethod
    def validate_request_size(content: str, max_size: int = 1024 * 1024) -> bool:
        """Validate request size is within limits"""
        return len(content.encode('utf-8')) <= max_size
    
    @staticmethod
    def validate_content_type(content_type: str) -> bool:
        """Validate content type is allowed"""
        allowed_types = ['application/json', 'text/plain']
        return content_type in allowed_types
    
    @staticmethod
    def detect_injection_attempts(data: Dict[str, Any]) -> List[str]:
        """Detect potential injection attempts"""
        issues = []
        
        def check_value(value, path=""):
            if isinstance(value, str):
                # SQL injection patterns
                sql_patterns = [
                    r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
                    r"(?i)(or|and)\s+\d+\s*=\s*\d+",
                    r"(?i)'.*?'\s*(or|and)",
                    r"--;",
                    r"/\*.*?\*/"
                ]
                
                for pattern in sql_patterns:
                    if re.search(pattern, value):
                        issues.append(f"Potential SQL injection in {path}: {pattern}")
                
                # XSS patterns
                xss_patterns = [
                    r"<script.*?>",
                    r"javascript:",
                    r"on\w+\s*=",
                    r"vbscript:",
                    r"data:.*base64"
                ]
                
                for pattern in xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        issues.append(f"Potential XSS in {path}: {pattern}")
            
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}" if path else k)
            
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    check_value(v, f"{path}[{i}]" if path else f"[{i}]")
        
        check_value(data)
        return issues
    
    def validate_request(self, request: EnhancedHypothesisRequest) -> "ValidationReport":
        """Validate an enhanced hypothesis request for security issues"""
        report = ValidationReport(
            is_valid=True, 
            validation_level=request.validation_level,
            timestamp=str(request.timestamp) if request.timestamp else None
        )
        
        # Convert request to dict for validation
        request_dict = request.dict()
        
        # Check for injection attempts
        injection_issues = self.detect_injection_attempts(request_dict)
        for issue in injection_issues:
            report.add_error(issue)
        
        # Validate request size
        request_str = str(request_dict)
        if not self.validate_request_size(request_str):
            report.add_error("Request size exceeds maximum allowed")
        
        # Check for suspicious patterns in target profiles
        for profile in request.targetProfile:
            if any(char in profile for char in ['<', '>', '"', "'", ';', '--']):
                report.add_error(f"Suspicious characters in target profile: {profile}")
        
        # Check for suspicious patterns in exclude field
        for exclude_item in request.exclude:
            if any(pattern in exclude_item for pattern in ['../', '../', '.\\', '..\\', '/etc/', '/bin/', 'passwd']):
                report.add_error(f"Path traversal attempt detected in exclude field: {exclude_item}")
            if any(char in exclude_item for char in ['<', '>', '"', "'", ';', '--']):
                report.add_error(f"Suspicious characters in exclude field: {exclude_item}")
        
        return report

class ValidationReport(BaseModel):
    """Validation report with results and errors"""
    is_valid: bool = Field(...)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_level: ValidationLevel = Field(...)
    timestamp: Optional[str] = Field(default=None)
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)

# Global instances
rate_limiter = RateLimiter()
security_validator = SecurityValidator()

def validate_enhanced_request(request_data: Dict[str, Any], client_id: str = "default") -> Dict[str, Any]:
    """Comprehensive request validation"""
    
    # Security checks
    security_issues = security_validator.detect_injection_attempts(request_data)
    if security_issues:
        return {
            "valid": False,
            "errors": security_issues,
            "error_type": "security_violation"
        }
    
    # Size validation
    request_str = str(request_data)
    if not security_validator.validate_request_size(request_str):
        return {
            "valid": False,
            "errors": ["Request size exceeds maximum allowed"],
            "error_type": "size_limit"
        }
    
    # Rate limiting
    rate_check = rate_limiter.check_rate_limit(client_id, "hypothesis_generation")
    if not rate_check["allowed"]:
        return {
            "valid": False,
            "errors": [rate_check["reason"]],
            "error_type": "rate_limit",
            "retry_after": rate_check["retry_after"]
        }
    
    # Schema validation
    try:
        validated_request = EnhancedHypothesisRequest(**request_data)
        return {
            "valid": True,
            "validated_data": validated_request.dict(),
            "rate_limit_remaining": rate_check.get("remaining", {})
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "error_type": "validation_error"
        }

if __name__ == "__main__":
    # Test cases
    print("🔒 Testing Enhanced Data Validation")
    print("=" * 50)
    
    # Valid request
    valid_request = {
        "targetProfile": ["SÜSS", "FRUCHTIG"],
        "constraints": {"maxComponents": 3, "noveltyThreshold": 0.7},
        "context": "Test hypothesis generation"
    }
    
    result = validate_enhanced_request(valid_request)
    print(f"Valid request: {'✅ PASSED' if result['valid'] else '❌ FAILED'}")
    
    # Invalid requests
    invalid_requests = [
        {
            "targetProfile": [],  # Empty profile
            "constraints": {"maxComponents": 3},
            "context": "Test"
        },
        {
            "targetProfile": ["INVALID_PROFILE"],  # Invalid profile
            "constraints": {"maxComponents": 3, "noveltyThreshold": 0.7},
            "context": "Test"
        },
        {
            "targetProfile": ["SÜSS"],
            "constraints": {"maxComponents": -1, "noveltyThreshold": 2.0},  # Invalid values
            "context": "Test"
        },
        {
            "targetProfile": ["SÜSS"],
            "constraints": {"maxComponents": 3, "noveltyThreshold": 0.7},
            "context": "<script>alert('xss')</script>"  # XSS attempt
        }
    ]
    
    for i, invalid_req in enumerate(invalid_requests, 1):
        result = validate_enhanced_request(invalid_req)
        print(f"Invalid request {i}: {'❌ PROPERLY REJECTED' if not result['valid'] else '⚠️ INCORRECTLY ACCEPTED'}")
        if not result['valid']:
            print(f"  Reason: {result['errors'][0]}")
    
    print("\n✅ Enhanced validation system operational!")
