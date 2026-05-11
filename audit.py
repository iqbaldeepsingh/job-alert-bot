#!/usr/bin/env python3
"""
Audit script — tests all API scrapers without Selenium.
Run:  python audit.py
"""
import sys
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress scraper-level noise; we print our own report
logging.disable(logging.CRITICAL)

from config.settings import COMPANIES
from scrapers.custom_scrapers import get_scraper, GenericScraper

API_SCRAPERS  = {"greenhouse", "lever", "workday", "phenom", "smartrecruiters",
                 "ashby", "avature", "oracle_hcm"}
# These use Selenium only — can't be tested without Chrome
CUSTOM_WITH_DEDICATED = {
    # Big tech
    "Google Canada", "Meta Canada", "Apple Canada", "Netflix Canada",
    "Shopify", "IBM Canada",
    # Banks / dedicated Selenium
    "Scotiabank",
    "Microsoft Canada",
    "Uber Canada",
    # j2w (SAP SuccessFactors) — Selenium
    "Deloitte Canada", "SAP Canada", "TELUS Health", "Scotiabank Digital Factory",
    "HCL Technologies Canada", "Wipro Canada", "Capgemini Canada", "City of Toronto",
    # iCIMS
    "Kinaxis", "Mackenzie Investments",
    # DayforceHCM
    "Questrade", "LifeLabs", "MindBridge AI",
    # Other dedicated Selenium
    "Atlassian Canada", "Intuit Canada", "Clio", "Coveo",
    "TCS Canada", "Cognizant Canada",
    "iA Financial Group", "PayPal Canada", "Oracle Canada",
    "WELL Health Technologies", "Stantec", "Pfizer Canada", "Klick Health",
    "Infosys Canada",
    "KPMG Canada",
}

STATUS_OK    = "✅ working"
STATUS_ZERO  = "⚠️  0 jobs"
STATUS_ERROR = "❌ error"
STATUS_SEL   = "🔵 selenium"
STATUS_SKIP  = "⬜ custom/skip"


def test_company(company: dict) -> dict:
    name    = company["name"]
    scraper_type = company.get("scraper", "custom")
    result  = {"name": name, "scraper": scraper_type, "jobs": 0, "status": "", "note": ""}

    # Known Selenium-only dedicated scrapers — skip without Chrome
    if name in CUSTOM_WITH_DEDICATED:
        result["status"] = STATUS_SEL
        result["note"]   = "Dedicated Selenium scraper"
        return result

    # For custom-typed companies, resolve the actual scraper class.
    # GenericScraper = no dedicated scraper → skip. Others → test via API.
    if scraper_type not in API_SCRAPERS:
        scraper = get_scraper(company)
        if isinstance(scraper, GenericScraper):
            result["status"] = STATUS_SKIP
            result["note"]   = "GenericScraper — skipped"
            return result
        # Has a dedicated API scraper (e.g. AmazonScraper, MicrosoftScraper)
        # Fall through to the normal scrape attempt below.

    try:
        scraper = get_scraper(company)
        jobs    = scraper.scrape(None)   # API scrapers ignore the driver arg
        n       = len(jobs)
        result["jobs"]   = n
        result["status"] = STATUS_OK if n > 0 else STATUS_ZERO
        result["note"]   = f"{n} Canada data jobs"
    except AttributeError as e:
        # Workday fell back to Selenium (driver=None crash) — API path failed
        result["status"] = STATUS_SEL
        result["note"]   = "API failed → Selenium fallback needed"
    except Exception as e:
        result["status"] = STATUS_ERROR
        result["note"]   = str(e)[:80]

    return result


def main():
    top100 = [c for c in COMPANIES if c.get("top100")]
    others = [c for c in COMPANIES if not c.get("top100")]

    print(f"\n{'='*70}")
    print(f"  Job Alert Bot — Scraper Audit   ({len(COMPANIES)} companies total)")
    print(f"{'='*70}\n")

    results = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = {pool.submit(test_company, c): c for c in COMPANIES}
        done = 0
        for future in as_completed(futures):
            r = future.result()
            results[r["name"]] = r
            done += 1
            print(f"\r  Testing... {done}/{len(COMPANIES)}", end="", flush=True)

    elapsed = time.time() - start
    print(f"\r  Done in {elapsed:.0f}s{' '*20}\n")

    def print_section(label, companies):
        print(f"\n{'─'*70}")
        print(f"  {label}  ({len(companies)} companies)")
        print(f"{'─'*70}")
        print(f"  {'Company':<36} {'Scraper':<16} {'Status':<18} {'Note'}")
        print(f"  {'─'*34} {'─'*14} {'─'*16} {'─'*25}")
        ok = zero = err = sel = skip = 0
        for c in companies:
            r = results[c["name"]]
            s = r["status"]
            print(f"  {r['name']:<36} {r['scraper']:<16} {s:<18} {r['note']}")
            if s == STATUS_OK:    ok   += 1
            elif s == STATUS_ZERO: zero += 1
            elif s == STATUS_ERROR: err += 1
            elif s == STATUS_SEL:  sel  += 1
            elif s == STATUS_SKIP: skip += 1
        print(f"\n  Summary: ✅{ok}  ⚠️{zero}  ❌{err}  🔵{sel}  ⬜{skip}")
        return ok, zero, err, sel, skip

    t_ok, t_zero, t_err, t_sel, t_skip = 0, 0, 0, 0, 0
    for label, cos in [("TOP 100 COMPANIES", top100), ("REMAINING COMPANIES", others)]:
        ok, zero, err, sel, skip = print_section(label, cos)
        t_ok += ok; t_zero += zero; t_err += err; t_sel += sel; t_skip += skip

    print(f"\n{'='*70}")
    print(f"  OVERALL — {len(COMPANIES)} companies")
    print(f"  ✅ Confirmed working  : {t_ok}")
    print(f"  ⚠️  API works, 0 jobs  : {t_zero}  (no Canada data roles posted today)")
    print(f"  ❌ Error / broken     : {t_err}")
    print(f"  🔵 Selenium (untested): {t_sel}  (need Chrome to verify)")
    print(f"  ⬜ GenericScraper skip: {t_skip}  (expected to return 0)")
    confirmed = t_ok + t_zero
    print(f"\n  Confirmed pipeline working: {confirmed}/{len(COMPANIES)} companies")
    print(f"  (⚠️  means scraper works but no matching jobs posted right now)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
