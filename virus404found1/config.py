"""
config.py - Configuration for Insight Bridge Email Campaign Dashboard
"""

import os

# Timezone
TIMEZONE = "America/New_York"

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "campaigns.db")

# Minimum sends threshold - campaigns below this are ignored
MIN_SENDS = 5

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
SESSION_SECRET_KEY = "pnpt-dash-v2-s3cr3t-k3y-2026-zR7nP8wM"  # Change in production

# ─── Leadpier Revenue API ─────────────────────────────────────────
LEADPIER_AUTH_URL = "https://webapi.leadpier.com/v1/frontend/authenticate"
LEADPIER_DATA_URL = "https://webapi.leadpier.com/v1/api/stats/user/org/sources"
LEADPIER_USERNAME = "info@insightbridgeusa.com"
LEADPIER_PASSWORD = "Shakta123!"
LEADPIER_TOKEN_FILE = os.path.join(
    os.path.dirname(__file__), "database", "leadpier_token.json"
)
LEADPIER_TOKEN_EXPIRY_HOURS = 2
LEADPIER_CACHE_MINUTES = 30  # Don't re-fetch revenue if synced < 30 min ago

# ─── ExcelTrack Revenue API ───────────────────────────────────────
EXLTRK_API_URL = "https://partner.exltrk.com/api"
EXLTRK_API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiOTQzMDMzZWE5NWM2NGFmZTc4NjFkMmZhOTYwNjE1MjJlOTQxNGRmNTFlNWZiMzQ0ZGQ0NGI3Njk0MWY2MGRlMzYwMWFlNmQ5YjhhNDIzMzciLCJpYXQiOjE3Njg2Njg5MjcuNzc1Mzg4LCJuYmYiOjE3Njg2Njg5MjcuNzc1MzksImV4cCI6MTgwMDIwNDkyNy43NTIzMjksInN1YiI6IjIyMDg3OCIsInNjb3BlcyI6WyIqIl19.jCzzXdJIaGhlFWAUGk9yCtwch7rBzyC7UhWf_SklYgR3gWCvK0dAae_0il7yzDhbNcfDULXJzus_xnkz9M2mhK8CnSRtkB8iRyrAB0FzHv2qBTpfAOyOAMEdiCKAjzXYc_WV4Spwy9c_Kdneyi0ER_uAhCyjVn0ZX4B1xqUIFCw0OtYxurkeLLx7C6fpovBc_56DwMKWo9KB5bZdG2WBN7XVG9FggKc8-TFYIvXGogXKffQ0-WCUz-GF2Glr9DRkcUE9p0uJlb63TqRuSYu68ihJxkjOKHF6gohnnXV7MgI3kfoqO6GV5wkG87v6XS_ZNyyWwdfnhlza_xi1S8peYapOlWdQEsuNcsjKzQRpsHvGRdzqHcwThJKbh_ezoc7w2VjxeJQQvC1LWaBLt97rdr2X5zME0B1r4gL8HCYu1IEXTVwyry3QYni5aKrBJhRjPxfAGGJwCzxrKEnAS2wS_0kLgOirBOJdksLGNdg1dd9DLGZtP1nuJkH4It45p5P55HAM04RMmESRRxb386rIItD7v2fdvsFNz7cWh9mxrp0Qn0tG_FdrdpKYVQUTi7wQou3SDul7WEoa2aafJ915WCJOHdwnAHBzCpmveLIi48ee8Buln9cRB7j9SLQhkiY29GmNJwFR7LJxnoRcDzAL6tTv_oZ8b8HiDLVTa2_EzWo"
EXLTRK_CACHE_MINUTES = 30  # Don't re-fetch EXL if synced < 30 min ago

# Insight Bridge API Domains Configuration
DOMAINS = {
    "P3_CFL": {
        "name": "CapitalFastLane",
        "api_url": "https://ib5131.pptsend.com/apixml.php",
        "username": "CapitalFastLane",
        "usertoken": "37f3b27c0c77a9fa711ef41403e8838fd49616d6",
        "le_domain": "capitalfastlane.com",
        "phase": 3,
        "enabled": True,
    },
    "P3_CAP": {
        "name": "CashAccessPro",
        "api_url": "https://ib5131.pptsend.com/apixml.php",
        "username": "CashAccessPro",
        "usertoken": "43bc2a163d0eb8adcf32dee81fa94c857fe965ce",
        "le_domain": "cashaccesspro.com",
        "phase": 3,
        "enabled": True,
    },
    "P3_EFP": {
        "name": "EasyFundPath",
        "api_url": "https://ib5131.pptsend.com/apixml.php",
        "username": "EasyFundPath",
        "usertoken": "f1327adfc1c28e6bd95f717edc2dd4bfd6a321c7",
        "le_domain": "easyfundpath.com",
        "phase": 3,
        "enabled": True,
    },
    "P3_FEP": {
        "name": "FundEdgePro",
        "api_url": "https://ib5131.pptsend.com/apixml.php",
        "username": "FundEdgePro",
        "usertoken": "101ae20bec205af50215db7a09a7833f6fd01a7e",
        "le_domain": "fundedgepro.com",
        "phase": 3,
        "enabled": True,
    },
    "P3_RFB": {
        "name": "RapidFundBridge",
        "api_url": "https://ib5131.pptsend.com/apixml.php",
        "username": "RapidFundBridge",
        "usertoken": "5d9fb077f532b7386730542b27beeb09ded46169",
        "le_domain": "rapidfundbridge.com",
        "phase": 3,
        "enabled": True,
    },
}
