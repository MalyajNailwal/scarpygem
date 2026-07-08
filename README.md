# gem-scrapscrap

A Python CLI tool to scrape and download contract documents from [GeM (Government e-Marketplace)](https://gem.gov.in). Search by category, set a date range, and download all matching contract PDFs — no browser or Selenium required.

## What does it do?

GeM is India's government procurement platform. It publishes thousands of contract documents, but has no bulk download or export feature. This tool fills that gap.

**You give it:** a category (e.g. "Ball Point Pens") + a date range.
**It gives you:** all matching contract PDFs, downloaded locally.

## What pain points does it solve?

| Problem | How this tool fixes it |
|---------|----------------------|
| GeM has no bulk download option | Scrapes all pages and downloads every matching contract PDF automatically |
| Browser-based scraping is slow and fragile | Pure HTTP requests — no headless browser or automation needed |
| No way to track new contracts over time | Built-in scheduler runs scrapes on a cron (daily, weekly, specific days) |
| GeM's UI is slow and unresponsive | HTTP requests are fast — scrapes 50 pages in seconds |
| Need to manually organize downloaded files | Auto-organizes into date-based folders, creates ZIP bundles |
| Hard to find the right category (13,000+ options) | CLI has autocomplete search across all GeM categories |
| No programmatic access to contract data | Pure Python HTTP — easy to integrate into pipelines or scripts |

## Use cases

- **Government procurement teams** — Track new contracts in your category daily
- **Vendors/suppliers** — Monitor GeM for relevant tenders and contract awards
- **Researchers/analysts** — Bulk-download contract data for market analysis
- **Compliance teams** — Archive contract documents for audit trails
- **Anyone** who needs to download many GeM documents without clicking one-by-one

## Quick Start

### Install

```bash
pip3 install gem-scrapscrap
```

### Run

```bash
gem-scrapscrap
```

That's it. The CLI will:

1. Connect to GeM and load all 13,000+ categories
2. Let you search and pick a category with autocomplete
3. Ask for a date range
4. Search all matching contract pages
5. Download every contract PDF with a progress bar
6. Optionally create a ZIP of all downloads

### First run

On first launch, the tool adds itself to your PATH automatically. On Windows it modifies the user PATH via registry; on Mac/Linux it appends to your shell config (`.zshrc` / `.bash_profile`).

## CLI Features

### Interactive menu

```
  ╔═══════════════════════════════════════════╗
  ║     GeM Document Scraper CLI v1.7.1      ║
  ║   Government e-Marketplace Downloader     ║
  ╚═══════════════════════════════════════════╝

  MAIN MENU
  1.  Scrape & Download
  2.  Search categories
  3.  Setup Schedule
  4.  Stop Schedule
  5.  Uninstall
  6.  Quit
```

### Autocomplete category search

Type to filter through GeM's 13,000+ categories. Uses `questionary` for a smooth autocomplete experience (falls back to numbered list if not installed).

### Download options

- **Download ALL** — Grab every matching contract
- **Download as ZIP** — All contracts in a single ZIP file
- **Pick specific** — Select individual documents by number (supports ranges like `1,3,5-8`)
- **Skip** — Preview results without downloading

### Auto-update

On launch, checks PyPI for a newer version and prompts to update. Restarts automatically after updating.

### Uninstall

Menu option `5` cleanly removes the package, cleans shell config, and removes PATH entries.

## Scheduling

Set up automated scrapes that run in the background:

```
  Setup Auto-Scraping Schedule
  Search & select categories for auto-scraping

  Scrape & Download → Add category: LED Bulbs
  Date range: 01-07-2025 to 07-07-2025
  Scraping time: 09:00 IST
  How often: Specific weekdays → Monday, Wednesday, Friday
  Run until: forever
```

Scheduler features:
- Run daily, on specific weekdays, or on specific days of month
- Set an end date or run forever
- Downloads save to `~/Desktop/gem-updates/YYYY-MM-DD/` with per-category subfolders
- Config stored at `~/.gem_scrapscrap/schedule.json`
- Run standalone: `gem-scrapscrap-schedule`

## Web UI

A Flask-based web interface is also available for browser-based usage:

```bash
pip3 install flask gunicorn requests beautifulsoup4
python3 app.py
```

Open **http://localhost:5000**.

### API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Web UI |
| POST | `/scrape` | Start a new scraping job |
| GET | `/status/<job_id>` | Job status + logs + file list |
| GET | `/download/<job_id>/<file>` | Download a single PDF |
| GET | `/download_all/<job_id>` | Download all PDFs as ZIP |
| GET | `/categories` | List all GeM categories |

## How It Works

The tool uses GeM's server-side AJAX endpoints directly — no headless browser or page rendering required:

1. **Load categories** — GET `gem.gov.in/view_contracts`, parse the category dropdown
2. **Search contracts** — POST to the contract details endpoint with category value + date range + page number
3. **Paginate** — Loop through pages (up to 50) until no more results
4. **Download** — For each document, fetch the download URL from the response and grab the PDF

All communication happens over standard HTTP — fast, lightweight, and runs anywhere Python does.

## Tested Categories

These categories are known to have contracts on GeM:

| Category | Notes |
|----------|-------|
| `Ball Point Pens (V2) as per IS 3705` | Office supplies, high volume |
| `Note Sorting Machines (V2)` | Banking equipment |
| `LED Bulb with Battery as per IS 16102` | Govt LED scheme |
| `Split Air Conditioner, Wall Mount Type (V3) ISI Marked to IS 1391 (Part 2)` | HVAC |
| `Nitrogen Tyre Inflators` | Automotive |

Use a wide date range (e.g., `01-01-2025` to `07-07-2025`) for more results.

## Date Format

The CLI accepts `DD-MM-YYYY` (e.g. `01-07-2025`).
The web UI accepts multiple formats and auto-converts:
- `DD-MM-YYYY` (e.g. 01-07-2025)
- `DD/MM/YYYY` (e.g. 01/07/2025)
- `YYYY-MM-DD` (e.g. 2025-07-01)

## Project Structure

```
gem-scrapscrap/
├── gem_cli.py          # CLI entry point (interactive terminal)
├── scraper.py          # HTTP scraping engine (used by web UI)
├── scheduler.py        # Background scheduler for auto-scraping
├── app.py              # Flask web server
├── main.py             # Legacy Selenium-based CLI (deprecated)
├── actions.py          # Legacy Selenium helpers (deprecated)
├── templates/
│   └── index.html      # Web UI (HTML + CSS + JS, no frameworks)
├── pyproject.toml      # Package config (PyPI: gem-scrapscrap)
├── requirements.txt    # Web UI dependencies
├── Dockerfile          # Container for web UI deployment
├── railway.json        # Railway deployment config
└── render.yaml         # Render deployment config
```

## Dependencies

| Package | Purpose | Used by |
|---------|---------|---------|
| `requests` | HTTP requests to GeM | CLI + Web UI |
| `beautifulsoup4` | HTML parsing | CLI + Web UI |
| `rich` | Terminal UI (tables, progress, panels) | CLI |
| `questionary` | Interactive prompts + autocomplete | CLI |
| `schedule` | Cron-like job scheduling | Scheduler |
| `flask` | Web server | Web UI |
| `gunicorn` | Production WSGI server | Web UI (deploy) |

## Deploy

### Railway

1. Go to [railway.app](https://railway.app) → Sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `Wickcore/gem-scrapscrap`
4. Railway auto-detects the Dockerfile
5. Click **Deploy**

Your app will be live at `https://your-app.up.railway.app`

### Render

Uses `render.yaml` — auto-detects Docker deployment.

## Notes

- Each scraping job runs in its own thread with its own download directory
- The scheduler saves to `~/Desktop/gem-updates/` by default
- GeM may change their page structure, which could break selectors
- The legacy `main.py` uses Selenium + Tesseract OCR — kept for reference, not actively maintained

## License

MIT
