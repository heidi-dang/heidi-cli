"""
Audit and compliance logging system for model hosting.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import gzip
import threading

logger = logging.getLogger("heidi.audit")

class AuditLevel(Enum):
    """Audit log levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ComplianceCategory(Enum):
    """Compliance categories."""
    SECURITY = "security"
    PRIVACY = "privacy"
    ACCESS = "access"
    DATA = "data"
    PERFORMANCE = "performance"
    USAGE = "usage"

@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    timestamp: datetime
    level: AuditLevel
    category: ComplianceCategory
    action: str
    resource: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]
    model_id: Optional[str] = None
    tokens_processed: Optional[int] = None
    processing_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.event_id == "":
            self.event_id = hashlib.sha256(
                f"{self.timestamp.isoformat()}{self.action}{self.resource}".encode()
            ).hexdigest()[:16]
    
    @property
    def timestamp_iso(self) -> str:
        """Get ISO format timestamp."""
        return self.timestamp.isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp_iso,
            "level": self.level.value,
            "category": self.category.value,
            "action": self.action,
            "resource": self.resource,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "model_id": self.model_id,
            "tokens_processed": self.tokens_processed,
            "processing_time_ms": self.processing_time_ms,
            "status_code": self.status_code,
            "error_message": self.error_message
        }

@dataclass
class ComplianceReport:
    """Compliance report data."""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    category: ComplianceCategory
    metrics: Dict[str, Any]
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "category": self.category.value,
            "metrics": self.metrics,
            "violations": self.violations,
            "recommendations": self.recommendations
        }

class AuditLogger:
    """Manages audit logging and compliance."""
    
    def __init__(self, db_path: Optional[Path] = None, retention_days: int = 365):
        if db_path is None:
            db_path = Path("state/audit.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        
        self._init_database()
        self._lock = threading.Lock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _init_database(self):
        """Initialize audit database."""
        with sqlite3.connect(self.db_path) as conn:
            # Audit events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    model_id TEXT,
                    tokens_processed INTEGER,
                    processing_time_ms INTEGER,
                    status_code INTEGER,
                    error_message TEXT
                )
            """)
            
            # Compliance reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_reports (
                    report_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    category TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    violations TEXT NOT NULL,
                    recommendations TEXT NOT NULL
                )
            """)
            
            # Data retention table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_retention (
                    table_name TEXT PRIMARY KEY,
                    retention_days INTEGER NOT NULL,
                    last_cleanup TEXT
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_events(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_model ON audit_events(model_id)")
            
            # Initialize retention settings
            conn.execute("""
                INSERT OR REPLACE INTO data_retention (table_name, retention_days, last_cleanup)
                VALUES ('audit_events', ?, datetime('now'))
            """, (self.retention_days,))
            
            conn.commit()
    
    def log_event(self, level: AuditLevel, category: ComplianceCategory, 
                  action: str, resource: str, details: Dict[str, Any] = None,
                  user_id: str = None, session_id: str = None,
                  ip_address: str = None, user_agent: str = None,
                  model_id: str = None, tokens_processed: int = None,
                  processing_time_ms: int = None, status_code: int = None,
                  error_message: str = None) -> str:
        """Log an audit event."""
        event = AuditEvent(
            event_id="",  # Will be generated in __post_init__
            timestamp=datetime.now(timezone.utc),
            level=level,
            category=category,
            action=action,
            resource=resource,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            model_id=model_id,
            tokens_processed=tokens_processed,
            processing_time_ms=processing_time_ms,
            status_code=status_code,
            error_message=error_message
        )
        
        with self._lock:
            self._save_event(event)
        
        return event.event_id
    
    def log_interaction(self, user_id: str, session_id: str, model_id: str,
                       prompt: str, response: str, tokens: int, 
                       processing_time_ms: int, ip_address: str = None,
                       user_agent: str = None) -> str:
        """Log a model interaction for compliance."""
        # Hash sensitive content for privacy
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        response_hash = hashlib.sha256(response.encode()).hexdigest()
        
        details = {
            "prompt_length": len(prompt),
            "response_length": len(response),
            "prompt_hash": prompt_hash,
            "response_hash": response_hash
        }
        
        return self.log_event(
            level=AuditLevel.INFO,
            category=ComplianceCategory.DATA,
            action="model_interaction",
            resource=f"model:{model_id}",
            details=details,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            model_id=model_id,
            tokens_processed=tokens,
            processing_time_ms=processing_time_ms
        )
    
    def log_security_event(self, action: str, details: Dict[str, Any],
                          ip_address: str = None, user_id: str = None) -> str:
        """Log a security event."""
        return self.log_event(
            level=AuditLevel.WARNING,
            category=ComplianceCategory.SECURITY,
            action=action,
            resource="security_system",
            details=details,
            user_id=user_id,
            ip_address=ip_address
        )
    
    def log_access_event(self, user_id: str, resource: str, action: str,
                        granted: bool, ip_address: str = None) -> str:
        """Log an access control event."""
        details = {"granted": granted}
        
        return self.log_event(
            level=AuditLevel.INFO if granted else AuditLevel.WARNING,
            category=ComplianceCategory.ACCESS,
            action=action,
            resource=resource,
            details=details,
            user_id=user_id,
            ip_address=ip_address
        )
    
    def search_events(self, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     user_id: Optional[str] = None,
                     category: Optional[ComplianceCategory] = None,
                     action: Optional[str] = None,
                     model_id: Optional[str] = None,
                     level: Optional[AuditLevel] = None,
                     limit: int = 1000) -> List[AuditEvent]:
        """Search audit events with filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if category:
                query += " AND category = ?"
                params.append(category.value)
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            if model_id:
                query += " AND model_id = ?"
                params.append(model_id)
            
            if level:
                query += " AND level = ?"
                params.append(level.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            events = []
            for row in cursor.fetchall():
                events.append(AuditEvent(
                    event_id=row['event_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    level=AuditLevel(row['level']),
                    category=ComplianceCategory(row['category']),
                    action=row['action'],
                    resource=row['resource'],
                    user_id=row['user_id'],
                    session_id=row['session_id'],
                    ip_address=row['ip_address'],
                    user_agent=row['user_agent'],
                    details=json.loads(row['details']) if row['details'] else {},
                    model_id=row['model_id'],
                    tokens_processed=row['tokens_processed'],
                    processing_time_ms=row['processing_time_ms'],
                    status_code=row['status_code'],
                    error_message=row['error_message']
                ))
            
            return events
    
    def generate_compliance_report(self, category: ComplianceCategory,
                                  period_start: datetime, period_end: datetime) -> ComplianceReport:
        """Generate a compliance report for a specific category and period."""
        report_id = hashlib.sha256(
            f"{category.value}{period_start.isoformat()}{period_end.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Get events for the period
        events = self.search_events(
            start_date=period_start,
            end_date=period_end,
            category=category,
            limit=10000
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(events, category)
        
        # Identify violations
        violations = self._identify_violations(events, category)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(violations, category)
        
        report = ComplianceReport(
            report_id=report_id,
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            category=category,
            metrics=metrics,
            violations=violations,
            recommendations=recommendations
        )
        
        # Save report
        self._save_report(report)
        
        return report
    
    def export_audit_logs(self, start_date: datetime, end_date: datetime,
                         format: str = "json", compress: bool = True) -> Union[str, bytes]:
        """Export audit logs for a date range."""
        events = self.search_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000  # Large limit for export
        )
        
        if format == "json":
            data = json.dumps([event.to_dict() for event in events], indent=2)
            
            if compress:
                return gzip.compress(data.encode())
            return data
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if events:
                fieldnames = list(events[0].to_dict().keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in events:
                    writer.writerow(event.to_dict())
            
            data = output.getvalue()
            
            if compress:
                return gzip.compress(data.encode())
            return data
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get activity summary for a user."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        events = self.search_events(
            start_date=start_date,
            user_id=user_id,
            limit=10000
        )
        
        # Calculate summary
        summary = {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "actions": {},
            "categories": {},
            "models": {},
            "tokens_processed": 0,
            "avg_processing_time_ms": 0,
            "error_rate": 0.0
        }
        
        processing_times = []
        error_count = 0
        
        for event in events:
            # Count actions
            summary["actions"][event.action] = summary["actions"].get(event.action, 0) + 1
            
            # Count categories
            summary["categories"][event.category.value] = summary["categories"].get(event.category.value, 0) + 1
            
            # Count models
            if event.model_id:
                summary["models"][event.model_id] = summary["models"].get(event.model_id, 0) + 1
            
            # Sum tokens
            if event.tokens_processed:
                summary["tokens_processed"] += event.tokens_processed
            
            # Track processing time
            if event.processing_time_ms:
                processing_times.append(event.processing_time_ms)
            
            # Count errors
            if event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
                error_count += 1
        
        # Calculate averages
        if processing_times:
            summary["avg_processing_time_ms"] = sum(processing_times) / len(processing_times)
        
        if len(events) > 0:
            summary["error_rate"] = (error_count / len(events)) * 100
        
        return summary
    
    def _save_event(self, event: AuditEvent):
        """Save audit event to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO audit_events (
                    event_id, timestamp, level, category, action, resource,
                    user_id, session_id, ip_address, user_agent, details,
                    model_id, tokens_processed, processing_time_ms,
                    status_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.timestamp_iso, event.level.value,
                event.category.value, event.action, event.resource,
                event.user_id, event.session_id, event.ip_address,
                event.user_agent, json.dumps(event.details),
                event.model_id, event.tokens_processed, event.processing_time_ms,
                event.status_code, event.error_message
            ))
            conn.commit()
    
    def _save_report(self, report: ComplianceReport):
        """Save compliance report to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO compliance_reports (
                    report_id, generated_at, period_start, period_end,
                    category, metrics, violations, recommendations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id, report.generated_at.isoformat(),
                report.period_start.isoformat(), report.period_end.isoformat(),
                report.category.value, json.dumps(report.metrics),
                json.dumps(report.violations), json.dumps(report.recommendations)
            ))
            conn.commit()
    
    def _calculate_metrics(self, events: List[AuditEvent], 
                          category: ComplianceCategory) -> Dict[str, Any]:
        """Calculate metrics for events."""
        metrics = {
            "total_events": len(events),
            "unique_users": len(set(e.user_id for e in events if e.user_id)),
            "unique_sessions": len(set(e.session_id for e in events if e.session_id)),
            "actions": {},
            "levels": {},
            "avg_tokens_per_event": 0,
            "avg_processing_time_ms": 0
        }
        
        total_tokens = 0
        processing_times = []
        
        for event in events:
            # Count actions
            metrics["actions"][event.action] = metrics["actions"].get(event.action, 0) + 1
            
            # Count levels
            metrics["levels"][event.level.value] = metrics["levels"].get(event.level.value, 0) + 1
            
            # Sum tokens
            if event.tokens_processed:
                total_tokens += event.tokens_processed
            
            # Track processing time
            if event.processing_time_ms:
                processing_times.append(event.processing_time_ms)
        
        # Calculate averages
        if len(events) > 0:
            metrics["avg_tokens_per_event"] = total_tokens / len(events)
        
        if processing_times:
            metrics["avg_processing_time_ms"] = sum(processing_times) / len(processing_times)
        
        return metrics
    
    def _identify_violations(self, events: List[AuditEvent], 
                            category: ComplianceCategory) -> List[Dict[str, Any]]:
        """Identify compliance violations."""
        violations = []
        
        if category == ComplianceCategory.SECURITY:
            # Check for failed authentication attempts
            failed_auth = [e for e in events if e.action == "auth_failed"]
            if len(failed_auth) > 10:  # Threshold
                violations.append({
                    "type": "excessive_failed_auth",
                    "count": len(failed_auth),
                    "severity": "high",
                    "description": f"High number of failed authentication attempts: {len(failed_auth)}"
                })
        
        elif category == ComplianceCategory.USAGE:
            # Check for unusual token usage
            token_events = [e for e in events if e.tokens_processed and e.tokens_processed > 10000]
            if len(token_events) > 0:
                violations.append({
                    "type": "high_token_usage",
                    "count": len(token_events),
                    "severity": "medium",
                    "description": f"High token usage events detected: {len(token_events)}"
                })
        
        return violations
    
    def _generate_recommendations(self, violations: List[Dict[str, Any]],
                                 category: ComplianceCategory) -> List[str]:
        """Generate recommendations based on violations."""
        recommendations = []
        
        for violation in violations:
            if violation["type"] == "excessive_failed_auth":
                recommendations.append("Implement rate limiting for authentication endpoints")
                recommendations.append("Review IP addresses with high failure rates")
            
            elif violation["type"] == "high_token_usage":
                recommendations.append("Monitor user token consumption patterns")
                recommendations.append("Consider implementing token usage alerts")
        
        # General recommendations
        if not violations:
            recommendations.append("Compliance monitoring looks good - continue current practices")
        
        return recommendations
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_old_records():
            while True:
                try:
                    self._cleanup_old_records()
                    # Sleep for 24 hours
                    import time
                    time.sleep(86400)
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
                    time.sleep(3600)  # Retry in 1 hour
        
        cleanup_thread = threading.Thread(target=cleanup_old_records, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_old_records(self):
        """Clean up old audit records based on retention policy."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old audit events
            cursor = conn.execute("""
                DELETE FROM audit_events WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            
            # Update last cleanup time
            conn.execute("""
                UPDATE data_retention SET last_cleanup = datetime('now') WHERE table_name = 'audit_events'
            """)
            
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old audit records")


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
