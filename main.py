"""
Main Orchestrator
ਸਾਰੇ scrapers ਚਲਾਉਂਦਾ ਹੈ, deduplicate ਕਰਦਾ ਹੈ, email ਭੇਜਦਾ ਹੈ

Run:           python main.py
Morning:       python main.py --run morning
Evening:       python main.py --run evening
Test email:    python main.py --test-email
Clear cache:   python main.py --clear-cache
No headless:   python main.py --no-headless
Broad test:    python main.py --broad   (all roles: SE, QA, DevOps; skip dedup)
"""

import os
import sys
import time
import random
import logging
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.settings import COMPANIES
from scrapers.custom_scrapers import get_scraper, GenericScraper, AmazonScraper, NetflixScraper, ShopifyScraper
from scrapers.base_scraper import BaseScraper, build_driver
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.ashby_scraper import AshbyScraper
from scrapers.phenom_scraper import PhenomScraper
from scrapers.smartrecruiters_scraper import SmartRecruitersScraper
from scrapers.avature_scraper import AvatureScraper
from scrapers.oracle_hcm_scraper import OracleHCMScraper
from utils.email_builder import send_email, send_broad_summary_email
from utils.deduplicator import filter_new_jobs, clear_cache

# Scrapers that use HTTP only — no Chrome needed at all
_NO_SELENIUM = (
    GreenhouseScraper, LeverScraper, AshbyScraper, PhenomScraper,
    SmartRecruitersScraper, AvatureScraper, OracleHCMScraper,
    AmazonScraper, NetflixScraper, ShopifyScraper,
)

# Per-company wall-clock timeout — prevents one stuck scraper blocking the run
_COMPANY_TIMEOUT_S = 60

# ── Logging setup ───────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/job_alert.log", mode="a"),
    ]
)
logger = logging.getLogger(__name__)


# ── Scrape one company ──────────────────────────────────────────
# Limit concurrent Chrome launches to 3 — prevents "Text file busy" on chromedriver binary.
# Semaphore only gates the launch; multiple Chromes run simultaneously once started.
_chrome_semaphore = __import__("threading").Semaphore(3)

def scrape_company(company: dict, headless: bool = True) -> list:
    scraper = get_scraper(company)
    if isinstance(scraper, _NO_SELENIUM):
        try:
            return scraper.run(None)
        except Exception as e:
            logger.error(f"[{company['name']}] Unexpected error: {e}")
            return []

    with _chrome_semaphore:
        time.sleep(random.uniform(0.3, 1.0))
        driver = build_driver(headless=headless)
    try:
        return scraper.run(driver)
    except Exception as e:
        logger.error(f"[{company['name']}] Unexpected error: {e}")
        return []
    finally:
        driver.quit()


# ── Scrape all companies ────────────────────────────────────────
def scrape_all(headless: bool = True, track_counts: bool = False):
    import threading as _threading

    all_jobs       = []
    company_counts = []
    _lock          = _threading.Lock()
    done_count     = [0]

    API_TYPES = {"greenhouse", "lever", "workday", "phenom", "ashby",
                 "smartrecruiters", "oracle_hcm", "avature"}
    api_cos = [c for c in COMPANIES if c.get("scraper") in API_TYPES]
    sel_cos = [c for c in COMPANIES
               if c.get("scraper") not in API_TYPES
               and not isinstance(get_scraper(c), GenericScraper)]
    skipped = len(COMPANIES) - len(api_cos) - len(sel_cos)
    total   = len(api_cos) + len(sel_cos)

    logger.info(f"{'='*55}")
    logger.info(f"Total companies : {len(COMPANIES)}")
    logger.info(f"API scrapers    : {len(api_cos)} (no Chrome needed)")
    logger.info(f"Selenium scrapers: {len(sel_cos)} (need Chrome)")
    logger.info(f"Skipped (Generic): {skipped} (no dedicated scraper)")
    logger.info(f"{'='*55}")

    def _collect(c, jobs):
        with _lock:
            all_jobs.extend(jobs)
            if track_counts:
                company_counts.append((c["name"], len(jobs)))
            done_count[0] += 1
            logger.info(
                f"Progress: {done_count[0]}/{total} | "
                f"{c['name']}: {len(jobs)} jobs | Total: {len(all_jobs)}"
            )

    def _run_pool(cos, max_workers):
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(scrape_company, c, headless): c for c in cos}
            for future in as_completed(futures):
                c = futures[future]
                try:
                    jobs = future.result(timeout=_COMPANY_TIMEOUT_S)
                except Exception as e:
                    logger.error(f"[{c['name']}] timed out or crashed: {e}")
                    jobs = []
                _collect(c, jobs)

    # Phase 1 (API, 40 threads) and Phase 2 (Selenium, 6 threads) run concurrently
    t1 = _threading.Thread(target=_run_pool, args=(api_cos, 40), daemon=True)
    t2 = _threading.Thread(target=_run_pool, args=(sel_cos, 6),  daemon=True)
    logger.info("Starting API + Selenium phases concurrently...")
    t1.start(); t2.start()
    t1.join();  t2.join()

    logger.info(f"Scraping complete — {len(all_jobs)} total jobs")
    if track_counts:
        return all_jobs, company_counts
    return all_jobs


# ── Main run ────────────────────────────────────────────────────
def run(run_label: str = "Daily", headless: bool = True, broad: bool = False, include_us: bool = False):
    start = time.time()
    logger.info(f"{'='*55}")
    logger.info(f"Job Alert Bot — {run_label}{'  [BROAD TEST]' if broad else ''}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*55}")

    if broad:
        BaseScraper.is_data_role = lambda self, title: True
        logger.info("BROAD MODE: is_data_role patched to True for all titles")

    if include_us:
        BaseScraper.is_canada_job = lambda self, location: True
        logger.info("INCLUDE-US MODE: is_canada_job patched to accept all locations")

    # Step 1 — Scrape
    if broad:
        all_jobs, company_counts = scrape_all(headless=headless, track_counts=True)
    else:
        all_jobs = scrape_all(headless=headless)

    # Step 2 — Broad mode: send summary email and exit
    if broad:
        logger.info(f"BROAD MODE: sending summary email ({len(company_counts)} companies)")
        success = send_broad_summary_email(company_counts, run_label=run_label)
        elapsed = time.time() - start
        logger.info(f"Done in {elapsed:.0f}s | success={success}")
        return

    # Step 2 — Deduplicate
    new_jobs = filter_new_jobs(all_jobs)

    if not new_jobs:
        logger.info("No new jobs found — sending status email")
        send_email([], run_label=run_label)
        return

    # Step 3 — Sort (Senior first)
    level_order = {
        "Staff / Lead": 0,
        "Principal":    1,
        "Senior":       2,
        "Mid-Level":    3,
        "Entry Level":  4,
    }
    new_jobs.sort(key=lambda j: level_order.get(j.get("level", "Mid-Level"), 3))

    # Step 4 — Send email (chunk if large batch)
    CHUNK_SIZE = 50
    logger.info(f"Sending email with {len(new_jobs)} new jobs...")
    if len(new_jobs) <= CHUNK_SIZE:
        success = send_email(new_jobs, run_label=run_label)
    else:
        chunks = [new_jobs[i:i + CHUNK_SIZE] for i in range(0, len(new_jobs), CHUNK_SIZE)]
        logger.info(f"Large batch — splitting into {len(chunks)} emails of up to {CHUNK_SIZE} jobs")
        success = all(
            send_email(chunk, run_label=f"{run_label} ({idx+1}/{len(chunks)})")
            for idx, chunk in enumerate(chunks)
        )

    elapsed = time.time() - start
    logger.info(f"{'='*55}")
    logger.info(f"Done in {elapsed:.0f}s")
    logger.info(f"Scraped: {len(all_jobs)} | New: {len(new_jobs)} | Email: {success}")
    logger.info(f"{'='*55}")


# ── CLI ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Alert Bot")
    parser.add_argument("--run",
        choices=["morning", "evening", "daily"],
        default="daily",
        help="Run label for email subject")
    parser.add_argument("--no-headless",
        action="store_true",
        help="Show Chrome window (for debugging)")
    parser.add_argument("--clear-cache",
        action="store_true",
        help="Clear seen jobs cache")
    parser.add_argument("--test-email",
        action="store_true",
        help="Send test email with dummy jobs")
    parser.add_argument("--broad",
        action="store_true",
        help="Broad test: accept all job titles, skip deduplication")
    parser.add_argument("--include-us",
        action="store_true",
        help="Include US jobs alongside Canada (useful for testing which scrapers work)")
    args = parser.parse_args()

    if args.clear_cache:
        clear_cache()
        print("✅ Cache cleared")
        sys.exit(0)

    if args.test_email:
        dummy = [
            {
                "title": "Senior Data Engineer",
                "company": "RBC",
                "category": "Banks",
                "location": "Toronto, ON",
                "level": "Senior",
                "type": "Hybrid",
                "posted": "Today",
                "url": "https://jobs.rbc.com",
                "salary": "$125K–$165K",
                "skills": ["Azure", "Databricks", "PySpark", "Delta Lake", "dbt"],
            },
            {
                "title": "Analytics Engineer",
                "company": "Shopify",
                "category": "Big Tech",
                "location": "Remote Canada",
                "level": "Senior",
                "type": "Remote",
                "posted": "2 days ago",
                "url": "https://shopify.com/careers",
                "salary": "$138K–$178K",
                "skills": ["GCP", "Trino", "dbt", "Python", "Spark"],
            },
            {
                "title": "Data Engineer",
                "company": "Deloitte Canada",
                "category": "Consulting",
                "location": "Toronto, ON",
                "level": "Entry Level",
                "type": "Hybrid",
                "posted": "1 week ago",
                "url": "https://careers.deloitte.ca",
                "salary": "$75K–$98K",
                "skills": ["Azure", "Python", "SQL", "dbt", "ADF"],
            },
        ]
        ok = send_email(dummy, run_label="TEST")
        print(f"Test email {'✅ sent!' if ok else '❌ failed — check .env file'}")
        sys.exit(0)

    labels = {
        "morning": "Morning (9 AM)",
        "evening": "Evening (6 PM)",
        "daily":   "Daily",
    }
    run(run_label=labels[args.run], headless=not args.no_headless, broad=args.broad, include_us=args.include_us)