import logging
import time
import sys
from scrapers.base_scraper import BaseScraper, build_driver
BaseScraper.is_data_role = lambda self, t: True

from config.settings import COMPANIES
from scrapers.custom_scrapers import get_scraper

results = {"pass": [], "zero": [], "error": []}

headless = "--headless" not in sys.argv

for i, co in enumerate(COMPANIES):
    name = co["name"]
    driver = build_driver(headless=True)
    try:
        driver.set_page_load_timeout(30)
        jobs = get_scraper(co).scrape(driver)
        count = len(jobs)
        if count > 0:
            results["pass"].append((name, count))
            print(f"✅ [{i+1}/{len(COMPANIES)}] {name}: {count} jobs")
        else:
            results["zero"].append(name)
            print(f"⚠️  [{i+1}/{len(COMPANIES)}] {name}: 0 jobs")
    except Exception as e:
        results["error"].append((name, str(e)[:80]))
        print(f"❌ [{i+1}/{len(COMPANIES)}] {name}: ERROR {str(e)[:60]}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    sys.stdout.flush()

print("\n" + "="*60)
print(f"PASS (jobs found): {len(results['pass'])}")
print(f"ZERO (no jobs):    {len(results['zero'])}")
print(f"ERROR (crashed):   {len(results['error'])}")
print("\nERRORS:")
for name, e in results["error"]:
    print(f"  {name}: {e}")
print("\nZERO JOBS:")
for name in results["zero"]:
    print(f"  {name}")
