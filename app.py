import os
import uuid
import threading
import zipfile
import io
import json
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from scraper import run_scrape

app = Flask(__name__)

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

jobs = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def start_scrape():
    data = request.json
    category = data.get("category", "").strip()
    from_date = data.get("from_date", "").strip()
    to_date = data.get("to_date", "").strip()

    if not category or not from_date or not to_date:
        return jsonify({"error": "All fields are required"}), 400

    job_id = str(uuid.uuid4())[:8]
    download_dir = os.path.join(DOWNLOADS_DIR, job_id)

    jobs[job_id] = {
        "status": "starting",
        "message": "Job queued...",
        "category": category,
        "from_date": from_date,
        "to_date": to_date,
        "documents_found": 0,
        "documents_downloaded": 0,
        "logs": [],
        "download_dir": download_dir,
        "downloaded_files": [],
    }

    thread = threading.Thread(
        target=run_scrape,
        args=(job_id, category, from_date, to_date, jobs),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    downloaded = []
    if os.path.exists(job["download_dir"]):
        for f in os.listdir(job["download_dir"]):
            if f.endswith((".pdf", ".zip")) and not os.path.isdir(os.path.join(job["download_dir"], f)):
                downloaded.append(f)

    return jsonify({
        "status": job["status"],
        "message": job["message"],
        "category": job["category"],
        "from_date": job["from_date"],
        "to_date": job["to_date"],
        "documents_found": job["documents_found"],
        "documents_downloaded": job["documents_downloaded"],
        "logs": job["logs"],
        "downloaded_files": downloaded,
    })


@app.route("/download/<job_id>/<filename>")
def download_file(job_id, filename):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    file_path = os.path.join(job["download_dir"], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)


@app.route("/download_all/<job_id>")
def download_all(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    download_dir = job["download_dir"]
    if not os.path.exists(download_dir):
        return jsonify({"error": "No files to download"}), 404

    pdf_files = [
        f for f in os.listdir(download_dir)
        if f.endswith(".pdf") and not os.path.isdir(os.path.join(download_dir, f))
    ]

    if not pdf_files:
        return jsonify({"error": "No PDF files found"}), 404

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for pdf in pdf_files:
            pdf_path = os.path.join(download_dir, pdf)
            zipf.write(pdf_path, pdf)
    zip_buffer.seek(0)

    zip_name = f"gem_documents_{job_id}.zip"
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_name,
    )


CATEGORIES_CACHE = None

@app.route("/categories")
def get_categories():
    global CATEGORIES_CACHE
    if CATEGORIES_CACHE:
        return jsonify(CATEGORIES_CACHE)

    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories_cache.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            CATEGORIES_CACHE = json.load(f)
        return jsonify(CATEGORIES_CACHE)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://gem.gov.in/view_contracts")
        import time
        time.sleep(5)

        select = Select(driver.find_element(By.ID, "buyer_category"))
        categories = []
        for opt in select.options:
            text = opt.text.strip()
            if text and text not in ("--Select Category--", "--Select--"):
                categories.append(text)
        driver.quit()

        CATEGORIES_CACHE = categories
        with open(cache_file, "w") as f:
            json.dump(categories, f)

        return jsonify(categories)
    except Exception as e:
        return jsonify([])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
