# """
# Test script to verify FastAPI endpoints
# """

# import requests

# base_url = "http://localhost:8000"

# print("Testing LeadPier Data Sync Service API\n")
# print("=" * 60)

# # Test health endpoint
# print("\n1. Testing /health endpoint...")
# try:
#     response = requests.get(f"{base_url}/health")
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.json()}\n")
# except Exception as e:
#     print(f"Error: {e}\n")

# # Test root endpoint
# print("2. Testing / (root) endpoint...")
# try:
#     response = requests.get(f"{base_url}/")
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.json()}\n")
# except Exception as e:
#     print(f"Error: {e}\n")

# # Test status endpoint
# print("3. Testing /status endpoint...")
# try:
#     response = requests.get(f"{base_url}/status")
#     print(f"Status Code: {response.status_code}")
#     print(f"Response:")
#     import json

#     print(json.dumps(response.json(), indent=2))
# except Exception as e:
#     print(f"Error: {e}\n")

# # Test logs endpoint
# print("\n4. Testing /logs endpoint (last 10 lines)...")
# try:
#     response = requests.get(f"{base_url}/logs?lines=10")
#     print(f"Status Code: {response.status_code}")
#     data = response.json()
#     print(f"Log file: {data['log_file']}")
#     print(f"Total lines: {data['total_lines']}")
#     print(f"Showing: {data['showing']} lines\n")
#     print("Recent logs:")
#     for log in data["logs"][-5:]:
#         print(f"  {log}")
# except Exception as e:
#     print(f"Error: {e}\n")

# print("\n" + "=" * 60)
# print("API URL: http://localhost:8000")
# print("Docs URL: http://localhost:8000/docs")
# print("=" * 60)


import requests

LE_API_URL = "https://app.shaktallc.com/email_dashboard/stats/le_api.php"

headers = {"Content-Type": "application/json"}

payload = {
    "report_date": "2026-02-13",
    "data": [
        {
            "campaign_code": "mta-b_0213-lbe-e2",
            "clicks": 111111111111111,
            "leads": 11111111111111111111,
            "lead_percent": 45.00,
            "sales": 1111111111111111111,
            "sale_percent": 33.33,
            "revenue": 10.24,
            "epc": 1.14,
            "rpc": 0.51,
        }
    ],
}

# ---- POST first ----
post_res = requests.post(LE_API_URL, json=payload, headers=headers)
print("POST:", post_res.status_code, post_res.text)

payload = {
    "report_date": "2026-02-13",
    "data": [
        {
            "campaign_code": "mta-b_0213-lbe-e2",
            "clicks": 20,
            "leads": 9,
            "lead_percent": 45.00,
            "sales": 3,
            "sale_percent": 33.33,
            "revenue": 10.24,
            "epc": 1.14,
            "rpc": 0.51,
        }
    ],
}


params = {"action": "get_combined", "date": "2026-02-13"}

get_res = requests.get(LE_API_URL, params=params, timeout=30)

print("GET COMBINED STATUS:", get_res.status_code)
print("GET COMBINED DATA:", get_res.json())


# ---- PUT second ----
# put_res = requests.put(LE_API_URL, json=payload, headers=headers)
# print("PUT:", put_res.status_code, put_res.text)
