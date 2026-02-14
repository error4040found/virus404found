import requests
import json
import logging
from datetime import datetime
from pytz import timezone
from config import LE_API_URL, TIMEZONE

# Configure logger
logger = logging.getLogger(__name__)


def transform_leadpier_to_le_format(source_data, report_date):
    """
    Transform LeadPier source statistics to LE API format

    Args:
        source_data: Single source record from LeadPier API
        report_date: Date in YYYY-MM-DD format

    Returns:
        Transformed data in LE API format
    """
    # Extract campaign code from source field
    # Example: "vr-b-oZaR5m-t-mlYq6o-0213"
    campaign_code = source_data.get("source", "")

    # Get metrics from LeadPier data
    visitors = int(source_data.get("visitors", 0))
    total_leads = int(source_data.get("totalLeads", 0))
    sold_leads = int(source_data.get("soldLeads", 0))
    total_revenue = float(source_data.get("totalRevenue", 0))

    # Calculate percentages and metrics
    lead_percent = float(source_data.get("conversionRate", 0))
    sale_percent = float(source_data.get("soldRate", 0))

    # Calculate EPC (Earnings Per Click) and RPC (Revenue Per Click)
    epc = round(total_revenue / visitors, 2) if visitors > 0 else 0.0
    rpc = epc  # RPC is same as EPV (earnings per visitor)

    return {
        "campaign_code": campaign_code,
        "clicks": visitors,  # Using visitors as clicks
        "leads": total_leads,
        "lead_percent": round(lead_percent, 2),
        "sales": sold_leads,
        "sale_percent": round(sale_percent, 2),
        "revenue": round(total_revenue, 2),
        "epc": round(float(source_data.get("EPL", 0)), 2),  # Earnings per lead
        "rpc": rpc,  # Revenue per click (visitor)
    }


def send_to_le_api(
    report_date,
    data_list,
    api_url=LE_API_URL,
):
    """
    Send transformed data to LE API using PUT request

    Args:
        report_date: Date in YYYY-MM-DD format
        data_list: List of transformed data records
        api_url: LE API endpoint URL

    Returns:
        API response or None if failed
    """
    payload = {"report_date": report_date, "data": data_list}

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        logger.info(f"Sending PUT request to LE API...")
        logger.info(f"Report Date: {report_date}")
        logger.info(f"Total Records: {len(data_list)}")

        response = requests.put(api_url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()

        if result.get("success"):
            logger.info(f"Successfully sent data to LE API")
            logger.info(f"  Matched: {result.get('matched', 0)}")
            logger.info(f"  Unmatched: {result.get('unmatched', 0)}")
            logger.info(f"  Total Processed: {result.get('total_received', 0)}")

            if result.get("details"):
                logger.info(f"--- Sample Matched Records ---")
                for i, detail in enumerate(result.get("details", [])[:3], 1):
                    logger.info(
                        f"{i}. {detail.get('le_code')} → {detail.get('domain')}"
                    )
                    logger.info(f"   PP Campaign: {detail.get('pp_campaign')}")
                    logger.info(
                        f"   Sends: {detail.get('sends')}, Revenue: ${detail.get('revenue')}"
                    )

            if result.get("errors"):
                logger.warning(f"Errors encountered:")
                for error in result.get("errors", []):
                    logger.warning(f"  - {error}")
        else:
            logger.error(f"LE API returned failure: {result.get('message')}")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


def process_and_send_leadpier_data(leadpier_response, report_date=None):
    """
    Process LeadPier API response and send to LE API

    Args:
        leadpier_response: Full response from LeadPier API
        report_date: Optional date override (defaults to Indian timezone current date)

    Returns:
        LE API response
    """
    if not leadpier_response or not leadpier_response.get("data"):
        logger.error("No data to process from LeadPier response")
        return None

    # Get report date
    if not report_date:
        ist = timezone("Asia/Kolkata")
        report_date = datetime.now(ist).strftime("%Y-%m-%d")

    # Extract statistics from LeadPier response
    statistics = leadpier_response.get("data", {}).get("statistics", [])

    if not statistics:
        logger.error("No statistics found in LeadPier response")
        return None

    # Transform each record
    transformed_data = []
    for source_record in statistics:
        # Only include records with actual data (visitors > 0)
        if int(source_record.get("visitors", 0)) > 0:
            transformed = transform_leadpier_to_le_format(source_record, report_date)
            transformed_data.append(transformed)

    logger.info(
        f"Transformed {len(transformed_data)} records (filtered from {len(statistics)} total)"
    )

    if not transformed_data:
        logger.error("No valid records to send after filtering")
        return None

    # Send to LE API
    return send_to_le_api(report_date, transformed_data)


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Example usage - this would typically be called from get_data.py
    from get_data import get_source_statistics

    logger.info("Fetching data from LeadPier API...")
    leadpier_data = get_source_statistics()

    if leadpier_data:
        logger.info("=" * 60)
        result = process_and_send_leadpier_data(leadpier_data)

        if result:
            logger.info("Data pipeline completed successfully!")
        else:
            logger.error("Failed to complete data pipeline")
    else:
        logger.error("Failed to fetch data from LeadPier")
