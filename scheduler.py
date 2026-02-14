"""
Scheduler logic and job execution
"""

import threading
from datetime import datetime
from typing import Optional, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

from config import SCHEDULE_INTERVAL_MINUTES, TIMEZONE
from logging_config import get_logger
from get_data import get_source_statistics
from post_or_put import process_and_send_leadpier_data

logger = get_logger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None

# Job statistics tracking
job_stats: Dict[str, Any] = {
    "last_run": None,
    "last_status": None,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_matched": 0,
    "last_unmatched": 0,
    "is_running": False,
}


def scheduled_job():
    """
    Main job that runs on schedule to fetch and send data
    """
    global job_stats

    job_stats["is_running"] = True
    job_stats["total_runs"] += 1

    try:
        ist = timezone(TIMEZONE)
        current_time = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %Z")

        logger.info("=" * 70)
        logger.info(f"[STARTED] Job started at {current_time}")
        logger.info("=" * 70)

        # Step 1: Fetch data from LeadPier
        logger.info("[FETCH] Fetching data from LeadPier API...")
        leadpier_data = get_source_statistics()

        if not leadpier_data:
            logger.error("[ERROR] Failed to fetch data from LeadPier API")
            job_stats["last_status"] = "failed"
            job_stats["failed_runs"] += 1
            job_stats["is_running"] = False
            return

        logger.info("[SUCCESS] Successfully fetched LeadPier data")

        # Step 2: Send data to LE API
        logger.info("[SEND] Sending data to LE API...")
        le_response = process_and_send_leadpier_data(leadpier_data)

        if le_response and le_response.get("success"):
            matched = le_response.get("matched", 0)
            unmatched = le_response.get("unmatched", 0)
            job_stats["last_matched"] = matched
            job_stats["last_unmatched"] = unmatched
            logger.info(
                f"[SUCCESS] Data sent - Matched: {matched}, Unmatched: {unmatched}"
            )
            job_stats["last_status"] = "success"
            job_stats["successful_runs"] += 1
        else:
            logger.warning("[WARNING] LE API submission completed with issues")
            job_stats["last_status"] = "warning"
            job_stats["failed_runs"] += 1

        logger.info("=" * 70)
        logger.info("[COMPLETED] Job completed successfully")
        logger.info("=" * 70)
        logger.info("")

        job_stats["last_run"] = current_time

    except Exception as e:
        logger.error(f"[ERROR] Error in scheduled job: {e}", exc_info=True)
        job_stats["last_status"] = "error"
        job_stats["failed_runs"] += 1
    finally:
        job_stats["is_running"] = False


def init_scheduler():
    """
    Initialize and start the background scheduler
    """
    global scheduler

    logger.info("[INIT] Starting LeadPier Data Scheduler Service")
    logger.info(f"[SCHEDULE] Schedule: Every {SCHEDULE_INTERVAL_MINUTES} minutes")
    logger.info("=" * 70)

    # Create background scheduler
    scheduler = BackgroundScheduler(timezone=timezone(TIMEZONE))

    # Add job to run every N minutes
    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(minutes=SCHEDULE_INTERVAL_MINUTES),
        id="leadpier_data_sync",
        name="LeadPier to LE API Data Sync",
        replace_existing=True,
    )

    # Start scheduler
    scheduler.start()

    # Run the job immediately on startup in a separate thread
    logger.info("[RUN] Running initial job...")
    threading.Thread(target=scheduled_job, daemon=True).start()

    logger.info("[READY] Scheduler started successfully")
    logger.info("=" * 70)


def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
    """
    global scheduler

    if scheduler:
        scheduler.shutdown()
        logger.info("[SHUTDOWN] Scheduler stopped")


def get_scheduler():
    """
    Get the global scheduler instance

    Returns:
        BackgroundScheduler instance or None
    """
    return scheduler


def get_job_stats() -> Dict[str, Any]:
    """
    Get current job statistics

    Returns:
        Dictionary with job statistics
    """
    return job_stats.copy()


def trigger_job_manually():
    """
    Manually trigger the scheduled job
    """
    if job_stats["is_running"]:
        return {
            "status": "already_running",
            "message": "Job is currently running. Please wait for it to complete.",
        }

    # Run job in background thread
    threading.Thread(target=scheduled_job, daemon=True).start()

    return {
        "status": "triggered",
        "message": "Job has been triggered and will run in the background",
    }
