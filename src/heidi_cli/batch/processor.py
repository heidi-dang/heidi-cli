"""
Batch processing and queuing system for model hosting.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger("heidi.batch")

class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class BatchRequest:
    """Individual request within a batch job."""
    request_id: str
    model_id: str
    messages: List[Dict[str, str]]
    parameters: Dict[str, Any]
    user_id: str
    session_id: str

@dataclass
class BatchJob:
    """Batch processing job."""
    job_id: str
    user_id: str
    requests: List[BatchRequest]
    status: JobStatus
    priority: JobPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    progress: int = 0
    total_requests: int = 0
    
    def __post_init__(self):
        if self.total_requests == 0:
            self.total_requests = len(self.requests)

@dataclass
class QueueStatus:
    """Queue status information."""
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    avg_wait_time: float
    avg_processing_time: float
    queue_depth: int

class BatchProcessor:
    """Manages batch processing and job queuing."""
    
    def __init__(self, db_path: Optional[Path] = None, max_workers: int = 4):
        if db_path is None:
            db_path = Path("state/batch.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        self._init_database()
        
        # Thread pool for processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_lock = threading.Lock()
        self._running = False
        self._processor_task = None
    
    def _init_database(self):
        """Initialize batch processing database."""
        with sqlite3.connect(self.db_path) as conn:
            # Jobs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    progress INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    requests TEXT NOT NULL,
                    results TEXT
                )
            """)
            
            # Job metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_metrics (
                    job_id TEXT PRIMARY KEY,
                    wait_time REAL,
                    processing_time REAL,
                    tokens_processed INTEGER,
                    requests_processed INTEGER,
                    FOREIGN KEY (job_id) REFERENCES batch_jobs (job_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON batch_jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON batch_jobs(priority DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON batch_jobs(created_at)")
            
            conn.commit()
    
    def start_processor(self):
        """Start the batch processor."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_jobs())
        logger.info("Batch processor started")
    
    def stop_processor(self):
        """Stop the batch processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
        self.executor.shutdown(wait=True)
        logger.info("Batch processor stopped")
    
    def enqueue_batch(self, user_id: str, requests: List[Dict[str, Any]], 
                     priority: JobPriority = JobPriority.NORMAL) -> str:
        """Enqueue a batch job."""
        job_id = str(uuid.uuid4())
        
        # Convert requests to BatchRequest objects
        batch_requests = []
        for req in requests:
            batch_requests.append(BatchRequest(
                request_id=str(uuid.uuid4()),
                model_id=req.get("model_id", "default"),
                messages=req.get("messages", []),
                parameters=req.get("parameters", {}),
                user_id=user_id,
                session_id=req.get("session_id", "")
            ))
        
        job = BatchJob(
            job_id=job_id,
            user_id=user_id,
            requests=batch_requests,
            status=JobStatus.PENDING,
            priority=priority,
            created_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        self._save_job(job)
        
        logger.info(f"Enqueued batch job {job_id} with {len(requests)} requests")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a specific job."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM batch_jobs WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            requests = json.loads(row['requests'])
            batch_requests = []
            for req in requests:
                batch_requests.append(BatchRequest(**req))
            
            results = None
            if row['results']:
                results = json.loads(row['results'])
            
            return BatchJob(
                job_id=row['job_id'],
                user_id=row['user_id'],
                requests=batch_requests,
                status=JobStatus(row['status']),
                priority=JobPriority(row['priority']),
                created_at=datetime.fromisoformat(row['created_at']),
                started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                error_message=row['error_message'],
                results=results,
                progress=row['progress'],
                total_requests=row['total_requests']
            )
    
    def get_queue_status(self) -> QueueStatus:
        """Get current queue status."""
        with sqlite3.connect(self.db_path) as conn:
            # Count jobs by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM batch_jobs GROUP BY status
            """)
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Calculate averages
            cursor = conn.execute("""
                SELECT 
                    AVG(wait_time) as avg_wait,
                    AVG(processing_time) as avg_process
                FROM job_metrics
                WHERE completed_at > datetime('now', '-24 hours')
            """)
            metrics = cursor.fetchone()
            
            return QueueStatus(
                pending_jobs=status_counts.get('pending', 0),
                running_jobs=status_counts.get('running', 0),
                completed_jobs=status_counts.get('completed', 0),
                failed_jobs=status_counts.get('failed', 0),
                avg_wait_time=metrics['avg_wait'] or 0.0,
                avg_processing_time=metrics['avg_process'] or 0.0,
                queue_depth=status_counts.get('pending', 0)
            )
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE batch_jobs 
                SET status = ?, completed_at = ?
                WHERE job_id = ? AND status = ?
            """, (JobStatus.CANCELLED.value, datetime.now(timezone.utc).isoformat(),
                  job_id, JobStatus.PENDING.value))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Cancelled job {job_id}")
                return True
            return False
    
    def get_user_jobs(self, user_id: str, limit: int = 50) -> List[BatchJob]:
        """Get jobs for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM batch_jobs 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            jobs = []
            for row in cursor.fetchall():
                requests = json.loads(row['requests'])
                batch_requests = []
                for req in requests:
                    batch_requests.append(BatchRequest(**req))
                
                results = None
                if row['results']:
                    results = json.loads(row['results'])
                
                jobs.append(BatchJob(
                    job_id=row['job_id'],
                    user_id=row['user_id'],
                    requests=batch_requests,
                    status=JobStatus(row['status']),
                    priority=JobPriority(row['priority']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    error_message=row['error_message'],
                    results=results,
                    progress=row['progress'],
                    total_requests=row['total_requests']
                ))
            
            return jobs
    
    async def _process_jobs(self):
        """Main job processing loop."""
        while self._running:
            try:
                # Get next job to process
                job = self._get_next_job()
                if not job:
                    await asyncio.sleep(1)  # No jobs, wait
                    continue
                
                # Process job in thread pool
                self.executor.submit(self._process_single_job, job)
                
            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                await asyncio.sleep(5)
    
    def _get_next_job(self) -> Optional[BatchJob]:
        """Get the next job to process."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM batch_jobs 
                WHERE status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """, (JobStatus.PENDING.value,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Update status to running
            conn.execute("""
                UPDATE batch_jobs 
                SET status = ?, started_at = ?
                WHERE job_id = ?
            """, (JobStatus.RUNNING.value, datetime.now(timezone.utc).isoformat(), row['job_id']))
            conn.commit()
            
            # Create job object
            requests = json.loads(row['requests'])
            batch_requests = []
            for req in requests:
                batch_requests.append(BatchRequest(**req))
            
            return BatchJob(
                job_id=row['job_id'],
                user_id=row['user_id'],
                requests=batch_requests,
                status=JobStatus.RUNNING,
                priority=JobPriority(row['priority']),
                created_at=datetime.fromisoformat(row['created_at']),
                started_at=datetime.now(timezone.utc),
                total_requests=row['total_requests']
            )
    
    def _process_single_job(self, job: BatchJob):
        """Process a single batch job."""
        try:
            logger.info(f"Processing job {job.job_id}")
            
            # Import here to avoid circular imports
            from ..model_host.manager import manager
            
            results = []
            total_tokens = 0
            start_time = datetime.now(timezone.utc)
            
            for i, request in enumerate(job.requests):
                try:
                    # Process individual request
                    response = asyncio.run(manager.get_response(
                        model_id=request.model_id,
                        messages=request.messages,
                        **request.parameters
                    ))
                    
                    results.append({
                        "request_id": request.request_id,
                        "status": "success",
                        "response": response
                    })
                    
                    # Count tokens
                    if 'usage' in response:
                        total_tokens += response['usage'].get('total_tokens', 0)
                    
                    # Update progress
                    job.progress = i + 1
                    self._update_job_progress(job.job_id, job.progress)
                    
                except Exception as e:
                    logger.error(f"Error processing request {request.request_id}: {e}")
                    results.append({
                        "request_id": request.request_id,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Calculate metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            wait_time = (job.started_at - job.created_at).total_seconds()
            
            # Update job with results
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.results = results
            job.progress = job.total_requests
            
            self._save_job_results(job, wait_time, processing_time, total_tokens)
            
            logger.info(f"Completed job {job.job_id} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process job {job.job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self._save_job(job)
    
    def _save_job(self, job: BatchJob):
        """Save job to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO batch_jobs (
                    job_id, user_id, status, priority, created_at, started_at,
                    completed_at, error_message, progress, total_requests,
                    requests, results
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.user_id, job.status.value, job.priority.value,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.error_message, job.progress, job.total_requests,
                json.dumps([asdict(req) for req in job.requests]),
                json.dumps(job.results) if job.results else None
            ))
            conn.commit()
    
    def _save_job_results(self, job: BatchJob, wait_time: float, 
                         processing_time: float, total_tokens: int):
        """Save job results and metrics."""
        with sqlite3.connect(self.db_path) as conn:
            # Save job
            self._save_job(job)
            
            # Save metrics
            conn.execute("""
                INSERT OR REPLACE INTO job_metrics (
                    job_id, wait_time, processing_time, tokens_processed,
                    requests_processed
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                job.job_id, wait_time, processing_time, total_tokens,
                job.total_requests
            ))
            conn.commit()
    
    def _update_job_progress(self, job_id: str, progress: int):
        """Update job progress."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE batch_jobs SET progress = ? WHERE job_id = ?
            """, (progress, job_id))
            conn.commit()


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None

def get_batch_processor() -> BatchProcessor:
    """Get global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
        _batch_processor.start_processor()
    return _batch_processor
