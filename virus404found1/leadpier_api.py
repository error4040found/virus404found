"""
leadpier_api.py - Leadpier Revenue API client

Authenticates with webapi.leadpier.com and fetches source-level
revenue statistics.  The matching logic maps Leadpier source names
(e.g. "mta-b_0216-cfl-e3") to Insight Bridge campaign names ("0216-cfl-e3").

Ported from:
  - new_project/login_request.py  (auth flow)
  - new_project/get_data.py       (data fetch)
  - stats/api/LeadpierAPI.php     (matching algorithm)
"""

import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from config import (
    LEADPIER_AUTH_URL,
    LEADPIER_DATA_URL,
    LEADPIER_USERNAME,
    LEADPIER_PASSWORD,
    LEADPIER_TOKEN_FILE,
    LEADPIER_TOKEN_EXPIRY_HOURS,
)

logger = logging.getLogger("leadpier_api")

# ─── Core-name extraction for improved matching ─────────────────
_CORE_RE = re.compile(r"(?<!\d)(\d{4}-.+)$")
_PREFIX_ROOT_RE = re.compile(r"^([a-z]+)")


def _extract_core(name: str) -> str | None:
    """Extract the date-code core (e.g. '0316-afw-e2') from a source or campaign name."""
    m = _CORE_RE.search(name.lower())
    return m.group(1) if m else None


def _extract_prefix_root(name: str) -> str:
    """Extract the leading alphabetic prefix root (e.g. 'mta' from 'mta-b_0316-afw-e2')."""
    m = _PREFIX_ROOT_RE.match(name.lower())
    return m.group(1) if m else ""


def _platform_compatible(campaign_lower: str, source_lower: str) -> bool:
    """Check whether campaign and source share the same platform prefix root.

    Dynamically compares the leading alphabetic segment of each name.
    e.g. mta_… ↔ mta-b_… both have root 'mta' → compatible.
         mta_… ↔ spg_…  roots differ → incompatible.
    """
    camp_root = _extract_prefix_root(campaign_lower)
    src_root = _extract_prefix_root(source_lower)
    if not camp_root or not src_root:
        return False
    # Match if roots are the same or one is a prefix of the other (min 3 chars)
    shorter, longer = sorted((camp_root, src_root), key=len)
    return len(shorter) >= 3 and longer.startswith(shorter)


class LeadpierAPI:
    """Async client for the Leadpier revenue API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._token: str | None = None
        self._token_time: datetime | None = None
        self._load_saved_token()

    # ─── Token persistence ──────────────────────────────────────
    def _load_saved_token(self) -> None:
        """Load token + timestamp from disk cache."""
        try:
            path = Path(LEADPIER_TOKEN_FILE)
            if path.exists():
                data = json.loads(path.read_text())
                self._token = data.get("token")
                ts = data.get("last_login_time")
                if ts:
                    self._token_time = datetime.fromisoformat(ts)
                logger.debug("Loaded saved Leadpier token")
        except Exception as exc:
            logger.warning("Could not load saved token: %s", exc)

    def _save_token(self) -> None:
        """Persist token + timestamp to disk."""
        try:
            path = Path(LEADPIER_TOKEN_FILE)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "token": self._token,
                        "last_login_time": (
                            self._token_time.isoformat() if self._token_time else None
                        ),
                    },
                    indent=2,
                )
            )
        except Exception as exc:
            logger.warning("Could not save token: %s", exc)

    def _is_token_valid(self) -> bool:
        if not self._token or not self._token_time:
            return False
        elapsed = datetime.now() - self._token_time
        return elapsed < timedelta(hours=LEADPIER_TOKEN_EXPIRY_HOURS)

    # ─── Authentication ─────────────────────────────────────────
    async def _authenticate(self) -> str:
        """Login to Leadpier and return bearer token."""
        logger.info("Authenticating with Leadpier...")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                LEADPIER_AUTH_URL,
                json={
                    "username": LEADPIER_USERNAME,
                    "password": LEADPIER_PASSWORD,
                },
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "origin": "https://dash.leadpier.com",
                    "referer": "https://dash.leadpier.com/",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("errorCode") != "NO_ERROR":
            raise RuntimeError(f"Leadpier auth failed: {data.get('errorCode')}")

        token = data["data"]["token"]
        self._token = token
        self._token_time = datetime.now()
        self._save_token()
        logger.info("Leadpier authentication successful")
        return token

    async def _get_token(self) -> str:
        """Return a valid token, refreshing if needed."""
        if self._is_token_valid():
            return self._token  # type: ignore
        return await self._authenticate()

    # ─── Fetch source statistics ────────────────────────────────
    async def get_sources(
        self,
        period_from: str,
        period_to: str,
    ) -> list[dict[str, Any]]:
        """
        Fetch source-level revenue data from Leadpier (with pagination).

        Returns list of dicts with keys:
          source, visitors, totalLeads, soldLeads, totalRevenue, EPL, EPV, ...
        """
        token = await self._get_token()

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"bearer {token}",
            "origin": "https://dash.leadpier.com",
            "referer": "https://dash.leadpier.com/",
        }

        all_stats: list[dict] = []
        offset = 0
        limit = 1000

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                payload = {
                    "limit": limit,
                    "offset": offset,
                    "orderBy": "totalRevenue",
                    "orderDirection": "DESC",
                    "periodFrom": period_from,
                    "periodTo": period_to,
                }

                resp = await client.post(
                    LEADPIER_DATA_URL,
                    json=payload,
                    headers=headers,
                )

                # Token may have expired server-side
                if resp.status_code in (401, 403):
                    logger.warning("Leadpier token rejected, re-authenticating...")
                    token = await self._authenticate()
                    headers["authorization"] = f"bearer {token}"
                    resp = await client.post(
                        LEADPIER_DATA_URL,
                        json=payload,
                        headers=headers,
                    )

                resp.raise_for_status()
                data = resp.json()

                page_stats = data.get("data", {}).get("statistics", [])
                all_stats.extend(page_stats)

                total_count = int(data.get("data", {}).get("count", 0) or 0)
                if len(all_stats) >= total_count or len(page_stats) < limit:
                    break
                offset += limit

        logger.info(
            "Leadpier: %d sources for %s → %s", len(all_stats), period_from, period_to
        )
        return all_stats

    # ─── Matching algorithm ─────────────────────────────────────
    @staticmethod
    def match_source_to_campaign(
        sources: list[dict], campaign_name: str
    ) -> dict[str, Any] | None:
        """
        Match Leadpier source records to a Insight Bridge campaign name.

        Matching rules (all case-insensitive):
          1. Exact match:  source == campaign_name
          2. Underscore suffix: source ends with _campaign_name
          3. Source-prefix:  source matches ^source\\d+[-_]campaign_name$
          4. Dash-contains:  source contains -campaign_name
          5. Core-name:  extract MMDD-domain-segment core from both,
                         match only if platform prefixes are compatible

        Multiple sources can match → metrics are SUMMED.
        """
        cn_lower = campaign_name.lower()
        cn_core = _extract_core(cn_lower)
        total_revenue = 0.0
        total_visitors = 0
        total_leads = 0
        total_sold = 0
        matched = False

        for src in sources:
            sn = (src.get("source") or "").lower()
            if not sn:
                continue

            hit = (
                sn == cn_lower
                or sn.endswith(f"_{cn_lower}")
                or bool(re.match(r"^source\d+[-_]" + re.escape(cn_lower) + r"$", sn))
                or f"-{cn_lower}" in sn
            )

            # Rule 5: core-name matching with platform awareness
            if not hit and cn_core and cn_core != cn_lower:
                sn_core = _extract_core(sn)
                if sn_core == cn_core and _platform_compatible(cn_lower, sn):
                    hit = True

            if hit:
                matched = True
                total_revenue += float(src.get("totalRevenue", 0) or 0)
                total_visitors += int(src.get("visitors", 0) or 0)
                total_leads += int(src.get("totalLeads", 0) or 0)
                total_sold += int(src.get("soldLeads", 0) or 0)

        if not matched:
            return None

        return {
            "revenue": round(total_revenue, 2),
            "visitors": total_visitors,
            "leads": total_leads,
            "sold_leads": total_sold,
        }

    # ─── Convenience: match all campaigns at once ───────────────
    @staticmethod
    def match_all_campaigns(
        sources: list[dict], campaign_names: list[str]
    ) -> dict[str, dict]:
        """
        Match a list of campaign names against Leadpier sources.
        Returns {campaign_name: {revenue, visitors, leads, sold_leads}} for matches.
        Deduplicates campaign names to avoid redundant matching work.
        """
        result: dict[str, dict] = {}
        for cn in dict.fromkeys(campaign_names):  # deduplicate, preserve order
            m = LeadpierAPI.match_source_to_campaign(sources, cn)
            if m:
                result[cn] = m
        return result

    # ─── Filtered source fetch (for spillover) ──────────────────
    async def get_sources_filtered(
        self,
        period_from: str,
        period_to: str,
        source_filter: str,
    ) -> dict:
        """
        Fetch source-level revenue data filtered by a source pattern
        (SQL LIKE syntax, e.g. '%AFW%').
        Returns the full data dict with 'statistics' and 'totals'.
        """
        token = await self._get_token()

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"bearer {token}",
            "origin": "https://dash.leadpier.com",
            "referer": "https://dash.leadpier.com/",
        }
        payload = {
            "limit": 50,
            "offset": 0,
            "orderBy": "totalRevenue",
            "orderDirection": "DESC",
            "periodFrom": period_from,
            "periodTo": period_to,
            "source": source_filter,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                LEADPIER_DATA_URL,
                json=payload,
                headers=headers,
            )

            if resp.status_code in (401, 403):
                logger.warning("Leadpier token rejected, re-authenticating...")
                token = await self._authenticate()
                headers["authorization"] = f"bearer {token}"
                resp = await client.post(
                    LEADPIER_DATA_URL,
                    json=payload,
                    headers=headers,
                )

            resp.raise_for_status()
            data = resp.json()

        return data.get("data", {})
