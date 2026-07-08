import time
import os
import re
import json
import requests as req
from bs4 import BeautifulSoup


def log_msg(job_id, job, msg):
    print(f"[{job_id}] {msg}")
    job["logs"].append(msg)


def run_scrape(job_id, category, from_date, to_date, jobs):
    job = jobs[job_id]
    download_dir = os.path.abspath(job["download_dir"])
    os.makedirs(download_dir, exist_ok=True)

    try:
        log_msg(job_id, job, "Starting scraper...")
        job["status"] = "running"
        job["message"] = "Connecting to GeM..."

        session = req.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        # Step 1: Load page
        log_msg(job_id, job, "Loading GeM website...")
        job["message"] = "Loading GeM..."
        resp = session.get("https://gem.gov.in/view_contracts", timeout=60)
        if resp.status_code != 200:
            raise Exception(f"Failed to load GeM: HTTP {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")

        # Step 2: Get category value
        log_msg(job_id, job, f"Finding category: {category}")
        job["message"] = f"Finding: {category}"
        cat_select = soup.find("select", {"id": "buyer_category"})
        cat_value = None
        if cat_select:
            for opt in cat_select.find_all("option"):
                if opt.text.strip() == category:
                    cat_value = opt["value"]
                    break

        if not cat_value:
            raise Exception(f"Category '{category}' not found on GeM")

        log_msg(job_id, job, f"Category found: {cat_value}")

        # Step 3: Search (AJAX endpoint doesn't need CAPTCHA)
        log_msg(job_id, job, "Searching contracts...")
        job["message"] = "Searching..."
        all_docs = []

        search_data = {
            "fromDate": from_date,
            "toDate": to_date,
            "department": "",
            "bno": "",
            "buyer_category": cat_value,
            "page": 0,
        }

        search_resp = session.post(
            "https://gem.gov.in/view_contracts/contract_details",
            data=search_data,
            timeout=60,
        )

        result_soup = BeautifulSoup(search_resp.text, "html.parser")
        first_page_docs = result_soup.find_all("div", class_="border")

        if first_page_docs:
            all_docs = list(first_page_docs)
            log_msg(job_id, job, f"Found {len(first_page_docs)} documents on page 0.")
        else:
            log_msg(job_id, job, "No documents found for this category/date range.")
            job["status"] = "done"
            job["message"] = "No documents found. Try a wider date range."
            return

        # Step 4: Load remaining pages
        max_pages = 50
        page = 1
        while page < max_pages:
            next_data = {
                "fromDate": from_date,
                "toDate": to_date,
                "department": "",
                "bno": "",
                "buyer_category": cat_value,
                "page": page,
            }
            next_resp = session.post(
                "https://gem.gov.in/view_contracts/contract_details",
                data=next_data,
                timeout=60,
            )
            next_soup = BeautifulSoup(next_resp.text, "html.parser")
            next_docs = next_soup.find_all("div", class_="border")

            if not next_docs:
                break

            all_docs.extend(next_docs)
            log_msg(job_id, job, f"Page {page}: +{len(next_docs)} docs (total: {len(all_docs)})")
            page += 1
            time.sleep(0.5)

        doc_count = len(all_docs)
        job["documents_found"] = doc_count
        log_msg(job_id, job, f"Total documents found: {doc_count}")
        job["message"] = f"Found {doc_count} documents. Downloading..."

        if doc_count == 0:
            job["status"] = "done"
            job["message"] = "No documents found."
            return

        # Step 5: Download each document
        for i, doc in enumerate(all_docs):
            try:
                log_msg(job_id, job, f"Downloading document {i+1}/{doc_count}...")
                job["message"] = f"Downloading {i+1}/{doc_count}..."
                job["documents_downloaded"] = i

                link = doc.find("a")
                if not link:
                    continue

                onclick = link.get("onclick", "")
                match = re.search(r"openCap\('([^']+)'\)", onclick)
                if not match:
                    continue

                contract_id = match.group(1)

                dl_resp = session.post(
                    "https://gem.gov.in/view_contracts/sbtCaptcha",
                    data={"oid": contract_id},
                    timeout=60,
                )
                dl_data = json.loads(dl_resp.text)

                if dl_data.get("status") != "1":
                    log_msg(job_id, job, f"Document {i+1}: download auth failed")
                    continue

                code_html = dl_data.get("code", "")
                url_match = re.search(r'href=["\']([^"\']+)["\']', code_html)
                if not url_match:
                    continue

                download_url = url_match.group(1)
                pdf_resp = session.get(download_url, timeout=60)
                content_type = pdf_resp.headers.get("Content-Type", "")

                if len(pdf_resp.content) > 1000:
                    filename = f"document_{i+1}.pdf"
                    filepath = os.path.join(download_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(pdf_resp.content)
                    job["downloaded_files"].append(filename)
                    log_msg(job_id, job, f"Document {i+1} downloaded ({len(pdf_resp.content)} bytes).")
                else:
                    log_msg(job_id, job, f"Document {i+1}: too small ({len(pdf_resp.content)} bytes)")

                time.sleep(1)

            except Exception as e:
                err_msg = str(e).split("\n")[0]
                log_msg(job_id, job, f"Error on document {i+1}: {err_msg}")

        job["documents_downloaded"] = doc_count
        job["status"] = "done"
        log_msg(job_id, job, f"Done! {doc_count} documents processed.")
        job["message"] = f"Complete! {doc_count} documents."

    except Exception as e:
        log_msg(job_id, job, f"Fatal error: {e}")
        job["status"] = "error"
        job["message"] = f"Error: {e}"
