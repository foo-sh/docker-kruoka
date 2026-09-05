import json
import re
import sys
import urllib.error
import urllib.request
import zoneinfo
from datetime import datetime, timedelta

TIMEZONE = zoneinfo.ZoneInfo("Europe/Helsinki")


def fetch_api(base_url, endpoint):
    """Helper to handle urllib requests and return (status_code, json_dict or None)."""
    url = f"{base_url}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body)
    except urllib.error.HTTPError as e:
        return e.code, None


def validate_time_format(time_str):
    """Verifies time string matches HH:MM format within 00:00 to 24:00 bounds."""
    assert re.match(r"^\d{1,2}:\d{2}$", time_str), (
        f"Invalid time format structure: {time_str}"
    )

    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])

    assert 0 <= minutes < 60, f"Minutes out of range: {minutes}"
    assert 0 <= hours <= 24, f"Hours out of range: {hours}"
    if hours == 24:
        assert minutes == 0, f"Time cannot exceed 24:00 (got {time_str})"


def verify_success_payload(data):
    """Validates presence and structural accuracy of grocery hours data."""
    assert data is not None, "Expected JSON response body, got None"
    assert "opens" in data, f"Missing required 'opens' key in payload: {data}"
    assert "closes" in data, f"Missing required 'closes' key in payload: {data}"

    validate_time_format(data["opens"])
    validate_time_format(data["closes"])


def test_api_routes(base_url):
    # 1. Setup dynamic test dates
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    future_8_days = (datetime.now(TIMEZONE) + timedelta(days=8)).strftime("%Y-%m-%d")

    print(f"Running API assertion tests against: {base_url}")

    # 2. Test Root endpoint (Today's hours)
    print("-> Checking Root /")
    status, data = fetch_api(base_url, "/")
    assert status == 200, f"Expected 200, got {status}"
    verify_success_payload(data)

    # 3. Test Valid ISO Date path (Today)
    print(f"-> Checking valid date /{today_str}")
    status, data = fetch_api(base_url, f"/{today_str}")
    assert status == 200, f"Expected 200, got {status}"
    verify_success_payload(data)

    # 4. Test Invalid date string format
    print("-> Checking bad format /not-a-date")
    status, _ = fetch_api(base_url, "/not-a-date")
    assert status == 404, f"Expected 404, got {status}"

    # 5. Test Far future date boundary (>= 8 days)
    print(f"-> Checking far future /{future_8_days}")
    status, _ = fetch_api(base_url, f"/{future_8_days}")
    assert status == 404, f"Expected 404, got {status}"

    # 6. Test Epoch / Historical date boundary
    print("-> Checking historical /1970-01-01")
    status, _ = fetch_api(base_url, "/1970-01-01")
    assert status == 404, f"Expected 404, got {status}"

    print("All assertions passed successfully!")


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    target_url = target_url.removesuffix("/")

    test_api_routes(target_url)
