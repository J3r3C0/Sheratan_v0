"""Audit log repository for security and compliance tracking"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timedelta

from ..models.documents import AuditLog


class AuditLogRepository:
    """Repository for audit log operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_log(
        self,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create a new audit log entry"""
        log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_log(self, log_id: UUID) -> Optional[AuditLog]:
        """Get audit log by ID"""
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()
    
    async def get_logs_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_logs_by_event_type(
        self,
        event_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs by event type"""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.event_type == event_type)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a specific resource"""
        result = await self.session.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_logs_in_timerange(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """Get audit logs within a time range"""
        query = select(AuditLog).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        )
        
        if event_types:
            query = query.where(AuditLog.event_type.in_(event_types))
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Search audit logs with multiple filters"""
        conditions = []
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if event_type:
            conditions.append(AuditLog.event_type == event_type)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
        
        query = select(AuditLog)
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_logs(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get recent audit logs"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.created_at >= cutoff)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def cleanup_old_logs(
        self,
        days: int = 90
    ) -> int:
        """Delete old audit logs (for compliance with retention policies)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.created_at < cutoff_date)
        )
        logs = result.scalars().all()
        
        count = len(logs)
        for log in logs:
            await self.session.delete(log)
        
        await self.session.flush()
        return count
