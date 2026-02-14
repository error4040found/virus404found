"""
Pydantic models for API requests and responses
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SchedulerConfig(BaseModel):
    """Configuration for scheduler interval"""

    interval_minutes: int = Field(
        default=10, ge=1, le=1440, description="Interval in minutes"
    )


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    scheduler_running: bool
    timestamp: str


class SchedulerInfo(BaseModel):
    """Scheduler status information"""

    running: bool
    next_run: Optional[str] = None


class JobStatistics(BaseModel):
    """Job execution statistics"""

    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: str


class LastExecution(BaseModel):
    """Last job execution details"""

    timestamp: Optional[str] = None
    status: Optional[str] = None
    matched_records: int = 0
    unmatched_records: int = 0
    currently_running: bool = False


class StatusResponse(BaseModel):
    """Complete status response"""

    scheduler: SchedulerInfo
    job_statistics: JobStatistics
    last_execution: LastExecution


class LogsResponse(BaseModel):
    """Logs response model"""

    log_file: str
    total_lines: int
    showing: int
    logs: list[str]


class TriggerResponse(BaseModel):
    """Job trigger response"""

    status: str
    message: str


class ServiceInfo(BaseModel):
    """Service information"""

    service: str
    version: str
    status: str
    endpoints: Dict[str, str]
