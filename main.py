"""
main.py - FastAPI application for Pinpointe Email Campaign Dashboard

Endpoints:
  GET  /login               → Login page
  POST /login               → Authenticate
  GET  /logout              → Logout
  GET  /                    → Dashboard UI (auth required)
  GET  /api/today           → Today's campaigns (excl. seeds) + revenue
  GET  /api/range           → Campaigns for date range + revenue
  GET  /api/seeds/today     → Today's seed campaigns + revenue
  GET  /api/seeds/range     → Seed campaigns for date range + revenue
  POST /api/sync/today      → Sync today from Pinpointe + Leadpier
  POST /api/sync/range      → Sync date range
  POST /api/sync/live       → Sync live days (T, T-1, T-2)
  POST /api/sync/revenue    → Sync Leadpier revenue only
  GET  /api/domains         → List configured domains
  GET  /api/health          → Health check
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

import pytz
from fastapi import FastAPI, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import TIMEZONE, DOMAINS, USERS, SESSION_SECRET_KEY

BASE_DIR = Path(__file__).resolve().parent
from database import (
    init_schema,
    upsert_domain,
    get_all_domains,
    get_all_domains_admin,
    get_domain_by_id,
    create_domain,
    update_domain,
    delete_domain,
    cleanup_old_data,
    get_daily_aggregated_stats,
    get_campaigns_by_date_range,
    get_leadpier_sources_by_date,
)
from sync_service import (
    sync_today,
    sync_live_days,
    sync_campaigns,
    sync_revenue,
    sync_exltrk_revenue,
    get_today_campaigns,
    get_campaigns_grouped,
    get_today_seed_campaigns,
    get_today_test_campaigns,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("main")


# ── Scheduled cleanup job ─────────────────────────────────────────
def scheduled_cleanup():
    """Run daily cleanup of data older than 30 days."""
    logger.info("Scheduler: starting daily data cleanup...")
    try:
        result = cleanup_old_data(days=30)
        logger.info(
            "Scheduler: cleanup complete — %d campaigns, %d stats, %d leadpier sources, %d exltrk sources removed (cutoff: %s)",
            result["campaigns"],
            result["campaign_stats"],
            result["leadpier_sources"],
            result.get("exltrk_sources", 0),
            result["cutoff_date"],
        )
    except Exception as e:
        logger.error("Scheduler: cleanup failed — %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB, seed domains, start scheduler."""
    logger.info("Initializing database...")
    init_schema()
    for code, domain in DOMAINS.items():
        upsert_domain(code, domain)
    logger.info("Database ready. %d domains loaded.", len(DOMAINS))

    # Start scheduler — runs cleanup daily at 2:00 AM EST
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        scheduled_cleanup,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_cleanup",
        name="Remove data older than 30 days",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily cleanup at 2:00 AM %s", TIMEZONE)

    # Also run cleanup once on startup
    scheduled_cleanup()

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Pinpointe Campaign Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files & templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Public paths that don't require login ─────────────────────────
PUBLIC_PATHS = {"/login", "/api/health"}
PUBLIC_PREFIXES = ("/static/",)
# Paths that require super role
SUPER_PATHS = {"/domains"}
SUPER_API_PREFIX = "/api/admin/"


class AuthGuardMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated users to login page. Enforce role for super paths."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow public paths and static files through
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        # Check session
        if not request.session.get("authenticated"):
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "error": "Not authenticated"},
                )
            return RedirectResponse(url="/login", status_code=302)
        # Check super role for admin paths
        role = request.session.get("role", "user")
        if path in SUPER_PATHS or path.startswith(SUPER_API_PREFIX):
            if role != "super":
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "error": "Super admin access required",
                        },
                    )
                return RedirectResponse(url="/", status_code=302)
        return await call_next(request)


# Order matters: SessionMiddleware wraps the app first,
# then AuthGuardMiddleware runs inside it (has access to request.session)
app.add_middleware(AuthGuardMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)


# ──────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already logged in, go to dashboard
    if request.session.get("authenticated"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    user = USERS.get(username)
    if user and user["password"] == password:
        request.session["authenticated"] = True
        request.session["username"] = username
        request.session["role"] = user["role"]
        logger.info("User '%s' (%s) logged in", username, user["role"])
        return RedirectResponse(url="/", status_code=302)
    logger.warning("Failed login attempt for user '%s'", username)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ──────────────────────────────────────────────────────────────────────
# Dashboard pages
# ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "role": request.session.get("role", "user"),
            "username": request.session.get("username", ""),
        },
    )


@app.get("/domains", response_class=HTMLResponse)
async def domains_page(request: Request):
    """Domain management dashboard (super users only — enforced by middleware)."""
    return templates.TemplateResponse(
        "domains.html",
        {
            "request": request,
            "role": request.session.get("role", "user"),
            "username": request.session.get("username", ""),
        },
    )


# ──────────────────────────────────────────────────────────────────────
# API: Read endpoints (from database)
# ──────────────────────────────────────────────────────────────────────
@app.get("/api/today")
async def api_today():
    domains = get_today_campaigns()
    return {
        "success": True,
        "date": datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d"),
        "timezone": TIMEZONE,
        "domains": domains,
    }


@app.get("/api/range")
async def api_range(
    startDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    endDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    domains = get_campaigns_grouped(startDate, endDate)
    return {
        "success": True,
        "startDate": startDate,
        "endDate": endDate,
        "timezone": TIMEZONE,
        "domains": domains,
    }


@app.get("/api/seeds/today")
async def api_seeds_today():
    domains = get_today_seed_campaigns()
    return {
        "success": True,
        "date": datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d"),
        "timezone": TIMEZONE,
        "domains": domains,
    }


@app.get("/api/seeds/range")
async def api_seeds_range(
    startDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    endDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    domains = get_campaigns_grouped(startDate, endDate, seed_only=True)
    return {
        "success": True,
        "startDate": startDate,
        "endDate": endDate,
        "timezone": TIMEZONE,
        "domains": domains,
    }


@app.get("/api/testing/today")
async def api_testing_today():
    domains = get_today_test_campaigns()
    return {
        "success": True,
        "date": datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d"),
        "timezone": TIMEZONE,
        "domains": domains,
    }


@app.get("/api/testing/range")
async def api_testing_range(
    startDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    endDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    domains = get_campaigns_grouped(startDate, endDate, test_only=True)
    return {
        "success": True,
        "startDate": startDate,
        "endDate": endDate,
        "timezone": TIMEZONE,
        "domains": domains,
    }


# ──────────────────────────────────────────────────────────────────────
# API: Sync endpoints (hit Pinpointe API → write to DB)
# ──────────────────────────────────────────────────────────────────────
@app.post("/api/sync/today")
async def api_sync_today():
    try:
        result = await sync_today()
        # Also sync Leadpier + ExcelTrack revenue for today
        today = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")
        rev = await sync_revenue(today, force=True)
        exl_rev = await sync_exltrk_revenue(today, force=True)
        result["revenue_sync"] = rev
        result["exltrk_sync"] = exl_rev
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.post("/api/sync/range")
async def api_sync_range(
    startDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    endDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    try:
        result = await sync_campaigns(startDate, endDate)
        # Sync Leadpier + ExcelTrack revenue for each date in range
        from datetime import timedelta as td

        rev_results = []
        exl_results = []
        d = datetime.strptime(startDate, "%Y-%m-%d")
        end = datetime.strptime(endDate, "%Y-%m-%d")
        while d <= end:
            day_str = d.strftime("%Y-%m-%d")
            rev = await sync_revenue(day_str, force=True)
            exl_rev = await sync_exltrk_revenue(day_str, force=True)
            rev_results.append(rev)
            exl_results.append(exl_rev)
            d += td(days=1)
        result["revenue_sync"] = rev_results
        result["exltrk_sync"] = exl_results
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.post("/api/sync/live")
async def api_sync_live():
    try:
        result = await sync_live_days()
        # Sync Leadpier + ExcelTrack revenue for live days
        from datetime import timedelta as td
        from config import LIVE_DAYS

        tz = pytz.timezone(TIMEZONE)
        rev_results = []
        exl_results = []
        for i in range(LIVE_DAYS + 1):
            day_str = (datetime.now(tz) - td(days=i)).strftime("%Y-%m-%d")
            rev = await sync_revenue(day_str, force=True)
            exl_rev = await sync_exltrk_revenue(day_str, force=True)
            rev_results.append(rev)
            exl_results.append(exl_rev)
        result["revenue_sync"] = rev_results
        result["exltrk_sync"] = exl_results
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.post("/api/sync/revenue")
async def api_sync_revenue(
    date: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    """Sync Leadpier + ExcelTrack revenue data only (no Pinpointe sync)."""
    try:
        if not date:
            date = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")
        result = await sync_revenue(date, force=True)
        exl_result = await sync_exltrk_revenue(date, force=True)
        return {"success": True, "leadpier": result, "exltrk": exl_result, "date": date}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


# ──────────────────────────────────────────────────────────────────────
# Visual Analytics
# ──────────────────────────────────────────────────────────────────────
@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Visual analytics page with charts."""
    domains = get_all_domains()
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "role": request.session.get("role", "user"),
            "username": request.session.get("username", ""),
            "domains": domains,
        },
    )


@app.get("/api/analytics")
async def api_analytics(
    startDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    endDate: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    domain: str = Query(None),
):
    """Return aggregated analytics data for charts: daily breakdown, domain breakdown, totals.
    Optional `domain` param filters by domain code (e.g. P2_LBE). Omit for all domains.
    """
    # Daily aggregation (filtered by domain if specified)
    daily_rows = get_daily_aggregated_stats(startDate, endDate, domain_code=domain)

    # Domain breakdown — single source of truth for revenue data
    domain_groups = get_campaigns_grouped(startDate, endDate)
    if domain:
        domain_groups = [dg for dg in domain_groups if dg["code"] == domain]

    # Derive per-date revenue from domain groups (ensures daily matches totals exactly)
    daily_revenue = {}
    for dg in domain_groups:
        for camp in dg["campaigns"]:
            d = camp["date"]
            if d not in daily_revenue:
                daily_revenue[d] = {
                    "revenue": 0.0,
                    "exl_revenue": 0.0,
                    "combined_revenue": 0.0,
                    "visitors": 0,
                    "total_leads": 0,
                    "conversions": 0,
                    "exl_clicks": 0,
                    "exl_sales": 0,
                }
            daily_revenue[d]["revenue"] += camp["revenue"]
            daily_revenue[d]["exl_revenue"] += camp.get("exl_revenue", 0)
            daily_revenue[d]["combined_revenue"] += camp.get("combined_revenue", 0)
            daily_revenue[d]["visitors"] += camp["visitors"]
            daily_revenue[d]["total_leads"] += camp["total_leads"]
            daily_revenue[d]["conversions"] += camp["conversions"]
            daily_revenue[d]["exl_clicks"] += camp.get("exl_clicks", 0)
            daily_revenue[d]["exl_sales"] += camp.get("exl_sales", 0)

    for row in daily_rows:
        rev = daily_revenue.get(row["date"], {})
        revenue = round(rev.get("revenue", 0.0), 2)
        exl_revenue = round(rev.get("exl_revenue", 0.0), 2)
        combined_revenue = round(rev.get("combined_revenue", 0.0), 2)
        sends = row["sends"]
        clicks = row["clicks"]
        row["revenue"] = revenue
        row["exl_revenue"] = exl_revenue
        row["combined_revenue"] = combined_revenue
        row["visitors"] = rev.get("visitors", 0)
        row["total_leads"] = rev.get("total_leads", 0)
        row["conversions"] = rev.get("conversions", 0)
        row["exl_clicks"] = rev.get("exl_clicks", 0)
        row["exl_sales"] = rev.get("exl_sales", 0)
        row["ecpm"] = (
            round((combined_revenue / sends) * 1000, 2)
            if sends > 0 and combined_revenue > 0
            else 0
        )
        row["epc"] = (
            round(combined_revenue / clicks, 2)
            if clicks > 0 and combined_revenue > 0
            else 0
        )

    # Build domain summary from domain groups
    domain_summary = []
    for dg in domain_groups:
        t = dg["totals"]
        domain_summary.append(
            {
                "name": dg["name"],
                "code": dg["code"],
                "sends": t["sends"],
                "opens": t["opens"],
                "clicks": t["clicks"],
                "bounces": t["bounces"],
                "unsubs": t["unsubs"],
                "revenue": t["revenue"],
                "exl_revenue": t.get("exl_revenue", 0),
                "combined_revenue": t.get("combined_revenue", 0),
                "exl_clicks": t.get("exl_clicks", 0),
                "exl_sales": t.get("exl_sales", 0),
                "conversions": t["conversions"],
                "visitors": t["visitors"],
                "total_leads": t["total_leads"],
                "open_pct": t["open_percent"],
                "click_pct": t["click_percent"],
                "ecpm": t["ecpm"],
                "epc": t["epc"],
            }
        )

    # Grand totals
    tot_sends = sum(d["sends"] for d in domain_summary)
    tot_opens = sum(d["opens"] for d in domain_summary)
    tot_clicks = sum(d["clicks"] for d in domain_summary)
    tot_bounces = sum(d["bounces"] for d in domain_summary)
    tot_unsubs = sum(d["unsubs"] for d in domain_summary)
    tot_revenue = sum(d["revenue"] for d in domain_summary)
    tot_exl_revenue = sum(d["exl_revenue"] for d in domain_summary)
    tot_combined_revenue = sum(d["combined_revenue"] for d in domain_summary)
    tot_exl_clicks = sum(d["exl_clicks"] for d in domain_summary)
    tot_exl_sales = sum(d["exl_sales"] for d in domain_summary)
    tot_conversions = sum(d["conversions"] for d in domain_summary)
    tot_visitors = sum(d["visitors"] for d in domain_summary)
    tot_total_leads = sum(d["total_leads"] for d in domain_summary)

    totals = {
        "sends": tot_sends,
        "opens": tot_opens,
        "clicks": tot_clicks,
        "bounces": tot_bounces,
        "unsubs": tot_unsubs,
        "revenue": round(tot_revenue, 2),
        "exl_revenue": round(tot_exl_revenue, 2),
        "combined_revenue": round(tot_combined_revenue, 2),
        "exl_clicks": tot_exl_clicks,
        "exl_sales": tot_exl_sales,
        "conversions": tot_conversions,
        "visitors": tot_visitors,
        "total_leads": tot_total_leads,
        "open_pct": round((tot_opens / tot_sends) * 100, 2) if tot_sends > 0 else 0,
        "click_pct": round((tot_clicks / tot_sends) * 100, 2) if tot_sends > 0 else 0,
        "ecpm": (
            round((tot_combined_revenue / tot_sends) * 1000, 2)
            if tot_sends > 0 and tot_combined_revenue > 0
            else 0
        ),
        "epc": (
            round(tot_combined_revenue / tot_clicks, 2)
            if tot_clicks > 0 and tot_combined_revenue > 0
            else 0
        ),
    }

    return {
        "success": True,
        "startDate": startDate,
        "endDate": endDate,
        "daily": daily_rows,
        "domains": domain_summary,
        "totals": totals,
        "selectedDomain": domain,
    }


# ──────────────────────────────────────────────────────────────────────
# API: Spillover — live Leadpier call (no DB caching)
# ──────────────────────────────────────────────────────────────────────
@app.get("/api/spillover")
async def api_spillover(
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    """
    For each enabled domain, call Leadpier twice:
      1) %{SHORT_CODE}% on `date` → total domain revenue today
      2) %{MMDD}-{SHORT_CODE}% on `date` → revenue from today's campaigns only
    Spillover = total - today's campaigns.

    Also computes ExcelTrack spillover using cached c3 data.

    Short codes are extracted from actual campaign names in the DB
    (pattern: MMDD-{SHORT}-eN), not from the domain code suffix.
    """
    from leadpier_api import LeadpierAPI
    from exltrk_api import ExltrkAPI
    import asyncio
    import re as _re
    from datetime import timedelta as _td

    lp = LeadpierAPI()
    domains = get_all_domains()

    # Build MMDD from the date (e.g. "2026-03-14" → "0314")
    mmdd = date[5:7] + date[8:10]

    # Get campaigns from last 90 days to reliably map domain codes → actual short codes
    mapping_start = (datetime.strptime(date, "%Y-%m-%d") - _td(days=90)).strftime(
        "%Y-%m-%d"
    )
    all_campaigns = get_campaigns_by_date_range(mapping_start, date)
    # Build domain_code → set of short codes from campaign names
    domain_shorts: dict[str, set[str]] = {}
    pattern = _re.compile(r"^\d{4}-([a-zA-Z]+)-")
    for c in all_campaigns:
        m = pattern.match(c["campaign_name"])
        if m:
            domain_shorts.setdefault(c["domain_code"], set()).add(m.group(1).lower())

    # Compute ExcelTrack spillover from cached c3 data
    # Total EXL revenue for date = all c3 entries for that date
    # Today's EXL = only c3 entries matching today's campaign cores (MMDD-*)
    from database import get_exltrk_sources_by_date
    from leadpier_api import _extract_core

    exl_sources = get_exltrk_sources_by_date(date)
    # Build total EXL revenue per domain short code
    # c3 format: "MMDD-SHORT-eN" → domain short = second part if multi-part, else whole
    exl_total_by_domain: dict[str, float] = {}
    exl_today_by_domain: dict[str, float] = {}

    # Map c3 → domain: extract short code from c3 value
    for src in exl_sources:
        c3 = src.get("c3", "")
        earned = float(src.get("earned", 0) or 0)
        # c3 is a core name like "0314-ivr-e3" or "0314-AFW-e4"
        parts = c3.split("-")
        if len(parts) >= 2:
            short = parts[1].lower()
        else:
            short = c3.lower()

        # Find which domain code this short belongs to
        for dcode, shorts_set in domain_shorts.items():
            if short in shorts_set:
                exl_total_by_domain[dcode] = exl_total_by_domain.get(dcode, 0) + earned
                # Check if this c3 is from today's campaigns (starts with MMDD)
                if c3.startswith(mmdd):
                    exl_today_by_domain[dcode] = (
                        exl_today_by_domain.get(dcode, 0) + earned
                    )
                break

    async def fetch_domain_spillover(d):
        code = d["code"]  # e.g. "P2_AFW"
        shorts = domain_shorts.get(code, set())

        if not shorts:
            # Fallback: derive from domain code suffix
            shorts = {(code.split("_", 1)[1] if "_" in code else code).lower()}

        try:
            # Aggregate across all short codes for this domain
            total_revenue = 0.0
            total_visitors = 0
            total_leads = 0
            total_sold = 0
            today_revenue = 0.0
            today_visitors = 0
            today_leads = 0
            today_sold = 0

            for short in shorts:
                # 1) Total domain revenue on this date
                total_data = await lp.get_sources_filtered(date, date, f"%{short}%")
                tt = total_data.get("totals", {})
                total_revenue += float(tt.get("totalRevenue", 0) or 0)
                total_visitors += int(tt.get("visitors", 0) or 0)
                total_leads += int(tt.get("totalLeads", 0) or 0)
                total_sold += int(tt.get("soldLeads", 0) or 0)

                # 2) Today's campaigns only (source pattern: %MMDD-SHORT%)
                today_data = await lp.get_sources_filtered(
                    date, date, f"%{mmdd}-{short}%"
                )
                td = today_data.get("totals", {})
                today_revenue += float(td.get("totalRevenue", 0) or 0)
                today_visitors += int(td.get("visitors", 0) or 0)
                today_leads += int(td.get("totalLeads", 0) or 0)
                today_sold += int(td.get("soldLeads", 0) or 0)

            return {
                "code": code,
                "name": d["name"],
                "total_revenue": round(total_revenue, 2),
                "total_visitors": total_visitors,
                "total_leads": total_leads,
                "total_sold": total_sold,
                "today_revenue": round(today_revenue, 2),
                "today_visitors": today_visitors,
                "today_leads": today_leads,
                "today_sold": today_sold,
                "spillover_revenue": round(total_revenue - today_revenue, 2),
                "spillover_visitors": total_visitors - today_visitors,
                "spillover_leads": total_leads - today_leads,
                "spillover_sold": total_sold - today_sold,
                # ExcelTrack spillover
                "exl_total_revenue": round(exl_total_by_domain.get(code, 0), 2),
                "exl_today_revenue": round(exl_today_by_domain.get(code, 0), 2),
                "exl_spillover_revenue": round(
                    exl_total_by_domain.get(code, 0) - exl_today_by_domain.get(code, 0),
                    2,
                ),
            }
        except Exception as e:
            logger.warning("Spillover fetch failed for %s: %s", code, e)
            return {
                "code": code,
                "name": d["name"],
                "error": str(e),
                "total_revenue": 0,
                "today_revenue": 0,
                "spillover_revenue": 0,
                "spillover_visitors": 0,
                "spillover_leads": 0,
                "spillover_sold": 0,
                "exl_total_revenue": 0,
                "exl_today_revenue": 0,
                "exl_spillover_revenue": 0,
            }

    results = await asyncio.gather(*[fetch_domain_spillover(d) for d in domains])

    return {"success": True, "date": date, "domains": list(results)}


# ──────────────────────────────────────────────────────────────────────
# API: Utility endpoints
# ──────────────────────────────────────────────────────────────────────
@app.get("/api/domains")
async def api_domains():
    domains = get_all_domains()
    return {"success": True, "domains": domains}


@app.get("/api/health")
async def api_health():
    return {
        "success": True,
        "status": "running",
        "timestamp": datetime.now(pytz.timezone(TIMEZONE)).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "timezone": TIMEZONE,
    }


# ──────────────────────────────────────────────────────────────────────
# API: Domain management (super admin only)
# ──────────────────────────────────────────────────────────────────────
@app.get("/api/admin/domains")
async def api_admin_domains(
    search: str = Query(""),
    page: int = Query(1, ge=1),
):
    """Paginated domain list with search."""
    result = get_all_domains_admin(search=search, page=page, per_page=15)
    return {"success": True, **result}


@app.get("/api/admin/domains/{domain_id}")
async def api_admin_domain_detail(domain_id: int):
    """Get a single domain."""
    domain = get_domain_by_id(domain_id)
    if not domain:
        return JSONResponse(
            status_code=404, content={"success": False, "error": "Domain not found"}
        )
    return {"success": True, "domain": domain}


@app.post("/api/admin/domains")
async def api_admin_domain_create(request: Request):
    """Create a new domain."""
    try:
        data = await request.json()
        required = ["code", "name", "api_url", "username", "usertoken", "le_domain"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Missing fields: {', '.join(missing)}",
                },
            )
        domain = create_domain(data)
        return {"success": True, "domain": domain}
    except ValueError as e:
        return JSONResponse(
            status_code=400, content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


@app.put("/api/admin/domains/{domain_id}")
async def api_admin_domain_update(domain_id: int, request: Request):
    """Update an existing domain."""
    try:
        data = await request.json()
        domain = update_domain(domain_id, data)
        if not domain:
            return JSONResponse(
                status_code=404, content={"success": False, "error": "Domain not found"}
            )
        return {"success": True, "domain": domain}
    except ValueError as e:
        return JSONResponse(
            status_code=400, content={"success": False, "error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


@app.delete("/api/admin/domains/{domain_id}")
async def api_admin_domain_delete(domain_id: int):
    """Delete a domain and all its campaigns."""
    try:
        deleted = delete_domain(domain_id)
        if not deleted:
            return JSONResponse(
                status_code=404, content={"success": False, "error": "Domain not found"}
            )
        return {"success": True, "message": "Domain deleted"}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


@app.get("/api/me")
async def api_me(request: Request):
    """Return current user info."""
    return {
        "success": True,
        "username": request.session.get("username", ""),
        "role": request.session.get("role", "user"),
    }


@app.post("/api/cleanup")
async def api_cleanup():
    """Manually trigger cleanup of data older than 30 days."""
    try:
        result = cleanup_old_data(days=30)
        return {"success": True, **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.get("/api/debug/test-pinpointe")
async def api_debug_test():
    """Quick diagnostic: call GetNewslettersSent for first domain and report."""
    from pinpoint_api import PinpointAPI

    first_code = next(iter(DOMAINS))
    domain = DOMAINS[first_code]
    api = PinpointAPI()
    try:
        campaigns = await api.get_campaigns_sent(domain, 3, "days")
        return {
            "success": True,
            "domain": domain["name"],
            "campaigns_found": len(campaigns),
            "sample": campaigns[:3] if campaigns else [],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "domain": domain["name"],
                "error": str(e),
            },
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
