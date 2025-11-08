"""Tests for policy engine functionality"""
import pytest
from sheratan_guard.policy import PolicyEngine, PolicyAction, PolicyRule


class TestPolicyEngine:
    """Test policy evaluation"""
    
    def test_default_policies(self):
        """Test that default policies are loaded"""
        engine = PolicyEngine(enabled=True)
        
        assert len(engine.rules) > 0
    
    def test_add_custom_rule(self):
        """Test adding a custom policy rule"""
        engine = PolicyEngine(enabled=True)
        initial_count = len(engine.rules)
        
        engine.add_rule(
            name="test_rule",
            condition=lambda ctx: "test" in ctx.get("content", ""),
            action=PolicyAction.DENY,
            message="Test content not allowed"
        )
        
        assert len(engine.rules) == initial_count + 1
    
    def test_empty_content_denied(self):
        """Test that empty content is denied"""
        engine = PolicyEngine(enabled=True)
        
        result = engine.evaluate({"content": ""})
        
        assert result["decision"] == PolicyAction.DENY.value
        assert "no_empty_content" in result["rules_triggered"]
    
    def test_large_content_warning(self):
        """Test warning on large content"""
        engine = PolicyEngine(enabled=True)
        
        large_content = "x" * 1_500_000
        result = engine.evaluate({"content": large_content})
        
        assert result["decision"] == PolicyAction.WARN.value
        assert "large_document_warning" in result["rules_triggered"]
    
    def test_normal_content_allowed(self):
        """Test that normal content is allowed"""
        engine = PolicyEngine(enabled=True)
        
        result = engine.evaluate({"content": "Normal text content"})
        
        assert result["decision"] == PolicyAction.ALLOW.value
        assert len(result["rules_triggered"]) == 0
    
    def test_deny_takes_precedence(self):
        """Test that DENY action takes precedence"""
        engine = PolicyEngine(enabled=True)
        
        # Add a DENY rule
        engine.add_rule(
            name="deny_test",
            condition=lambda ctx: "forbidden" in ctx.get("content", ""),
            action=PolicyAction.DENY,
            message="Forbidden content"
        )
        
        # Add a WARN rule
        engine.add_rule(
            name="warn_test",
            condition=lambda ctx: "forbidden" in ctx.get("content", ""),
            action=PolicyAction.WARN,
            message="Warning"
        )
        
        result = engine.evaluate({"content": "This has forbidden word"})
        
        assert result["decision"] == PolicyAction.DENY.value
    
    def test_redact_action(self):
        """Test REDACT action"""
        engine = PolicyEngine(enabled=True)
        
        engine.add_rule(
            name="redact_sensitive",
            condition=lambda ctx: "sensitive" in ctx.get("content", ""),
            action=PolicyAction.REDACT,
            message="Sensitive content detected"
        )
        
        result = engine.evaluate({"content": "This is sensitive data"})
        
        assert result["decision"] == PolicyAction.REDACT.value
        assert "redact_sensitive" in result["rules_triggered"]
    
    def test_disabled_engine(self):
        """Test that disabled engine always allows"""
        engine = PolicyEngine(enabled=False)
        
        result = engine.evaluate({"content": ""})
        
        assert result["decision"] == PolicyAction.ALLOW.value
        assert len(result["rules_triggered"]) == 0
    
    def test_multiple_rules_triggered(self):
        """Test multiple rules can be triggered"""
        engine = PolicyEngine(enabled=True)
        
        engine.add_rule(
            name="warn_1",
            condition=lambda ctx: "warning1" in ctx.get("content", ""),
            action=PolicyAction.WARN,
            message="Warning 1"
        )
        
        engine.add_rule(
            name="warn_2",
            condition=lambda ctx: "warning2" in ctx.get("content", ""),
            action=PolicyAction.WARN,
            message="Warning 2"
        )
        
        result = engine.evaluate({"content": "warning1 and warning2"})
        
        assert result["decision"] == PolicyAction.WARN.value
        assert len(result["rules_triggered"]) == 2
    
    def test_error_in_condition(self):
        """Test that errors in conditions are handled gracefully"""
        engine = PolicyEngine(enabled=True)
        
        def bad_condition(ctx):
            raise ValueError("Intentional error")
        
        engine.add_rule(
            name="error_rule",
            condition=bad_condition,
            action=PolicyAction.DENY,
            message="Should not trigger"
        )
        
        # Should not raise exception
        result = engine.evaluate({"content": "test"})
        
        # The error rule should not trigger
        assert "error_rule" not in result["rules_triggered"]
