"""
FastAPI Application - LeadPier Data Sync Service
Clean API routes with separated concerns
"""

import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pytz import timezone

from config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    HOST,
    PORT,
    RELOAD,
    LOG_LEVEL,
    LOGS_DIR,
    TIMEZONE,
)
from logging_config import setup_logging, get_logger
from models import ServiceInfo, TriggerResponse
from scheduler import (
    init_scheduler,
    shutdown_scheduler,
    get_scheduler,
    get_job_stats,
    trigger_job_manually,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on app startup"""
    init_scheduler()
    logger.info("[API] FastAPI server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown"""
    shutdown_scheduler()
    logger.info("[API] FastAPI server shutdown")


@app.get("/", response_model=ServiceInfo)
async def root():
    """Root endpoint with API information"""
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "logs": "/logs",
            "trigger": "/trigger",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    scheduler = get_scheduler()
    is_healthy = scheduler is not None and scheduler.running

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "healthy" if is_healthy else "unhealthy",
            "scheduler_running": is_healthy,
            "timestamp": datetime.now(timezone(TIMEZONE)).isoformat(),
        },
    )


@app.get("/status")
async def get_status():
    """Get scheduler status and job statistics"""
    scheduler = get_scheduler()
    job_stats = get_job_stats()

    next_run = None
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        if jobs:
            next_run_dt = jobs[0].next_run_time
            if next_run_dt:
                next_run = next_run_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    return {
        "scheduler": {
            "running": scheduler.running if scheduler else False,
            "next_run": next_run,
        },
        "job_statistics": {
            "total_runs": job_stats["total_runs"],
            "successful_runs": job_stats["successful_runs"],
            "failed_runs": job_stats["failed_runs"],
            "success_rate": (
                f"{(job_stats['successful_runs'] / job_stats['total_runs'] * 100):.2f}%"
                if job_stats["total_runs"] > 0
                else "N/A"
            ),
        },
        "last_execution": {
            "timestamp": job_stats["last_run"],
            "status": job_stats["last_status"],
            "matched_records": job_stats["last_matched"],
            "unmatched_records": job_stats["last_unmatched"],
            "currently_running": job_stats["is_running"],
        },
    }


@app.get("/logs")
async def get_logs(lines: int = 50):
    """Get recent log entries"""
    try:
        log_file = LOGS_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

        if not log_file.exists():
            return {"logs": [], "message": "No logs found for today"}

        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "log_file": str(log_file),
            "total_lines": len(all_lines),
            "showing": len(recent_lines),
            "logs": [line.strip() for line in recent_lines],
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/download")
async def download_logs():
    """Download today's log file"""
    log_file = LOGS_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        str(log_file),
        media_type="text/plain",
        filename=log_file.name,
    )


@app.post("/trigger", response_model=TriggerResponse)
async def trigger_job():
    """Manually trigger the sync job"""
    return trigger_job_manually()


if __name__ == "__main__":
    import uvicorn

    logger.info("[SERVER] Starting FastAPI server...")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL,
    )
