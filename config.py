"""
config.py - Configuration for Pinpointe Email Campaign Dashboard
"""

import os

# Timezone
TIMEZONE = "America/New_York"

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "campaigns.db")

# Minimum sends threshold - campaigns below this are ignored
MIN_SENDS = 50

# Number of "live" days (today + N days back) that always refresh from API
LIVE_DAYS = 2

# ─── Dashboard Authentication ─────────────────────────────────────
# Users: role "super" can manage domains, role "user" can only view dashboard
USERS = {
    "admin": {"password": "Shakta@123", "role": "super"},
    "manager": {"password": "Manager@123", "role": "super"},
    "viewer1": {"password": "Viewer@123", "role": "user"},
    "viewer2": {"password": "Viewer@456", "role": "user"},
}
SESSION_SECRET_KEY = "pnpt-dash-s3cr3t-k3y-2026-xK9mQ4vL"  # Change in production

# ─── Leadpier Revenue API ─────────────────────────────────────────
LEADPIER_AUTH_URL = "https://webapi.leadpier.com/v1/frontend/authenticate"
LEADPIER_DATA_URL = "https://webapi.leadpier.com/v1/api/stats/user/org/sources"
LEADPIER_USERNAME = "hello@shaktallc.com"
LEADPIER_PASSWORD = "Shakta123!"
LEADPIER_TOKEN_FILE = os.path.join(
    os.path.dirname(__file__), "database", "leadpier_token.json"
)
LEADPIER_TOKEN_EXPIRY_HOURS = 2
LEADPIER_CACHE_MINUTES = 30  # Don't re-fetch revenue if synced < 30 min ago

# Pinpointe API Domains Configuration
DOMAINS = {
    "P2_LBE": {
        "name": "LoanBoostExpress",
        "api_url": "https://sh5060b.pptsend.com/apixml.php",
        "username": "LoanBoostExpress",
        "usertoken": "2e016eec5ef34a9306001f65ef0f94b894f469ac",
        "le_domain": "loanboostexpress.com",
        "phase": 2,
        "enabled": True,
    },
    "P2_SLE": {
        "name": "SecureLoanEdge",
        "api_url": "https://sh5060b.pptsend.com/apixml.php",
        "username": "SecureLoanEdge",
        "usertoken": "a5e90bcbd4513c7fedc843e3e765f8c677099506",
        "le_domain": "secureloanedge.com",
        "phase": 2,
        "enabled": True,
    },
    "P2_RCT": {
        "name": "RapidCashTrack",
        "api_url": "https://sh5060b.pptsend.com/apixml.php",
        "username": "RapidCashTrack",
        "usertoken": "63be55632d8f67488fa0da7c73c8ca70408cef20",
        "le_domain": "rapidcashtrack.com",
        "phase": 2,
        "enabled": True,
    },
    "P2_PFE": {
        "name": "PrimeFundExpress",
        "api_url": "https://sh5060b.pptsend.com/apixml.php",
        "username": "PrimeFundExpress",
        "usertoken": "964f073010281989d92b47d727e44b92b0a6d75f",
        "le_domain": "primefundexpress.com",
        "phase": 2,
        "enabled": True,
    },
    "P2_AFW": {
        "name": "AdvanceFundWav",
        "api_url": "https://sh5060b.pptsend.com/apixml.php",
        "username": "AdvanceFundWav",
        "usertoken": "3e4864fb5d9ef6d9ae5866843b936a8231b3c8ea",
        "le_domain": "advancefundwave.com",
        "phase": 2,
        "enabled": True,
    },
}
