# System Architecture

## Application Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│                         (main.py)                               │
├─────────────────────────────────────────────────────────────────┤
│  REST Endpoints:                                                │
│  • GET  /         → Service info                                │
│  • GET  /health   → Health check                                │
│  • GET  /status   → Scheduler status + job stats                │
│  • GET  /logs     → Recent log entries                          │
│  • POST /trigger  → Manually trigger job                        │
└───────────────┬─────────────────────────────────────────────────┘
                │
                │ imports
                ↓
    ┌───────────────────────────────────────────────┐
    │         Configuration Layer                   │
    ├───────────────────────────────────────────────┤
    │ • config.py        → App settings             │
    │ • logging_config.py → Logging setup           │
    │ • models.py        → Data models              │
    └───────────────────────────────────────────────┘
                │
                │ imports
                ↓
    ┌───────────────────────────────────────────────┐
    │         Scheduler Layer                       │
    │          (scheduler.py)                       │
    ├───────────────────────────────────────────────┤
    │ • init_scheduler()      → Start scheduler     │
    │ • scheduled_job()       → Job execution       │
    │ • get_job_stats()       → Statistics          │
    │ • trigger_job_manually() → Manual trigger     │
    └─────────────────┬─────────────────────────────┘
                      │
                      │ calls
                      ↓
    ┌─────────────────────────────────────────────────┐
    │         Business Logic Layer                    │
    ├─────────────────────────────────────────────────┤
    │ • get_data.py      → Fetch from LeadPier API    │
    │ • post_or_put.py   → Send to LE API             │
    │ • login_request.py → Authentication             │
    └─────────────────┬───────────────────────────────┘
                      │
                      │ reads/writes
                      ↓
    ┌─────────────────────────────────────────────────┐
    │         Data Layer                              │
    ├─────────────────────────────────────────────────┤
    │ • source.json      → Token storage              │
    │ • logs/            → Application logs           │
    └─────────────────────────────────────────────────┘
```

## Module Responsibilities

### 1. Presentation Layer (main.py)
- **Responsibility:** HTTP request/response handling
- **Dependencies:** config, logging_config, models, scheduler
- **Output:** JSON responses to API clients

### 2. Configuration Layer
#### config.py
- **Responsibility:** Configuration constants
- **Dependencies:** None
- **Output:** Configuration values

#### logging_config.py
- **Responsibility:** Logging setup
- **Dependencies:** config
- **Output:** Configured logger instances

#### models.py
- **Responsibility:** Data validation
- **Dependencies:** None
- **Output:** Pydantic models

### 3. Scheduler Layer (scheduler.py)
- **Responsibility:** Job scheduling and execution
- **Dependencies:** config, logging_config, get_data, post_or_put
- **Output:** Job statistics, execution results

### 4. Business Logic Layer
#### login_request.py
- **Responsibility:** LeadPier authentication
- **Dependencies:** logging_config
- **Output:** Authentication token to source.json

#### get_data.py
- **Responsibility:** Fetch source statistics
- **Dependencies:** logging_config, login_request
- **Output:** LeadPier data

#### post_or_put.py
- **Responsibility:** Data transformation and transmission
- **Dependencies:** logging_config
- **Output:** LE API response

### 5. Data Layer
#### source.json
- **Structure:**
  ```json
  {
    "token": "JWT_TOKEN_HERE",
    "last_login_time": "2026-02-13 23:00:00",
    "user_email": "hello@shaktallc.com",
    "user_name": "User Name"
  }
  ```

#### logs/
- **Format:** scheduler_YYYYMMDD.log
- **Rotation:** Daily

## Data Flow

### Scheduled Job Execution
```
APScheduler (every 10 minutes)
    ↓
scheduler.scheduled_job()
    ↓
    ├─→ Check token expiry (2 hours)
    │   ├─→ Expired? login_request.login()
    │   └─→ Update source.json
    ↓
get_data.get_source_statistics()
    ↓
    ├─→ Read token from source.json
    ├─→ Call LeadPier API
    └─→ Return source statistics
    ↓
post_or_put.process_and_send_leadpier_data()
    ↓
    ├─→ Transform data format
    ├─→ Parse campaign codes
    ├─→ Call LE API with PUT request
    └─→ Return matched/unmatched counts
    ↓
Update job statistics in scheduler.py
    ↓
Log results to logs/scheduler_YYYYMMDD.log
```

### Manual Trigger (via API)
```
Client → POST /trigger
    ↓
main.py → trigger_job()
    ↓
scheduler.trigger_job_manually()
    ↓
    ├─→ Check if job is already running
    └─→ Execute scheduled_job() in background thread
    ↓
Return immediate response
```

## API Endpoints

### GET /
**Purpose:** Service information
**Response:**
```json
{
  "service": "LeadPier Data Sync Service",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {...}
}
```

### GET /health
**Purpose:** Health check for monitoring
**Response:**
```json
{
  "status": "healthy",
  "scheduler_running": true,
  "timestamp": "2026-02-13T23:23:35+05:30"
}
```

### GET /status
**Purpose:** Detailed scheduler and job status
**Response:**
```json
{
  "scheduler": {
    "running": true,
    "next_run": "2026-02-13 23:33:35 IST"
  },
  "job_statistics": {
    "total_runs": 1,
    "successful_runs": 1,
    "failed_runs": 0,
    "success_rate": "100.00%"
  },
  "last_execution": {
    "timestamp": "2026-02-13 23:23:35 IST",
    "status": "success",
    "matched_records": 152,
    "unmatched_records": 44,
    "currently_running": false
  }
}
```

### GET /logs?lines=50
**Purpose:** Recent log entries
**Response:**
```json
{
  "log_file": "logs/scheduler_20260213.log",
  "total_lines": 150,
  "showing": 50,
  "logs": ["2026-02-13 23:23:35 - INFO - ...", ...]
}
```

### POST /trigger
**Purpose:** Manually trigger sync job
**Response:**
```json
{
  "status": "triggered",
  "message": "Job has been triggered..."
}
```

## Configuration

### Scheduler Settings
- **Interval:** 10 minutes
- **Timezone:** Asia/Kolkata (IST)
- **Initial Run:** Immediate on startup

### Token Management
- **Expiry:** 2 hours
- **Auto-refresh:** On expiry detection
- **Storage:** source.json

### Logging
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Destination:** logs/scheduler_YYYYMMDD.log
- **Rotation:** Daily
- **Encoding:** UTF-8

## Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

### Server Deployment
```bash
# Run with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000

# Or use the built-in server
python main.py
```

### Monitoring
- **Health Check:** `curl http://localhost:8000/health`
- **Status:** `curl http://localhost:8000/status`
- **Logs:** `curl http://localhost:8000/logs`
- **Swagger UI:** http://localhost:8000/docs

## Error Handling

### Token Expiry
- **Detection:** Check last_login_time in source.json
- **Action:** Automatic re-authentication
- **Fallback:** Job fails, retry on next schedule

### API Failures
- **LeadPier API:** Log error, skip to next run
- **LE API:** Log error, track unmatched records

### Campaign Code Parsing
- **Invalid Format:** Log warning, count as unmatched
- **Unknown Domain:** Log warning, count as unmatched
- **Continue:** Process remaining records
