#!/usr/bin/env python3
"""
Test a single company's scraper.
Usage:
  python3 test_company.py "RBC"
  python3 test_company.py "PwC Canada"
  python3 test_company.py --all-api        # test all non-Selenium scrapers
"""
import sys
import logging
import argparse
from config.settings import COMPANIES
from scrapers.custom_scrapers import get_scraper, GenericScraper

logging.basicConfig(level=logging.WARNING)


def test_one(company: dict, driver=None, verbose=True) -> list:
    name = company["name"]
    scraper = get_scraper(company)

    if isinstance(scraper, GenericScraper):
        if verbose:
            print(f"⬜  {name} — GenericScraper (not implemented)")
        return []

    try:
        jobs = scraper.scrape(driver)
    except AttributeError:
        if verbose:
            print(f"🔵  {name} — Selenium scraper (needs Chrome, skipped in this test)")
        return []
    except Exception as e:
        if verbose:
            print(f"❌  {name} — ERROR: {e}")
        return []

    if verbose:
        status = f"✅  {len(jobs)} jobs found" if jobs else "⚠️   0 jobs (scraper works, none posted today)"
        print(f"\n{status}  —  {name}  [{company['scraper']}]")
        print(f"  URL: {company['careers_url'][:80]}")
        if jobs:
            print(f"  {'Title':<55} {'Location':<35} URL")
            print(f"  {'─'*55} {'─'*35} {'─'*40}")
            for j in jobs:
                title = j['title'][:54]
                loc   = j['location'][:34]
                url   = j.get('url', '')[:70]
                print(f"  {title:<55} {loc:<35} {url}")
    return jobs


def test_all_api():
    SELENIUM_TYPES = {"custom"}  # will skip custom that need Chrome
    total = ok = zero = err = skipped = 0

    for co in COMPANIES:
        total += 1
        scraper = get_scraper(co)
        if isinstance(scraper, GenericScraper):
            skipped += 1
            continue
        try:
            jobs = scraper.scrape(None)
            if jobs:
                ok += 1
                print(f"✅  {co['name']:<40} {len(jobs)} jobs")
            else:
                zero += 1
                print(f"⚠️   {co['name']:<40} 0 jobs")
        except AttributeError:
            print(f"🔵  {co['name']:<40} Selenium (skipped)")
            skipped += 1
        except Exception as e:
            err += 1
            print(f"❌  {co['name']:<40} ERROR: {str(e)[:60]}")

    print(f"\n{'='*60}")
    print(f"Total: {total}  ✅{ok}  ⚠️{zero}  ❌{err}  skipped:{skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("company", nargs="?", help="Company name (exact or partial match)")
    parser.add_argument("--all-api", action="store_true", help="Test all non-Selenium scrapers")
    args = parser.parse_args()

    if args.all_api:
        test_all_api()
        sys.exit(0)

    if not args.company:
        print("Usage: python3 test_company.py \"Company Name\"")
        print("       python3 test_company.py --all-api")
        sys.exit(1)

    # Find matching companies (partial match)
    query = args.company.lower()
    matches = [c for c in COMPANIES if query in c["name"].lower()]

    if not matches:
        print(f"No company found matching: {args.company}")
        print("Available companies:")
        for c in COMPANIES:
            print(f"  {c['name']}")
        sys.exit(1)

    for co in matches:
        test_one(co, driver=None, verbose=True)
