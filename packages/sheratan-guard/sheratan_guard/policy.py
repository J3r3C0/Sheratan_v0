"""Policy engine for access control and content filtering"""
import os
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    """Policy decision actions"""
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"
    WARN = "warn"


class PolicyRule:
    """A single policy rule"""
    
    def __init__(
        self,
        name: str,
        condition: callable,
        action: PolicyAction,
        message: str = ""
    ):
        self.name = name
        self.condition = condition
        self.action = action
        self.message = message
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[PolicyAction]:
        """Evaluate rule against context"""
        try:
            if self.condition(context):
                logger.debug(f"Policy rule '{self.name}' triggered: {self.action.value}")
                return self.action
        except Exception as e:
            logger.error(f"Error evaluating policy rule '{self.name}': {e}")
        
        return None


class PolicyEngine:
    """Main policy engine"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and os.getenv("GUARD_ENABLED", "true").lower() == "true"
        self.rules: List[PolicyRule] = []
        
        if self.enabled:
            self._load_default_rules()
            logger.info("Policy engine initialized")
        else:
            logger.info("Policy engine disabled")
    
    def _load_default_rules(self):
        """Load default policy rules"""
        # Example: Block empty content
        self.add_rule(
            name="no_empty_content",
            condition=lambda ctx: not ctx.get("content", "").strip(),
            action=PolicyAction.DENY,
            message="Content cannot be empty"
        )
        
        # Example: Warn on large documents
        self.add_rule(
            name="large_document_warning",
            condition=lambda ctx: len(ctx.get("content", "")) > 1_000_000,
            action=PolicyAction.WARN,
            message="Document exceeds 1MB"
        )
    
    def add_rule(
        self,
        name: str,
        condition: callable,
        action: PolicyAction,
        message: str = ""
    ):
        """Add a policy rule"""
        rule = PolicyRule(name, condition, action, message)
        self.rules.append(rule)
        logger.info(f"Added policy rule: {name}")
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all rules against context
        
        Returns:
            Dict with decision, triggered rules, and messages
        """
        if not self.enabled:
            return {
                "decision": PolicyAction.ALLOW.value,
                "rules_triggered": [],
                "messages": []
            }
        
        triggered = []
        messages = []
        final_action = PolicyAction.ALLOW
        
        for rule in self.rules:
            action = rule.evaluate(context)
            if action:
                triggered.append(rule.name)
                if rule.message:
                    messages.append(rule.message)
                
                # DENY takes precedence over everything
                if action == PolicyAction.DENY:
                    final_action = PolicyAction.DENY
                    break
                # REDACT takes precedence over WARN and ALLOW
                elif action == PolicyAction.REDACT and final_action != PolicyAction.DENY:
                    final_action = PolicyAction.REDACT
                # WARN takes precedence over ALLOW
                elif action == PolicyAction.WARN and final_action == PolicyAction.ALLOW:
                    final_action = PolicyAction.WARN
        
        return {
            "decision": final_action.value,
            "rules_triggered": triggered,
            "messages": messages
        }
