"""Tests for PII detection functionality"""
import pytest
from sheratan_guard.pii import PIIDetector, PIIType


class TestPIIDetector:
    """Test PII detection and redaction"""
    
    def test_email_detection(self):
        """Test email address detection"""
        detector = PIIDetector(enabled=True)
        text = "Contact me at john.doe@example.com for details"
        
        matches = detector.detect(text)
        
        assert len(matches) == 1
        assert matches[0]["type"] == PIIType.EMAIL.value
        assert "john.doe@example.com" in matches[0]["value"]
    
    def test_phone_detection(self):
        """Test phone number detection"""
        detector = PIIDetector(enabled=True)
        text = "Call me at 555-123-4567 or 5551234567"
        
        matches = detector.detect(text)
        
        assert len(matches) >= 1
        assert any(m["type"] == PIIType.PHONE.value for m in matches)
    
    def test_ssn_detection(self):
        """Test SSN detection"""
        detector = PIIDetector(enabled=True)
        text = "SSN: 123-45-6789"
        
        matches = detector.detect(text)
        
        assert len(matches) == 1
        assert matches[0]["type"] == PIIType.SSN.value
    
    def test_credit_card_detection(self):
        """Test credit card detection"""
        detector = PIIDetector(enabled=True)
        text = "Card number: 4532-1234-5678-9010"
        
        matches = detector.detect(text)
        
        assert len(matches) == 1
        assert matches[0]["type"] == PIIType.CREDIT_CARD.value
    
    def test_ip_address_detection(self):
        """Test IP address detection"""
        detector = PIIDetector(enabled=True)
        text = "Server IP: 192.168.1.100"
        
        matches = detector.detect(text)
        
        assert len(matches) == 1
        assert matches[0]["type"] == PIIType.IP_ADDRESS.value
    
    def test_multiple_pii_detection(self):
        """Test detection of multiple PII types"""
        detector = PIIDetector(enabled=True)
        text = "Email: test@example.com, Phone: 555-123-4567, IP: 10.0.0.1"
        
        matches = detector.detect(text)
        
        assert len(matches) == 3
        types = [m["type"] for m in matches]
        assert PIIType.EMAIL.value in types
        assert PIIType.PHONE.value in types
        assert PIIType.IP_ADDRESS.value in types
    
    def test_redaction(self):
        """Test PII redaction"""
        detector = PIIDetector(enabled=True)
        text = "Contact john@example.com at 555-123-4567"
        
        redacted = detector.redact(text)
        
        assert "john@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_custom_replacement(self):
        """Test PII redaction with custom replacement"""
        detector = PIIDetector(enabled=True)
        text = "Email: test@example.com"
        
        redacted = detector.redact(text, replacement="***")
        
        assert "test@example.com" not in redacted
        assert "***" in redacted
    
    def test_scan_and_report(self):
        """Test comprehensive scan and report"""
        detector = PIIDetector(enabled=True)
        text = "Contact: user@example.com, Phone: 555-123-4567"
        
        report = detector.scan_and_report(text)
        
        assert report["has_pii"] is True
        assert report["pii_count"] == 2
        assert len(report["pii_types"]) == 2
        assert PIIType.EMAIL.value in report["pii_types"]
        assert PIIType.PHONE.value in report["pii_types"]
        assert "user@example.com" not in report["redacted_text"]
        assert "555-123-4567" not in report["redacted_text"]
    
    def test_no_pii_detection(self):
        """Test text without PII"""
        detector = PIIDetector(enabled=True)
        text = "This is just normal text without any sensitive information"
        
        matches = detector.detect(text)
        
        assert len(matches) == 0
    
    def test_disabled_detector(self):
        """Test that disabled detector returns empty results"""
        detector = PIIDetector(enabled=False)
        text = "Email: test@example.com, Phone: 555-123-4567"
        
        matches = detector.detect(text)
        redacted = detector.redact(text)
        
        assert len(matches) == 0
        assert redacted == text  # No redaction when disabled
