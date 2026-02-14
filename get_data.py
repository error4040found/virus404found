import requests
import json
import logging
from datetime import datetime, timedelta
from pytz import timezone
from login_request import login
from config import LEADPIER_DATA_URL, SOURCE_JSON, TOKEN_EXPIRY_HOURS, TIMEZONE

# Configure logger
logger = logging.getLogger(__name__)


def get_token_and_login_time():
    """
    Read token and last login time from source.json file
    """
    try:
        with open(SOURCE_JSON, "r") as f:
            data = json.load(f)
            return data.get("token"), data.get("last_login_time")
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None


def is_token_expired(last_login_time_str, hours=TOKEN_EXPIRY_HOURS):
    """
    Check if the token is expired based on last login time

    Args:
        last_login_time_str: ISO format timestamp string
        hours: Number of hours to consider token valid (from config)

    Returns:
        True if token is expired, False otherwise
    """
    if not last_login_time_str:
        return True

    try:
        # Parse the last login time
        last_login_time = datetime.fromisoformat(last_login_time_str)

        # Get current time
        current_time = datetime.now()

        # Calculate time difference
        time_diff = current_time - last_login_time

        # Check if more than specified hours have passed
        if time_diff > timedelta(hours=hours):
            logger.info(
                f"Token expired: Last login was {time_diff.total_seconds() / 3600:.2f} hours ago"
            )
            return True
        else:
            remaining_time = timedelta(hours=hours) - time_diff
            logger.info(
                f"Token valid: {remaining_time.total_seconds() / 60:.1f} minutes remaining"
            )
            return False

    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing login time: {e}")
        return True


def get_source_statistics(period_from=None, period_to=None, retry_count=0):
    """
    Fetch source statistics from LeadPier API with automatic token refresh

    Args:
        period_from: Start date (YYYY-MM-DD format), defaults to today in IST
        period_to: End date (YYYY-MM-DD format), defaults to today in IST
        retry_count: Internal counter to prevent infinite retry loops
    """
    # Get current date in Indian timezone if not provided
    if not period_from or not period_to:
        ist = timezone(TIMEZONE)
        current_date_ist = datetime.now(ist).strftime("%Y-%m-%d")
        period_from = period_from or current_date_ist
        period_to = period_to or current_date_ist

    logger.info(f"Fetching data for period: {period_from} to {period_to}")

    # Get token and last login time from source.json
    token, last_login_time = get_token_and_login_time()

    # Check if token exists and is not expired
    if not token or is_token_expired(last_login_time):
        logger.info("Token is missing or expired. Logging in...")
        login()
        token, last_login_time = get_token_and_login_time()

        if not token:
            logger.error("Failed to obtain token after login")
            return None

    url = LEADPIER_DATA_URL

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"bearer {token}",
        "origin": "https://dash.leadpier.com",
        "referer": "https://dash.leadpier.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }

    payload = {
        "limit": 1000,
        "offset": 0,
        "orderBy": "source",
        "orderDirection": "DESC",
        "periodFrom": period_from,
        "periodTo": period_to,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        # Check if token expired or unauthorized
        if response.status_code == 401 or response.status_code == 403:
            if retry_count < 2:  # Prevent infinite loops
                logger.warning("Token expired or unauthorized. Refreshing token...")
                login()
                return get_source_statistics(period_from, period_to, retry_count + 1)
            else:
                logger.error("Failed to authenticate after multiple attempts")
                return None

        response.raise_for_status()
        data = response.json()

        if data.get("errorCode") == "NO_ERROR" or not data.get("errorCode"):
            statistics = data.get("data", {})
            count = statistics.get("count", 0)
            stats_list = statistics.get("statistics", [])

            logger.info(f"Successfully fetched {count} source records")
            logger.info(f"Retrieved {len(stats_list)} statistics entries")

            # Display summary of top sources
            if stats_list:
                logger.info("--- Top 5 Sources ---")
                for i, stat in enumerate(stats_list[:5], 1):
                    logger.info(f"{i}. Source: {stat.get('source')}")
                    logger.info(
                        f"   Visitors: {stat.get('visitors')}, Total Leads: {stat.get('totalLeads')}, Revenue: ${stat.get('totalRevenue')}"
                    )
                    logger.info(
                        f"   Conversion Rate: {stat.get('conversionRate')}%, Sold Leads: {stat.get('soldLeads')}"
                    )

            return data
        else:
            logger.error(f"API Error: {data.get('errorCode')}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get data for today (Indian timezone)
    result = get_source_statistics()

    # Optionally save to a file
    if result:
        ist = timezone("Asia/Kolkata")
        timestamp = datetime.now(ist).strftime("%Y%m%d_%H%M%S")
        filename = f"source_stats_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(result, f, indent=4)

        logger.info(f"Data saved to {filename}")

        # Send data to LE API
        logger.info("=" * 60)
        logger.info("Sending data to LE API...")
        logger.info("=" * 60)

        from post_or_put import process_and_send_leadpier_data

        le_response = process_and_send_leadpier_data(result)

        if le_response:
            logger.info("Complete pipeline executed successfully!")
        else:
            logger.warning("Data fetched but LE API submission failed")
