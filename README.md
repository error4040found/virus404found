# LeadPier Data Sync Service

FastAPI-based automated service that fetches data from LeadPier API and sends it to LE API every 10 minutes with real-time monitoring.

## Features

- ✅ **FastAPI Web Interface** - Monitor application health and status
- ✅ **Auto Scheduler** - Runs every 10 minutes
- ✅ **Token Management** - Automatic 2-hour expiry check & refresh
- ✅ **Indian Timezone** - All operations in IST
- ✅ **Centralized Logging** - All logs saved in `logs/` folder
- ✅ **REST API Endpoints** - View status, logs, and trigger jobs
- ✅ **Interactive Docs** - Built-in Swagger UI

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Start the Server (Recommended)

```bash
python main.py
```

The server will start on **http://localhost:8000**

- Scheduler runs automatically every 10 minutes
- Initial job starts immediately on startup
- Logs saved to `logs/scheduler_YYYYMMDD.log`

## API Endpoints

Access the service at **http://localhost:8000**

### Health Check

```bash
GET /health
```

Returns scheduler health status

### Service Status

```bash
GET /status
```

Returns detailed statistics:

- Scheduler running status
- Next scheduled run time
- Total/successful/failed runs
- Last execution details (matched/unmatched records)

### View Logs

```bash
GET /logs?lines=50
```

Get recent log entries (default: 50 lines)

### Download Logs

```bash
GET /logs/download
```

Download today's complete log file

### Manual Trigger

```bash
POST /trigger
```

Manually trigger a sync job

### Interactive Documentation

```bash
GET /docs
```

Swagger UI with interactive API documentation

## Example API Responses

### Health Check

```json
{
  "status": "healthy",
  "scheduler_running": true,
  "timestamp": "2026-02-13T23:15:01+05:30"
}
```

### Status

```json
{
  "scheduler": {
    "running": true,
    "next_run": "2026-02-13 23:23:09 IST"
  },
  "job_statistics": {
    "total_runs": 5,
    "successful_runs": 5,
    "failed_runs": 0,
    "success_rate": "100.00%"
  },
  "last_execution": {
    "timestamp": "2026-02-13 23:13:09 IST",
    "status": "success",
    "matched_records": 152,
    "unmatched_records": 43,
    "currently_running": false
  }
}
```

## Files

- **main.py** - FastAPI server with background scheduler
- **login_request.py** - LeadPier authentication
- **get_data.py** - Fetch source statistics
- **post_or_put.py** - Transform & send to LE API
- **source.json** - Token storage
- **logs/** - Daily log files
- **test_api.py** - API testing script

## Configuration

### Change Schedule Interval

Edit `main.py`, line ~142:

```python
trigger=IntervalTrigger(minutes=10),  # Change 10 to desired minutes
```

### Change Server Port

Edit `main.py`, line ~308:

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000)  # Change port
```

### API Endpoints

- **LeadPier API**: `get_data.py` line ~93
- **LE API**: `post_or_put.py` line ~52

## Logging

All logs are saved in the `logs/` folder with daily rotation:

- Format: `logs/scheduler_YYYYMMDD.log`
- Contains: All application events, errors, and API responses
- **No print statements** - Everything uses proper logging

View logs via:

1. API: `GET /logs`
2. File: Check `logs/` folder
3. Real-time: `Get-Content logs/scheduler_YYYYMMDD.log -Wait -Tail 20`

## Monitoring

### View Status Dashboard

```bash
# Open in browser
http://localhost:8000/docs
```

### Check Health

```bash
python test_api.py
```

### View Logs

```bash
# Via API
curl http://localhost:8000/logs?lines=20

# Via file
Get-Content logs/scheduler_20260213.log -Tail 50
```

## Running as Windows Service

Use NSSM (Non-Sucking Service Manager):

```cmd
# Download NSSM from https://nssm.cc/download
nssm install LeadPierSync "C:\path\to\python.exe" "C:\path\to\main.py"
nssm set LeadPierSync AppDirectory "C:\path\to\project"
nssm start LeadPierSync
```

## Troubleshooting

**Server won't start:**

- Check if port 8000 is available
- Verify all dependencies are installed: `pip install -r requirements.txt`

**Token errors:**

- System auto-refreshes tokens every 2 hours
- Manual refresh: `python login_request.py`

**No data being sent:**

- Check logs: `GET /logs`
- Verify API endpoints are accessible
- Check `source.json` has valid token

**Job not running:**

- Check status: `GET /status`
- View scheduler health: `GET /health`
- Manual trigger: `POST /trigger`

## Development

### Run Individual Components

```bash
# Login only
python login_request.py

# Fetch data only
python get_data.py

# Test PUT endpoint only
python post_or_put.py

# Test API
python test_api.py
```

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Server (main.py)        │
│  - REST API Endpoints                   │
│  - Background Scheduler (10 min)        │
│  - Health Monitoring                    │
└────────────┬────────────────────────────┘
             │
             ├─► login_request.py
             │   └─► Authenticate with LeadPier
             │
             ├─► get_data.py
             │   └─► Fetch source statistics
             │
             └─► post_or_put.py
                 └─► Transform & send to LE API
```

## Links

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Status**: http://localhost:8000/status

## Deployment

### 🚀 Quick Deploy to Railway (Recommended)

Railway is the easiest way to deploy this application:

1. Go to https://railway.app and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Done! Your app is deployed with the scheduler running

**See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) for detailed instructions.**

### Other Options

- **Render.com** - Free tier available
- **Heroku** - Classic PaaS platform
- **Docker** - Use included Dockerfile
- **DigitalOcean** - App Platform

**See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for all deployment options.**

### Files for Deployment

- `Dockerfile` - For containerized deployment
- `docker-compose.yml` - For local Docker testing
- `Procfile` - For Heroku/Railway
- `railway.json` - Railway configuration
- `.env.example` - Environment variables template

## License

Internal use only for Shakta LLC.
