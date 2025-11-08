"""Audit logging for security and compliance"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    DOCUMENT_INGEST = "document_ingest"
    SEARCH_QUERY = "search_query"
    ANSWER_REQUEST = "answer_request"
    POLICY_VIOLATION = "policy_violation"
    PII_DETECTED = "pii_detected"
    ACCESS_DENIED = "access_denied"
    SYSTEM_ERROR = "system_error"


class AuditLogger:
    """Audit logging for compliance and security"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.logger = logging.getLogger("sheratan.audit")
        
        # Create separate handler for audit logs
        handler = logging.FileHandler("audit.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        if self.enabled:
            logger.info("Audit logging enabled")
    
    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            user_id: User performing the action
            resource_id: Resource being accessed
            action: Action being performed
            result: Result of the action (success, denied, error)
            metadata: Additional metadata
        """
        if not self.enabled:
            return
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_id": resource_id,
            "action": action,
            "result": result,
            "metadata": metadata or {}
        }
        
        self.logger.info(json.dumps(event))
    
    def log_document_ingest(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log document ingestion"""
        self.log(
            event_type=AuditEventType.DOCUMENT_INGEST,
            user_id=user_id,
            resource_id=document_id,
            action="ingest",
            result="success" if success else "failed",
            metadata=metadata
        )
    
    def log_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        results_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log search query"""
        self.log(
            event_type=AuditEventType.SEARCH_QUERY,
            user_id=user_id,
            action="search",
            result="success",
            metadata={
                **(metadata or {}),
                "query": query,
                "results_count": results_count
            }
        )
    
    def log_policy_violation(
        self,
        policy_name: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log policy violation"""
        self.log(
            event_type=AuditEventType.POLICY_VIOLATION,
            user_id=user_id,
            resource_id=resource_id,
            action=policy_name,
            result="denied",
            metadata=metadata
        )
    
    def log_pii_detection(
        self,
        pii_types: list,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log PII detection"""
        self.log(
            event_type=AuditEventType.PII_DETECTED,
            user_id=user_id,
            resource_id=resource_id,
            action="pii_scan",
            result="detected",
            metadata={
                **(metadata or {}),
                "pii_types": pii_types
            }
        )
