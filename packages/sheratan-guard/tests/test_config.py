"""Tests for configuration loading from YAML"""
import pytest
import tempfile
import os
from pathlib import Path
from sheratan_guard.config import GuardConfig


class TestGuardConfig:
    """Test YAML configuration loading"""
    
    def test_default_config_when_no_files(self):
        """Test that default config is loaded when files don't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = GuardConfig(config_dir=tmpdir)
            
            # Should have default policies
            assert len(config.get_policies()) > 0
            
            # Should have default blocklists
            assert len(config.get_all_blocklists()) > 0
            
            # Should have default rate limits
            assert "global" in config.rate_limits
    
    def test_load_policies_from_yaml(self):
        """Test loading policies from YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create policy file
            policy_file = Path(tmpdir) / "policies.yaml"
            policy_file.write_text("""
policies:
  - name: test_policy
    description: Test policy
    action: deny
    conditions:
      - field: content
        operator: empty
""")
            
            config = GuardConfig(config_dir=tmpdir)
            policies = config.get_policies()
            
            assert len(policies) > 0
            assert any(p["name"] == "test_policy" for p in policies)
    
    def test_load_blocklists_from_yaml(self):
        """Test loading blocklists from YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create blocklist file
            blocklist_file = Path(tmpdir) / "blocklists.yaml"
            blocklist_file.write_text("""
blocklists:
  test_list:
    - spam
    - malicious
    - forbidden
""")
            
            config = GuardConfig(config_dir=tmpdir)
            blocklist = config.get_blocklist("test_list")
            
            assert len(blocklist) == 3
            assert "spam" in blocklist
            assert "malicious" in blocklist
    
    def test_load_rate_limits_from_yaml(self):
        """Test loading rate limits from YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create rate limit file
            ratelimit_file = Path(tmpdir) / "ratelimits.yaml"
            ratelimit_file.write_text("""
rate_limits:
  global:
    requests_per_minute: 50
    requests_per_hour: 500
  /test:
    requests_per_minute: 10
    requests_per_hour: 100
""")
            
            config = GuardConfig(config_dir=tmpdir)
            
            global_limits = config.get_rate_limit("global")
            assert global_limits["requests_per_minute"] == 50
            
            test_limits = config.get_rate_limit("/test")
            assert test_limits["requests_per_minute"] == 10
    
    def test_is_blocked(self):
        """Test blocklist checking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            blocklist_file = Path(tmpdir) / "blocklists.yaml"
            blocklist_file.write_text("""
blocklists:
  spam_keywords:
    - viagra
    - casino
    - lottery
""")
            
            config = GuardConfig(config_dir=tmpdir)
            
            # Should be blocked
            assert config.is_blocked("Buy viagra now!", "spam_keywords") is True
            assert config.is_blocked("Visit our casino", "spam_keywords") is True
            
            # Should not be blocked
            assert config.is_blocked("Normal text", "spam_keywords") is False
    
    def test_case_insensitive_blocking(self):
        """Test that blocking is case-insensitive"""
        with tempfile.TemporaryDirectory() as tmpdir:
            blocklist_file = Path(tmpdir) / "blocklists.yaml"
            blocklist_file.write_text("""
blocklists:
  test_list:
    - BadWord
""")
            
            config = GuardConfig(config_dir=tmpdir)
            
            assert config.is_blocked("badword", "test_list") is True
            assert config.is_blocked("BADWORD", "test_list") is True
            assert config.is_blocked("BaDwOrD", "test_list") is True
    
    def test_get_nonexistent_blocklist(self):
        """Test getting a blocklist that doesn't exist"""
        config = GuardConfig()
        
        blocklist = config.get_blocklist("nonexistent")
        
        assert blocklist == []
    
    def test_get_nonexistent_rate_limit(self):
        """Test getting rate limit for endpoint without specific config"""
        config = GuardConfig()
        
        limit = config.get_rate_limit("/unknown_endpoint")
        
        # Should return global default
        assert "requests_per_minute" in limit
        assert "requests_per_hour" in limit
    
    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid YAML file
            policy_file = Path(tmpdir) / "policies.yaml"
            policy_file.write_text("invalid: yaml: content: [")
            
            # Should not raise exception, should use defaults
            config = GuardConfig(config_dir=tmpdir)
            
            # Should have default policies
            assert len(config.get_policies()) > 0
