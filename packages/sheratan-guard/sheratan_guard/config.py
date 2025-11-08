"""Configuration loader for policies and blocklists from YAML"""
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GuardConfig:
    """Load and manage guard configuration from YAML files"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize guard configuration
        
        Args:
            config_dir: Directory containing YAML config files
        """
        if config_dir is None:
            config_dir = os.getenv("GUARD_CONFIG_DIR", "/etc/sheratan/guard")
        
        self.config_dir = Path(config_dir)
        self.policies: List[Dict[str, Any]] = []
        self.blocklists: Dict[str, List[str]] = {}
        self.rate_limits: Dict[str, Any] = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load all configuration files"""
        # Load policies
        policy_file = self.config_dir / "policies.yaml"
        if policy_file.exists():
            try:
                with open(policy_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.policies = data.get('policies', [])
                    logger.info(f"Loaded {len(self.policies)} policies from {policy_file}")
            except Exception as e:
                logger.error(f"Error loading policies from {policy_file}: {e}")
                self._load_default_policies()
        else:
            logger.warning(f"Policy file not found: {policy_file}")
            self._load_default_policies()
        
        # Load blocklists
        blocklist_file = self.config_dir / "blocklists.yaml"
        if blocklist_file.exists():
            try:
                with open(blocklist_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.blocklists = data.get('blocklists', {})
                    logger.info(f"Loaded {len(self.blocklists)} blocklists from {blocklist_file}")
            except Exception as e:
                logger.error(f"Error loading blocklists from {blocklist_file}: {e}")
        else:
            logger.warning(f"Blocklist file not found: {blocklist_file}")
            self._load_default_blocklists()
        
        # Load rate limits
        ratelimit_file = self.config_dir / "ratelimits.yaml"
        if ratelimit_file.exists():
            try:
                with open(ratelimit_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.rate_limits = data.get('rate_limits', {})
                    logger.info(f"Loaded rate limits from {ratelimit_file}")
            except Exception as e:
                logger.error(f"Error loading rate limits from {ratelimit_file}: {e}")
        else:
            logger.warning(f"Rate limit file not found: {ratelimit_file}")
            self._load_default_rate_limits()
    
    def _load_default_policies(self):
        """Load default policies when no config file exists"""
        self.policies = [
            {
                "name": "no_empty_content",
                "description": "Reject empty content",
                "action": "deny",
                "conditions": [
                    {"field": "content", "operator": "empty"}
                ]
            },
            {
                "name": "content_size_limit",
                "description": "Warn on large content",
                "action": "warn",
                "conditions": [
                    {"field": "content_length", "operator": "greater_than", "value": 1000000}
                ]
            }
        ]
        logger.info("Loaded default policies")
    
    def _load_default_blocklists(self):
        """Load default blocklists when no config file exists"""
        self.blocklists = {
            "spam_keywords": [
                "viagra", "casino", "lottery", "prize",
                "click here", "limited time", "act now"
            ],
            "offensive_terms": [
                # Add context-specific terms as needed
            ],
            "suspicious_domains": [
                "example-spam.com",
                "suspicious-site.net"
            ]
        }
        logger.info("Loaded default blocklists")
    
    def _load_default_rate_limits(self):
        """Load default rate limits when no config file exists"""
        self.rate_limits = {
            "global": {
                "requests_per_minute": 100,
                "requests_per_hour": 1000
            },
            "ingest": {
                "requests_per_minute": 10,
                "requests_per_hour": 100
            },
            "search": {
                "requests_per_minute": 60,
                "requests_per_hour": 600
            },
            "answer": {
                "requests_per_minute": 20,
                "requests_per_hour": 200
            }
        }
        logger.info("Loaded default rate limits")
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """Get all policies"""
        return self.policies
    
    def get_blocklist(self, name: str) -> List[str]:
        """Get a specific blocklist by name"""
        return self.blocklists.get(name, [])
    
    def get_all_blocklists(self) -> Dict[str, List[str]]:
        """Get all blocklists"""
        return self.blocklists
    
    def get_rate_limit(self, endpoint: str) -> Dict[str, int]:
        """Get rate limit for a specific endpoint"""
        return self.rate_limits.get(endpoint, self.rate_limits.get("global", {}))
    
    def is_blocked(self, text: str, blocklist_name: str = "spam_keywords") -> bool:
        """
        Check if text contains blocked terms
        
        Args:
            text: Text to check
            blocklist_name: Name of the blocklist to use
            
        Returns:
            True if text contains blocked terms
        """
        blocklist = self.get_blocklist(blocklist_name)
        text_lower = text.lower()
        
        for term in blocklist:
            if term.lower() in text_lower:
                logger.warning(f"Blocked term detected: {term}")
                return True
        
        return False
