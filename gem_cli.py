#!/usr/bin/env python3
"""GeM Document Scraper CLI — Interactive terminal tool."""

import os
import sys
import platform
import subprocess
import time
import re
import json
import zipfile
import shutil
import requests as req
from bs4 import BeautifulSoup
from rich.console import Console

def get_version():
    try:
        from importlib.metadata import version
        return version("gem-scrapscrap")
    except Exception:
        return "dev"

__version__ = get_version()
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box
from rich.rule import Rule

try:
    import questionary
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

console = Console()
IS_WINDOWS = platform.system() == "Windows"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(sys.executable))

# ─── Auto PATH Setup ────────────────────────────────────────────────────────

def setup_path():
    """Add Python scripts dir to PATH if not already there."""
    path_marker = os.path.join(os.path.expanduser("~"), ".gem_scrapscrap_path_done")

    if os.path.exists(path_marker):
        return

    if IS_WINDOWS:
        # Windows: add to user PATH via registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
            winreg.CloseKey(key)

            if SCRIPTS_DIR.lower() not in current_path.lower():
                new_path = current_path + ";" + SCRIPTS_DIR
                subprocess.run(
                    ['setx', 'PATH', new_path],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                console.print(f"  [green]✓[/green] Added to Windows PATH: {SCRIPTS_DIR}")
                console.print("  [dim]Restart your terminal for changes to take effect[/dim]")
        except Exception:
            pass

    else:
        # Mac/Linux: add to shell config
        home = os.path.expanduser("~")
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            rc_file = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            rc_file = os.path.join(home, ".bash_profile")
        else:
            rc_file = os.path.join(home, ".profile")

        path_line = f'export PATH="{SCRIPTS_DIR}:$PATH"'

        if os.path.exists(rc_file):
            with open(rc_file, "r") as f:
                content = f.read()
            if SCRIPTS_DIR not in content:
                with open(rc_file, "a") as f:
                    f.write(f"\n# gem-scrapscrap\n{path_line}\n")
                console.print(f"  [green]✓[/green] Added to {rc_file}")
        else:
            with open(rc_file, "w") as f:
                f.write(f"# gem-scrapscrap\n{path_line}\n")
            console.print(f"  [green]✓[/green] Created {rc_file}")

    # Mark as done
    with open(path_marker, "w") as f:
        f.write("done")

def check_and_update():
    """Check PyPI for newer version and auto-update if found."""
    try:
        resp = req.get("https://pypi.org/pypi/gem-scrapscrap/json", timeout=5)
        if resp.status_code != 200:
            return True
        latest = resp.json()["info"]["version"]
        current = __version__

        if latest == current:
            return True

        print(f"\n  Update available: {current} → {latest}")
        try:
            ans = input("  Update now? (Y/n): ").strip().replace("\r", "").lower()
        except (EOFError, KeyboardInterrupt):
            ans = "y"

        if ans in ("", "y", "yes"):
            print("  Updating...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "gem-scrapscrap", "--quiet"],
                capture_output=False
            )
            if result.returncode == 0:
                print("  Updated! Restarting...\n")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("  Update failed. Run: pip3 install --upgrade gem-scrapscrap")
        return True

    except Exception:
        return True

        console.print(f"\n  [bold yellow]Update available: {current} → {latest}[/bold yellow]")
        try:
            ans = input("  Update now? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "y"

        if ans in ("", "y", "yes"):
            console.print("  [bold green]Updating...[/bold green]")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "gem-scrapscrap"],
                capture_output=False
            )
            console.print("  [bold green]Done! Restarting...[/bold]\n")
            time.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return True

    except Exception as e:
        return True

        console.print(f"\n  [bold yellow]Update available: {current} → {latest}[/bold yellow]")
        try:
            ans = console.input("  [bold]Update now? (Y/n):[/bold] ").strip().lower()
        except EOFError:
            ans = "y"

        if ans in ("", "y", "yes"):
            console.print("  [bold green]Updating...[/bold green]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "gem-scrapscrap"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print("  [bold green]Updated successfully![/bold green]")
                console.print("  [bold]Restarting...[/bold]\n")
                # Restart the process
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                console.print(f"  [bold red]Update failed. Run manually: pip3 install --upgrade gem-scrapscrap[/bold red]")
                return True
        return True

    except Exception:
        return True

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_terminal_width():
    return shutil.get_terminal_size((80, 24)).columns

def get_terminal_height():
    return shutil.get_terminal_size((80, 24)).lines

def banner():
    w = get_terminal_width()
    lines = [
        "  ╔═══════════════════════════════════════════╗  ",
        f"  ║     GeM Document Scraper CLI v{__version__:5s}      ║  ",
        "  ║   Government e-Marketplace Downloader     ║  ",
        "  ╚═══════════════════════════════════════════╝  ",
    ]
    for line in lines:
        console.print(Align.center(line, width=w), style="bold cyan")

def divider():
    console.print(Rule(style="dim blue"))

def success(msg):
    console.print(f"  [bold green]✓[/bold green] {msg}")

def error(msg):
    console.print(f"  [bold red]✗[/bold red] {msg}")

def info(msg):
    console.print(f"  [bold blue]i[/bold blue] {msg}")

def section(title):
    console.print()
    console.print(f"  [bold yellow]{title}[/bold yellow]")
    divider()

def input_field(prompt, default="", validator=None):
    while True:
        try:
            val = console.input(f"  [bold cyan]{prompt}:[/bold cyan] ").strip()
        except EOFError:
            return default
        if not val and default:
            return default
        if validator and not validator(val):
            continue
        return val

# ─── Uninstall ──────────────────────────────────────────────────────────────

def uninstall():
    section("Uninstall gem-scrapscrap")

    if not questionary.confirm("Are you sure you want to uninstall?").ask():
        info("Cancelled.")
        return

    try:
        if IS_WINDOWS:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "gem-scrapscrap", "-y"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        else:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "gem-scrapscrap", "-y"],
                capture_output=True, text=True
            )

        if result.returncode == 0:
            success("gem-scrapscrap uninstalled successfully!")

            # Remove from shell config
            if not IS_WINDOWS:
                home = os.path.expanduser("~")
                shell = os.environ.get("SHELL", "")
                rc_file = os.path.join(home, ".zshrc" if "zsh" in shell else ".bash_profile")

                if os.path.exists(rc_file):
                    with open(rc_file, "r") as f:
                        lines = f.readlines()
                    with open(rc_file, "w") as f:
                        for line in lines:
                            if "gem-scrapscrap" not in line and SCRIPTS_DIR not in line:
                                f.write(line)
                    success(f"Cleaned {rc_file}")

            # Remove marker
            marker = os.path.join(os.path.expanduser("~"), ".gem_scrapscrap_path_done")
            if os.path.exists(marker):
                os.remove(marker)

            success("All clean! No traces left.")
            console.print("\n[dim]Exiting...[/dim]")
            sys.exit(0)
        else:
            error(f"Uninstall failed: {result.stderr}")

    except Exception as e:
        error(f"Uninstall failed: {e}")

# ─── GeM API ────────────────────────────────────────────────────────────────

def get_session():
    s = req.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    return s

def load_categories(session):
    resp = session.get("https://gem.gov.in/view_contracts", timeout=60)
    soup = BeautifulSoup(resp.text, "html.parser")
    cat_select = soup.find("select", {"id": "buyer_category"})
    categories = []
    if cat_select:
        for opt in cat_select.find_all("option"):
            text = opt.text.strip()
            value = opt["value"]
            if text and text not in ("--Select Category--", "--Select--"):
                categories.append({"text": text, "value": value})
    return categories

def search_contracts(session, cat_value, from_date, to_date, page=0):
    search_data = {
        "fromDate": from_date,
        "toDate": to_date,
        "department": "",
        "bno": "",
        "buyer_category": cat_value,
        "page": page,
    }
    resp = session.post(
        "https://gem.gov.in/view_contracts/contract_details",
        data=search_data,
        timeout=60,
    )
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.find_all("div", class_="border")

def load_all_pages(session, cat_value, from_date, to_date, max_pages=50):
    all_docs = []
    for page in range(max_pages):
        docs = search_contracts(session, cat_value, from_date, to_date, page)
        if not docs:
            break
        all_docs.extend(docs)
        if len(docs) < 20:
            break
        time.sleep(0.3)
    return all_docs

def download_document(session, doc, index, download_dir):
    link = doc.find("a")
    if not link:
        return None
    onclick = link.get("onclick", "")
    match = re.search(r"openCap\('([^']+)'\)", onclick)
    if not match:
        return None
    contract_id = match.group(1)

    dl_resp = session.post(
        "https://gem.gov.in/view_contracts/sbtCaptcha",
        data={"oid": contract_id},
        timeout=60,
    )
    dl_data = json.loads(dl_resp.text)
    if dl_data.get("status") != "1":
        return None

    code_html = dl_data.get("code", "")
    url_match = re.search(r'href=["\']([^"\']+)["\']', code_html)
    if not url_match:
        return None

    pdf_resp = session.get(url_match.group(1), timeout=60)
    if len(pdf_resp.content) > 1000:
        filename = f"document_{index}.pdf"
        filepath = os.path.join(download_dir, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_resp.content)
        return {"filename": filename, "size": len(pdf_resp.content), "contract": contract_id}
    return None

def create_zip(download_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(download_dir)):
            if f.endswith(".pdf"):
                zf.write(os.path.join(download_dir, f), f)
    return os.path.getsize(zip_path)

# ─── Category Selection ─────────────────────────────────────────────────────

current_categories = []

def select_category(categories):
    global current_categories
    current_categories = categories

    section("Select Category")
    info(f"{len(categories)} categories available — type to search")

    if HAS_QUESTIONARY:
        try:
            choices = [c["text"] for c in categories]

            answer = questionary.autocomplete(
                "Search & select category",
                choices=choices,
                validate=lambda x: True if x else "Please select a category",
                style=questionary.Style([
                    ('question', 'bold cyan'),
                    ('answer', 'bold green'),
                    ('completion', 'dim'),
                ]),
            ).ask()

            if answer:
                for cat in categories:
                    if cat["text"] == answer or answer.lower() in cat["text"].lower():
                        success(f"Selected: {cat['text']}")
                        return cat
            return None

        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled[/dim]")
            return None
    else:
        search = input_field("Search (type to filter)", default="")
        matches = [c for c in categories if search.lower() in c["text"].lower()] if search else categories

        if not matches:
            error("No categories match.")
            return None

        console.print()
        shown = matches[:20]
        for i, cat in enumerate(shown, 1):
            console.print(f"  [green]{i:3d}.[/green] {cat['text']}")
        if len(matches) > 20:
            console.print(f"  [dim]... {len(matches) - 20} more[/dim]")

        choice = input_field(f"Pick (1-{len(shown)})", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            selected = shown[int(choice) - 1]
            success(f"Selected: {selected['text']}")
            return selected
        return None

def select_dates():
    section("Date Range")
    info("Format: DD-MM-YYYY (e.g. 01-01-2025)")

    def valid_date(d):
        if not re.match(r"^\d{2}-\d{2}-\d{4}$", d):
            error("Invalid format. Use DD-MM-YYYY")
            return False
        return True

    from_date = input_field("From date", validator=valid_date)
    to_date = input_field("To date", validator=valid_date)
    return from_date, to_date

def show_documents(docs):
    section(f"Found {len(docs)} Documents")
    w = get_terminal_width()

    table = Table(box=box.ROUNDED, show_lines=False, expand=True)
    table.add_column("#", style="green", width=4, no_wrap=True)
    table.add_column("Contract", style="cyan", ratio=3)
    table.add_column("Status", style="yellow", width=10, no_wrap=True)

    shown = min(15, len(docs))
    for i, doc in enumerate(docs[:shown], 1):
        link = doc.find("a")
        text = link.text.strip()[:w - 25] if link else "Unknown"
        table.add_row(str(i), text, "Ready")

    if len(docs) > shown:
        table.add_row("...", f"[dim]{len(docs) - shown} more[/dim]", "")

    console.print(table)

def select_download_option():
    section("Download Options")
    console.print("  [green]1.[/green]  Download ALL documents")
    console.print("  [green]2.[/green]  Download as ZIP")
    console.print("  [green]3.[/green]  Pick specific documents")
    console.print("  [green]4.[/green]  Skip")

    choice = input_field("Choose", default="2", validator=lambda x: x in ("1","2","3","4"))
    return {"1": "all", "2": "zip", "3": "pick", "4": "skip"}[choice]

def pick_documents(docs):
    section("Pick Documents")
    info("Enter numbers separated by commas (e.g. 1,3,5-8)")
    raw = input_field("Documents")

    indices = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            if start.isdigit() and end.isdigit():
                indices.extend(range(int(start), int(end) + 1))
        elif part.isdigit():
            indices.append(int(part))

    return [docs[i - 1] for i in indices if 1 <= i <= len(docs)]

def download_with_progress(session, docs, download_dir):
    section(f"Downloading {len(docs)} Documents")

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=get_terminal_width() - 30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading...", total=len(docs))

        for i, doc in enumerate(docs):
            progress.update(task, description=f"Document {i+1}/{len(docs)}")
            result = download_document(session, doc, i + 1, download_dir)
            if result:
                results.append(result)
            progress.advance(task)

    return results

def show_summary(results, download_dir):
    section("Download Complete")

    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("File", style="cyan", ratio=2)
    table.add_column("Contract", style="dim", ratio=3)
    table.add_column("Size", style="green", justify="right", width=10)

    total_size = 0
    for r in results:
        size_kb = r["size"] / 1024
        total_size += r["size"]
        table.add_row(r["filename"], r.get("contract", ""), f"{size_kb:.1f} KB")

    console.print(table)
    console.print()
    success(f"{len(results)} files saved to: [bold]{download_dir}[/bold]")
    success(f"Total size: {total_size / 1024:.1f} KB")

# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    # Auto setup PATH on first run
    setup_path()

    # Check for updates BEFORE clearing screen
    check_and_update()

    console.clear()
    banner()
    divider()

    # Load categories
    session = get_session()
    with console.status("[bold green]Connecting to GeM...[/bold green]"):
        categories = load_categories(session)

    console.print()
    success(f"Loaded {len(categories)} categories from GeM")

    while True:
        console.print()
        divider()
        console.print("  [bold]MAIN MENU[/bold]")
        divider()

        if HAS_QUESTIONARY:
            menu_choices = ["Scrape & Download", "Search categories", "Setup Schedule", "Stop Schedule", "Uninstall", "Quit"]
            try:
                action = questionary.select(
                    "Choose",
                    choices=menu_choices,
                    style=questionary.Style([
                        ('question', 'bold cyan'),
                        ('answer', 'bold green'),
                        ('pointer', 'bold cyan'),
                        ('highlighted', 'bold cyan'),
                    ]),
                ).ask()
            except KeyboardInterrupt:
                action = "Quit"
        else:
            console.print("  [green]1.[/green]  Scrape & Download")
            console.print("  [green]2.[/green]  Search categories")
            console.print("  [green]3.[/green]  Setup Schedule")
            console.print("  [green]4.[/green]  Stop Schedule")
            console.print("  [green]5.[/green]  Uninstall")
            console.print("  [green]6.[/green]  Quit")
            divider()
            action = input_field("Choose", default="1")
            action = {"1": "Scrape & Download", "2": "Search categories", "3": "Setup Schedule", "4": "Stop Schedule", "5": "Uninstall", "6": "Quit"}.get(action, "Quit")

        if not action or action == "Quit":
            console.print()
            info("Goodbye!")
            console.print()
            break

        if action == "Uninstall":
            uninstall()
            continue

        if "Stop Schedule" in action:
            from scheduler import load_config, save_config, CONFIG_FILE
            config = load_config()
            if config and config.get("jobs"):
                console.print(f"\n  [bold]{len(config['jobs'])} scheduled job(s):[/bold]")
                for i, job in enumerate(config["jobs"], 1):
                    console.print(f"    {i}. {job['name'][:50]} — {job['time']}")
                console.print()
                try:
                    choice = input("  Remove all schedules? (Y/n): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    choice = "y"
                if choice in ("", "y", "yes"):
                    save_config({"jobs": []})
                    success("All schedules removed!")
                else:
                    info("Cancelled.")
            else:
                info("No schedules configured.")
            continue

        if "Schedule" in action:
            setup_schedule(categories)
            continue

        if "Search" in action:
            section("Category Search")
            if HAS_QUESTIONARY:
                choices = [c["text"] for c in categories]
                try:
                    answer = questionary.autocomplete(
                        "Search categories",
                        choices=choices,
                        style=questionary.Style([
                            ('question', 'bold cyan'),
                            ('answer', 'bold green'),
                            ('completion', 'dim'),
                        ]),
                    ).ask()
                    if answer:
                        matches = [c for c in categories if answer.lower() in c["text"].lower()]
                        console.print()
                        for c in matches[:15]:
                            console.print(f"    [cyan]{c['text']}[/cyan]")
                        if len(matches) > 15:
                            console.print(f"    [dim]... {len(matches) - 15} more[/dim]")
                        console.print(f"\n  [green]{len(matches)} categories found[/green]")
                except KeyboardInterrupt:
                    pass
            else:
                search = input_field("Search")
                matches = [c for c in categories if search.lower() in c["text"].lower()]
                if matches:
                    for c in matches[:15]:
                        console.print(f"    {c['text']}")
                else:
                    error("No matches found")
            continue

        # Full workflow
        while True:
            selected = select_category(categories)
            if not selected:
                break

            from_date, to_date = select_dates()
            if not from_date:
                break

            with console.status("[bold yellow]Searching GeM...[/bold yellow]"):
                docs = load_all_pages(session, selected["value"], from_date, to_date)

            if not docs:
                console.print()
                error("No documents found for this date range.")
                console.print()
                if HAS_QUESTIONARY:
                    retry_action = questionary.select(
                        "What would you like to do?",
                        choices=["Try different dates", "Pick different category", "Main menu", "Quit"],
                        style=questionary.Style([
                            ('question', 'bold cyan'),
                            ('pointer', 'bold cyan'),
                            ('highlighted', 'bold cyan'),
                        ]),
                    ).ask()
                else:
                    console.print("  [green]1.[/green]  Try different dates")
                    console.print("  [green]2.[/green]  Pick different category")
                    console.print("  [green]3.[/green]  Main menu")
                    console.print("  [green]4.[/green]  Quit")
                    choice = input_field("Choose", default="1")
                    retry_action = {"1": "Try different dates", "2": "Pick different category", "3": "Main menu", "4": "Quit"}.get(choice, "Quit")

                if retry_action == "Quit":
                    info("Goodbye!")
                    sys.exit(0)
                elif retry_action == "Main menu":
                    break
                elif retry_action == "Pick different category":
                    continue
                else:
                    continue  # Try different dates
            break

        if not docs:
            continue

        show_documents(docs)

        option = select_download_option()
        if option == "skip":
            continue

        if option == "pick":
            to_download = pick_documents(docs)
            if not to_download:
                error("No documents selected.")
                continue
        else:
            to_download = docs

        download_dir = os.path.join(os.getcwd(), "gem_downloads")
        os.makedirs(download_dir, exist_ok=True)

        results = download_with_progress(session, to_download, download_dir)

        if not results:
            error("No documents downloaded.")
            continue

        if option in ("all", "zip") and len(results) > 1:
            if questionary.confirm("Create ZIP file?", default=True).ask():
                zip_path = os.path.join(download_dir, "all_documents.zip")
                with console.status("[bold yellow]Creating ZIP...[/bold yellow]"):
                    zip_size = create_zip(download_dir, zip_path)
                success(f"ZIP created: {zip_path} ({zip_size / 1024:.0f} KB)")

        show_summary(results, download_dir)


# ─── Schedule Setup ──────────────────────────────────────────────────────────

def setup_schedule(categories):
    section("Setup Auto-Scraping Schedule")

    from scheduler import save_config, load_config, DESKTOP

    config = load_config() or {"jobs": []}

    # Step 1: Autocomplete search for categories
    console.print()
    info("Search & select categories for auto-scraping")
    console.print()

    selected_cats = []

    if HAS_QUESTIONARY:
        cat_choices = [c["text"] for c in categories]

        # Let user add multiple categories via autocomplete
        while True:
            try:
                answer = questionary.autocomplete(
                    f"Add category ({len(selected_cats)} selected) or press Enter to finish",
                    choices=[c for c in cat_choices if c not in selected_cats],
                    style=questionary.Style([
                        ('question', 'bold cyan'),
                        ('answer', 'bold green'),
                        ('completion', 'dim'),
                    ]),
                ).ask()
            except KeyboardInterrupt:
                break

            if not answer:
                break

            selected_cats.append(answer)
            success(f"Added: {answer}")
            console.print()

            # Ask if user wants to add more
            try:
                more = input("  Add more? (Y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if more in ("n", "no"):
                break
    else:
        search = input_field("Search categories")
        matches = [c for c in categories if search.lower() in c["text"].lower()]
        for i, c in enumerate(matches[:15], 1):
            console.print(f"  [green]{i}.[/green] {c['text']}")
        picks = input_field("Pick numbers (comma-separated)")
        for p in picks.split(","):
            if p.strip().isdigit() and 1 <= int(p.strip()) <= len(matches):
                selected_cats.append(matches[int(p.strip()) - 1]["text"])
    if not selected_cats:
        error("No categories selected.")
        return

    selected_values = []
    for name in selected_cats:
        for c in categories:
            if c["text"] == name:
                selected_values.append({"name": c["text"], "value": c["value"]})
                break

    console.print()
    success(f"Selected {len(selected_values)} categories:")
    for c in selected_values:
        console.print(f"    • {c['name']}")

    # Date range
    console.print()
    info("Date range for each scrape (same range for all categories)")
    from_date, to_date = select_dates()
    if not from_date:
        return

    # Time
    console.print()
    if HAS_QUESTIONARY:
        time_str = questionary.text(
            "Scraping time (HH:MM, 24h format, IST)",
            default="09:00",
            validate=lambda x: True if re.match(r"^\d{2}:\d{2}$", x) else "Use HH:MM format (e.g. 09:00)",
        ).ask()
    else:
        time_str = input_field("Time (HH:MM)", default="09:00")

    # Frequency
    console.print()
    if HAS_QUESTIONARY:
        freq = questionary.select(
            "How often?",
            choices=["Every day", "Specific days of month", "Specific weekdays"],
            style=questionary.Style([
                ('question', 'bold cyan'),
                ('pointer', 'bold cyan'),
                ('highlighted', 'bold cyan'),
            ]),
        ).ask()
    else:
        console.print("  [green]1.[/green]  Every day")
        console.print("  [green]2.[/green]  Specific days of month")
        console.print("  [green]3.[/green]  Specific weekdays")
        freq = {"1": "Every day", "2": "Specific days of month", "3": "Specific weekdays"}.get(input_field("Choose", default="1"), "Every day")

    days = "daily"
    if freq == "Specific days of month":
        raw = input_field("Days (comma-separated, e.g. 1,10,20)", default="1,10,20")
        days = [int(d.strip()) for d in raw.split(",") if d.strip().isdigit()]
    elif freq == "Specific weekdays":
        if HAS_QUESTIONARY:
            days = questionary.checkbox(
                "Select days",
                choices=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                style=questionary.Style([
                    ('question', 'bold cyan'),
                    ('pointer', 'bold cyan'),
                    ('highlighted', 'bold cyan'),
                    ('checkbox', 'bold green'),
                    ('checkboxed', 'bold green'),
                ]),
            ).ask()
            days = [d.lower() for d in days] if days else ["monday"]
        else:
            raw = input_field("Days (comma-separated)", default="monday,wednesday,friday")
            days = [d.strip().lower() for d in raw.split(",")]

    # Duration
    console.print()
    if HAS_QUESTIONARY:
        until = questionary.text(
            "Run until (DD-MM-YYYY) or 'forever'",
            default="forever",
        ).ask()
    else:
        until = input_field("Run until (DD-MM-YYYY or 'forever')", default="forever")

    # Create job
    job = {
        "name": " + ".join([c["name"][:30] for c in selected_values]),
        "categories": selected_values,
        "from_date": from_date,
        "to_date": to_date,
        "time": time_str,
        "days": days,
        "until": until if until != "forever" else "",
    }

    config["jobs"].append(job)
    save_config(config)

    console.print()
    divider()
    success("Schedule saved!")
    console.print()
    console.print(f"  [bold]Categories:[/bold] {', '.join([c['name'][:40] for c in selected_values])}")
    console.print(f"  [bold]Date range:[/bold] {from_date} to {to_date}")
    console.print(f"  [bold]Time:[/bold] {time_str} IST")
    console.print(f"  [bold]Frequency:[/bold] {freq}")
    console.print(f"  [bold]Downloads:[/bold] {DESKTOP}/YYYY-MM-DD/")
    if until != "forever":
        console.print(f"  [bold]Until:[/bold] {until}")
    console.print()

    # Ask to start scheduler now
    try:
        start_now = input("  Start scheduler now? (Y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        start_now = "y"

    if start_now in ("", "y", "yes"):
        console.print()
        from scheduler import start_scheduler
        start_scheduler()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n")
        info("Interrupted. Bye!")
        sys.exit(0)
