#!/usr/bin/env python3
"""Background scheduler for GeM Document Scraper."""

import os
import sys
import json
import time
import platform
from datetime import datetime, timedelta
import schedule
import requests as req
from bs4 import BeautifulSoup

IS_WINDOWS = platform.system() == "Windows"
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".gem_scrapscrap")
CONFIG_FILE = os.path.join(CONFIG_DIR, "schedule.json")
DESKTOP = os.path.join(HOME, "Desktop", "gem-updates") if not IS_WINDOWS else os.path.join(HOME, "Desktop", "gem-updates")

def get_session():
    s = req.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    return s

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def search_and_download(category_name, category_value, from_date, to_date):
    """Scrape and download documents for a category."""
    session = get_session()

    # Create date folder
    today = datetime.now().strftime("%Y-%m-%d")
    download_dir = os.path.join(DESKTOP, today)
    os.makedirs(download_dir, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in category_name)[:50]
    cat_dir = os.path.join(download_dir, safe_name)
    os.makedirs(cat_dir, exist_ok=True)

    log_file = os.path.join(download_dir, "log.txt")
    def log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_file, "a") as f:
            f.write(line + "\n")

    log(f"Starting scrape: {category_name}")

    try:
        session.get("https://gem.gov.in/view_contracts", timeout=60)

        # Search
        search_data = {
            "fromDate": from_date, "toDate": to_date,
            "department": "", "bno": "",
            "buyer_category": category_value, "page": 0,
        }
        resp = session.post("https://gem.gov.in/view_contracts/contract_details", data=search_data, timeout=60)
        soup = BeautifulSoup(resp.text, "html.parser")
        first_docs = soup.find_all("div", class_="border")

        if not first_docs:
            log(f"No documents found for {category_name} ({from_date} to {to_date})")
            return 0

        # Load all pages
        all_docs = list(first_docs)
        for page in range(1, 50):
            search_data["page"] = page
            resp = session.post("https://gem.gov.in/view_contracts/contract_details", data=search_data, timeout=60)
            soup = BeautifulSoup(resp.text, "html.parser")
            docs = soup.find_all("div", class_="border")
            if not docs:
                break
            all_docs.extend(docs)
            if len(docs) < 20:
                break
            time.sleep(0.3)

        log(f"Found {len(all_docs)} documents")

        # Download
        import re, json as _json
        downloaded = 0
        for i, doc in enumerate(all_docs):
            try:
                link = doc.find("a")
                if not link:
                    continue
                onclick = link.get("onclick", "")
                match = re.search(r"openCap\('([^']+)'\)", onclick)
                if not match:
                    continue

                contract_id = match.group(1)
                dl_resp = session.post("https://gem.gov.in/view_contracts/sbtCaptcha", data={"oid": contract_id}, timeout=60)
                dl_data = _json.loads(dl_resp.text)
                if dl_data.get("status") != "1":
                    continue

                code_html = dl_data.get("code", "")
                url_match = re.search(r'href=["\']([^"\']+)["\']', code_html)
                if not url_match:
                    continue

                pdf_resp = session.get(url_match.group(1), timeout=60)
                if len(pdf_resp.content) > 1000:
                    filename = f"contract_{i+1}.pdf"
                    filepath = os.path.join(cat_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(pdf_resp.content)
                    downloaded += 1
                    log(f"Downloaded {filename} ({len(pdf_resp.content)} bytes)")

                time.sleep(1)
            except Exception as e:
                log(f"Error on document {i+1}: {str(e)[:50]}")

        log(f"Done: {downloaded}/{len(all_docs)} documents saved to {cat_dir}")
        return downloaded

    except Exception as e:
        log(f"Error: {e}")
        return 0

def run_scheduled_job(job):
    """Run a single scheduled scraping job."""
    print(f"\n{'='*50}")
    print(f"Running: {job['name']}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    for cat in job["categories"]:
        search_and_download(
            cat["name"], cat["value"],
            job["from_date"], job["to_date"]
        )

def start_scheduler():
    """Start the background scheduler."""
    config = load_config()
    if not config or not config.get("jobs"):
        print("No scheduled jobs found. Run 'gem-scrapscrap' to set up a schedule first.")
        return

    print(f"Starting scheduler with {len(config['jobs'])} job(s)...")
    print(f"Downloads will go to: {DESKTOP}")
    print("Press Ctrl+C to stop.\n")

    for job in config["jobs"]:
        time_str = job["time"]  # e.g. "09:00"
        days = job.get("days", "daily")
        until = job.get("until", "")

        # Check if schedule is still active
        if until:
            try:
                until_date = datetime.strptime(until, "%d-%m-%Y")
                if datetime.now() > until_date:
                    print(f"Skipping '{job['name']}' — expired (until {until})")
                    continue
            except ValueError:
                pass

        if days == "daily":
            schedule.every().day.at(time_str).do(run_scheduled_job, job)
            print(f"  Scheduled: {job['name']} daily at {time_str}")
        elif isinstance(days, list):
            for day in days:
                if day == "monday":
                    schedule.every().monday.at(time_str).do(run_scheduled_job, job)
                elif day == "tuesday":
                    schedule.every().tuesday.at(time_str).do(run_scheduled_job, job)
                elif day == "wednesday":
                    schedule.every().wednesday.at(time_str).do(run_scheduled_job, job)
                elif day == "thursday":
                    schedule.every().thursday.at(time_str).do(run_scheduled_job, job)
                elif day == "friday":
                    schedule.every().friday.at(time_str).do(run_scheduled_job, job)
                elif day == "saturday":
                    schedule.every().saturday.at(time_str).do(run_scheduled_job, job)
                elif day == "sunday":
                    schedule.every().sunday.at(time_str).do(run_scheduled_job, job)
            print(f"  Scheduled: {job['name']} on {', '.join(days)} at {time_str}")
        elif isinstance(days, list) and all(isinstance(d, int) for d in days):
            # Specific dates of month
            for day_num in days:
                schedule.every().day.at(time_str).do(lambda j=job, d=day_num: run_scheduled_job(j) if datetime.now().day == d else None)
            print(f"  Scheduled: {job['name']} on days {days} at {time_str}")

    print(f"\nScheduler running. Next job: {schedule.next_run()}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nScheduler stopped.")

if __name__ == "__main__":
    start_scheduler()
