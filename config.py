"""
Configuration settings for LeadPier Data Sync Service
"""

import os
from pathlib import Path

# Application Info
APP_TITLE = "LeadPier Data Sync Service"
APP_DESCRIPTION = "Automated service to sync LeadPier data to LE API"
APP_VERSION = "1.0.0"

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
RELOAD = False
LOG_LEVEL = "info"

# Scheduler Configuration
SCHEDULE_INTERVAL_MINUTES = 10
TIMEZONE = "Asia/Kolkata"

# API Configuration
LEADPIER_AUTH_URL = "https://webapi.leadpier.com/v1/frontend/authenticate"
LEADPIER_DATA_URL = "https://webapi.leadpier.com/v1/api/stats/user/org/sources"
LE_API_URL = "https://app.shaktallc.com/email_dashboard/stats/le_api.php"

# Authentication Credentials
LEADPIER_USERNAME = "hello@shaktallc.com"
LEADPIER_PASSWORD = "Shakta123!"

# Token Management
TOKEN_EXPIRY_HOURS = 2  # Token expires after 2 hours

# Paths
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
SOURCE_JSON = BASE_DIR / "source.json"

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL_CONFIG = "INFO"
