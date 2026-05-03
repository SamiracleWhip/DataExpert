import os
import json
import time
import urllib3
import requests
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

ACCESS_KEY = os.getenv("URA_ACCESS_KEY")
BASE_URL = "https://eservice.ura.gov.sg/uraDataService"
HEADERS_BASE = {"User-Agent": "curl/8.4.0"}
REQUEST_OPTS = {"verify": False}

OUTPUT_FILE = "raw_rental_contracts_all.json"

EXCLUDED_PROPERTY_TYPES = {"Semi-Detached House", "Detached House"}

QUARTERS = [
    "22q1", "22q2", "22q3", "22q4",
    "23q1", "23q2", "23q3", "23q4",
    "24q1", "24q2", "24q3", "24q4",
    "25q1", "25q2", "25q3", "25q4",
    "26q1",
]


def get_token():
    resp = requests.get(
        f"{BASE_URL}/insertNewToken/v1",
        headers={**HEADERS_BASE, "AccessKey": ACCESS_KEY},
        **REQUEST_OPTS
    )
    resp.raise_for_status()
    data = resp.json()
    if data["Status"] != "Success":
        raise RuntimeError(f"Token error: {data['Message']}")
    return data["Result"]


def fetch_quarter(token, ref_period):
    resp = requests.get(
        f"{BASE_URL}/invokeUraDS/v1",
        params={"service": "PMI_Resi_Rental", "refPeriod": ref_period},
        headers={**HEADERS_BASE, "AccessKey": ACCESS_KEY, "Token": token},
        **REQUEST_OPTS
    )
    resp.raise_for_status()
    data = resp.json()
    if data["Status"] != "Success":
        raise RuntimeError(f"API error for {ref_period}: {data['Message']}")
    return data["Result"]


if __name__ == "__main__":
    print("Getting token...")
    token = get_token()
    print("Token obtained.\n")

    all_data = {}
    total_projects = 0

    for quarter in QUARTERS:
        print(f"Fetching {quarter}...", end=" ", flush=True)
        try:
            records = fetch_quarter(token, quarter)
            for record in records:
                record["rental"] = [
                    r for r in record.get("rental", [])
                    if r.get("propertyType") not in EXCLUDED_PROPERTY_TYPES
                ]
            records = [r for r in records if r["rental"]]
            all_data[quarter] = records
            total_projects += len(records)
            print(f"{len(records)} projects")
        except Exception as e:
            print(f"FAILED: {e}")
            all_data[quarter] = []
        time.sleep(0.5)  # be polite to the API

    print(f"\nTotal projects across all quarters: {total_projects}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")
