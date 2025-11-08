"""PII (Personally Identifiable Information) detection"""
import os
import re
from typing import List, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PIIType(Enum):
    """Types of PII that can be detected"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


class PIIPattern:
    """A PII detection pattern"""
    
    def __init__(self, pii_type: PIIType, pattern: str, label: str):
        self.pii_type = pii_type
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.label = label
    
    def find(self, text: str) -> List[Dict[str, Any]]:
        """Find all matches in text"""
        matches = []
        for match in self.pattern.finditer(text):
            matches.append({
                "type": self.pii_type.value,
                "label": self.label,
                "value": match.group(),
                "start": match.start(),
                "end": match.end()
            })
        return matches


class PIIDetector:
    """Detect PII in text"""
    
    # Common PII patterns
    PATTERNS = [
        PIIPattern(
            PIIType.EMAIL,
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "Email Address"
        ),
        PIIPattern(
            PIIType.PHONE,
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "Phone Number"
        ),
        PIIPattern(
            PIIType.SSN,
            r'\b\d{3}-\d{2}-\d{4}\b',
            "Social Security Number"
        ),
        PIIPattern(
            PIIType.CREDIT_CARD,
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "Credit Card Number"
        ),
        PIIPattern(
            PIIType.IP_ADDRESS,
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "IP Address"
        ),
    ]
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and os.getenv("PII_DETECTION_ENABLED", "true").lower() == "true"
        
        if self.enabled:
            logger.info("PII detection enabled")
        else:
            logger.info("PII detection disabled")
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text
        
        Args:
            text: Text to scan
            
        Returns:
            List of detected PII with type, location, and value
        """
        if not self.enabled:
            return []
        
        all_matches = []
        
        for pattern in self.PATTERNS:
            matches = pattern.find(text)
            all_matches.extend(matches)
        
        # Sort by position
        all_matches.sort(key=lambda x: x['start'])
        
        if all_matches:
            logger.warning(f"Detected {len(all_matches)} PII instances")
        
        return all_matches
    
    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact PII from text
        
        Args:
            text: Text to redact
            replacement: Replacement string
            
        Returns:
            Text with PII redacted
        """
        if not self.enabled:
            return text
        
        matches = self.detect(text)
        
        if not matches:
            return text
        
        # Redact from end to start to preserve positions
        result = text
        for match in reversed(matches):
            result = result[:match['start']] + replacement + result[match['end']:]
        
        logger.info(f"Redacted {len(matches)} PII instances")
        return result
    
    def scan_and_report(self, text: str) -> Dict[str, Any]:
        """
        Scan text and return detailed report
        
        Returns:
            Dict with found PII and redacted text
        """
        matches = self.detect(text)
        redacted = self.redact(text) if matches else text
        
        return {
            "has_pii": len(matches) > 0,
            "pii_count": len(matches),
            "pii_types": list(set(m['type'] for m in matches)),
            "matches": matches,
            "redacted_text": redacted
        }
