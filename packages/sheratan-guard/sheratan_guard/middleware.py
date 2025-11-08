"""Middleware integration for guard features"""
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, status
import logging

from .pii import PIIDetector
from .policy import PolicyEngine, PolicyAction
from .audit import AuditLogger, AuditEventType
from .config import GuardConfig
from .ratelimit import RateLimiter, RateLimitMiddleware

logger = logging.getLogger(__name__)


class GuardMiddleware:
    """Combined guard middleware for FastAPI"""
    
    def __init__(
        self,
        enabled: bool = True,
        config: Optional[GuardConfig] = None
    ):
        """
        Initialize guard middleware
        
        Args:
            enabled: Whether guard is enabled
            config: Guard configuration (loads from YAML if not provided)
        """
        self.enabled = enabled
        self.config = config or GuardConfig()
        
        # Initialize components
        self.pii_detector = PIIDetector(enabled=enabled)
        self.policy_engine = PolicyEngine(enabled=enabled)
        self.audit_logger = AuditLogger(enabled=enabled)
        self.rate_limiter = RateLimiter()
        
        # Apply policies from config
        self._load_policies()
        
        logger.info("Guard middleware initialized")
    
    def _load_policies(self):
        """Load policies from configuration"""
        for policy_config in self.config.get_policies():
            try:
                name = policy_config.get("name")
                action_str = policy_config.get("action", "warn")
                description = policy_config.get("description", "")
                conditions = policy_config.get("conditions", [])
                
                # Convert action string to PolicyAction
                action = PolicyAction[action_str.upper()]
                
                # Create condition function from config
                condition = self._create_condition_function(conditions)
                
                self.policy_engine.add_rule(
                    name=name,
                    condition=condition,
                    action=action,
                    message=description
                )
                
            except Exception as e:
                logger.error(f"Error loading policy {policy_config.get('name')}: {e}")
    
    def _create_condition_function(self, conditions: list) -> Callable:
        """Create a condition function from configuration"""
        def condition_func(context: Dict[str, Any]) -> bool:
            for cond in conditions:
                field = cond.get("field")
                operator = cond.get("operator")
                value = cond.get("value")
                
                if operator == "empty":
                    if not context.get(field, "").strip():
                        return True
                
                elif operator == "greater_than":
                    field_val = context.get(field, 0)
                    if isinstance(field_val, str):
                        field_val = len(field_val)
                    if field_val > value:
                        return True
                
                elif operator == "contains":
                    field_val = str(context.get(field, "")).lower()
                    if value.lower() in field_val:
                        return True
                
                elif operator == "equals":
                    if context.get(field) == value:
                        return True
            
            return False
        
        return condition_func
    
    async def check_request(
        self,
        request: Request,
        content: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check request against all guard rules
        
        Args:
            request: FastAPI request object
            content: Content to check (for PII, policies)
            endpoint: Endpoint name for audit logging
            
        Returns:
            Dict with check results and any issues
        """
        if not self.enabled:
            return {
                "allowed": True,
                "pii_detected": False,
                "policy_violations": [],
                "blocked_terms": []
            }
        
        result = {
            "allowed": True,
            "pii_detected": False,
            "pii_types": [],
            "policy_violations": [],
            "blocked_terms": [],
            "warnings": []
        }
        
        if content:
            # Check for PII
            pii_report = self.pii_detector.scan_and_report(content)
            if pii_report["has_pii"]:
                result["pii_detected"] = True
                result["pii_types"] = pii_report["pii_types"]
                
                # Log PII detection
                self.audit_logger.log_pii_detection(
                    pii_types=pii_report["pii_types"],
                    user_id=self._get_client_id(request),
                    metadata={"endpoint": endpoint}
                )
            
            # Check against blocklists
            for blocklist_name in self.config.get_all_blocklists().keys():
                if self.config.is_blocked(content, blocklist_name):
                    result["blocked_terms"].append(blocklist_name)
                    result["allowed"] = False
            
            # Check policies
            context = {
                "content": content,
                "content_length": len(content),
                "endpoint": endpoint,
                "client_id": self._get_client_id(request)
            }
            
            policy_result = self.policy_engine.evaluate(context)
            
            if policy_result["decision"] == PolicyAction.DENY.value:
                result["allowed"] = False
                result["policy_violations"] = policy_result["rules_triggered"]
                
                # Log policy violation
                for rule_name in policy_result["rules_triggered"]:
                    self.audit_logger.log_policy_violation(
                        policy_name=rule_name,
                        user_id=self._get_client_id(request),
                        metadata={"endpoint": endpoint}
                    )
            
            elif policy_result["decision"] == PolicyAction.WARN.value:
                result["warnings"] = policy_result["messages"]
        
        return result
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client ID from request"""
        # Try to get real IP from headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def scrub_pii(self, text: str) -> str:
        """
        Scrub PII from text
        
        Args:
            text: Text to scrub
            
        Returns:
            Text with PII redacted
        """
        return self.pii_detector.redact(text)
    
    def create_rate_limit_middleware(self) -> RateLimitMiddleware:
        """
        Create rate limit middleware with current configuration
        
        Returns:
            Configured RateLimitMiddleware
        """
        return RateLimitMiddleware(
            limiter=self.rate_limiter,
            rate_limit_config=self.config.rate_limits
        )
