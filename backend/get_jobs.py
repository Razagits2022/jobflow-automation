"""Utility script to instantly get live job URLs for any company.

Usage:
    python get_jobs.py <company_name> [optional_role_filter]

Examples:
    python get_jobs.py figma
    python get_jobs.py careem engineer
    python get_jobs.py monzo
    python get_jobs.py warp
"""

import sys
import json
import urllib.request

def fetch_jobs(company: str, filter_keyword: str = ""):
    company = company.lower().strip()
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

    print(f"Fetching live jobs for '{company}' from Greenhouse...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            all_jobs = data.get("jobs", [])
    except Exception as e:
        print(f"Greenhouse board not found or error: {e}")
        all_jobs = []

    if not all_jobs:
        # Try Lever API
        lever_url = f"https://api.lever.co/v0/postings/{company}"
        try:
            req = urllib.request.Request(lever_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                lever_data = json.loads(response.read().decode())
                all_jobs = [
                    {"title": j.get("text"), "absolute_url": j.get("hostedUrl"), "location": j.get("categories", {}).get("location")}
                    for j in lever_data
                ]
        except Exception:
            pass

    if not all_jobs:
        print(f"No jobs found for '{company}'. Try another company (e.g. figma, careem, monzo, warp, duolingo, lyft).")
        return

    # Filter if keyword provided
    if filter_keyword:
        filtered = [j for j in all_jobs if filter_keyword.lower() in j.get("title", "").lower()]
    else:
        filtered = all_jobs

    print(f"\nFound {len(filtered)} matching jobs (showing top 10):\n" + "-" * 60)
    for i, j in enumerate(filtered[:10], 1):
        title = j.get("title")
        job_url = j.get("absolute_url")
        location = j.get("location", {}).get("name") if isinstance(j.get("location"), dict) else j.get("location", "")
        loc_str = f" ({location})" if location else ""
        print(f"{i}. {title}{loc_str}")
        print(f"   {job_url}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    co = sys.argv[1]
    kw = sys.argv[2] if len(sys.argv) > 2 else ""
    fetch_jobs(co, kw)
