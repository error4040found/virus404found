import requests
import json
import logging
from datetime import datetime
from config import (
    LEADPIER_AUTH_URL,
    LEADPIER_USERNAME,
    LEADPIER_PASSWORD,
    SOURCE_JSON,
)

# Configure logger
logger = logging.getLogger(__name__)


def login():
    """
    Authenticate with the LeadPier API and update last login time in source.json
    """
    url = LEADPIER_AUTH_URL

    credentials = {"username": LEADPIER_USERNAME, "password": LEADPIER_PASSWORD}

    # Headers to mimic browser request
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://dash.leadpier.com",
        "referer": "https://dash.leadpier.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }

    try:
        # Send login request
        logger.info("Sending login request...")
        response = requests.post(url, json=credentials, headers=headers)
        response.raise_for_status()

        # Parse response
        data = response.json()

        if data.get("errorCode") == "NO_ERROR":
            logger.info("Login successful!")
            logger.info(f"Token: {data['data']['token'][:50]}...")
            logger.info(f"User: {data['data']['firstName']} {data['data']['lastName']}")

            # Update source.json with last login time and token
            current_time = datetime.now().isoformat()

            # Read existing source.json data
            try:
                with open(SOURCE_JSON, "r") as f:
                    source_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                source_data = {}

            # Update with new login information
            source_data["last_login_time"] = current_time
            source_data["token"] = data["data"]["token"]
            source_data["user_email"] = data["data"]["email"]
            source_data["user_name"] = (
                f"{data['data']['firstName']} {data['data']['lastName']}"
            )

            # Write back to source.json
            with open(SOURCE_JSON, "w") as f:
                json.dump(source_data, f, indent=4)

            logger.info(f"Last login time updated in source.json: {current_time}")

            return data
        else:
            logger.error(f"Login failed: {data.get('errorCode')}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    login()
