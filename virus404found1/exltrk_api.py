"""
exltrk_api.py - ExcelTrack Partner API client

Fetches SubID reports from partner.exltrk.com grouped by c3.
The c3 values are campaign core names (e.g. "0314-ivr-e3") that
map directly to the core portion of Pinpointe campaign names.

Uses Bearer token authentication with a long-lived JWT token.
"""

import logging
from typing import Any

import httpx

from config import EXLTRK_API_URL, EXLTRK_API_TOKEN

logger = logging.getLogger("exltrk_api")


class ExltrkAPI:
    """Client for the ExcelTrack Partner API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    # ─── Fetch SubID report ─────────────────────────────────────
    async def get_subid_report(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        Fetch SubID report grouped by c3 with pagination.

        start_date/end_date: YYYY-MM-DD format
        Returns list of dicts with keys: c3, clicks, sales, earned, conv, epc
        """
        if not EXLTRK_API_TOKEN:
            logger.warning("ExcelTrack API token not configured, skipping")
            return []

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {EXLTRK_API_TOKEN}",
        }

        all_data: list[dict] = []
        page = 1
        records_per_page = 500

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                params = {
                    "start": start_date,
                    "end": end_date,
                    "group_by": "c3",
                    "currency_id": 1,
                    "campaign_aggregate": "true",
                    "page": page,
                    "records": records_per_page,
                    "order": "id",
                    "direction": "asc",
                }

                resp = await client.get(
                    f"{EXLTRK_API_URL}/reports/subid",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                page_data = data.get("data", [])
                all_data.extend(page_data)

                meta = data.get("meta", {})
                current_page = meta.get("current_page", 1)
                last_page = meta.get("last_page", 1)

                if current_page >= last_page:
                    break
                page += 1

        logger.info(
            "ExcelTrack: %d c3 entries for %s → %s",
            len(all_data),
            start_date,
            end_date,
        )
        return all_data

    # ─── Matching algorithm ─────────────────────────────────────
    @staticmethod
    def match_c3_to_campaign(
        c3_data: list[dict], campaign_name: str
    ) -> dict[str, Any] | None:
        """
        Match ExcelTrack c3 entries to a campaign name.

        Extracts the core from campaign_name (e.g. "mta_0314-ivr-e3" → "0314-ivr-e3")
        and matches against c3 values.
        """
        from leadpier_api import _extract_core

        cn_core = _extract_core(campaign_name.lower())
        if not cn_core:
            return None

        total_earned = 0.0
        total_clicks = 0
        total_sales = 0
        total_conv = 0
        matched = False

        for entry in c3_data:
            c3 = (entry.get("c3") or "").lower().strip()
            if not c3:
                continue

            if c3 == cn_core:
                matched = True
                total_earned += float(entry.get("earned", 0) or 0)
                total_clicks += int(entry.get("clicks", 0) or 0)
                total_sales += int(entry.get("sales", 0) or 0)
                total_conv += int(entry.get("conv", 0) or 0)

        if not matched:
            return None

        return {
            "earned": round(total_earned, 2),
            "clicks": total_clicks,
            "sales": total_sales,
            "conv": total_conv,
        }

    # ─── Convenience: match all campaigns at once ───────────────
    @staticmethod
    def match_all_campaigns(
        c3_data: list[dict], campaign_names: list[str]
    ) -> dict[str, dict]:
        """
        Match a list of campaign names against ExcelTrack c3 data.
        Returns {campaign_name: {earned, clicks, sales, conv}} for matches.
        Deduplicates campaign names to avoid redundant matching work.
        """
        result: dict[str, dict] = {}
        for cn in dict.fromkeys(campaign_names):  # deduplicate, preserve order
            m = ExltrkAPI.match_c3_to_campaign(c3_data, cn)
            if m:
                result[cn] = m
        return result
