"""
Custom Scrapers
Google, Amazon, Microsoft, Meta, Apple, Netflix,
Uber, LinkedIn, Spotify, Deloitte, CGI, TD Bank,
Scotiabank, Rogers, Telus, Bell, + Generic fallback
"""

import time
import logging
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from scrapers.base_scraper import BaseScraper
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.workday_scraper import WorkdayScraper
from scrapers.phenom_scraper import PhenomScraper
from scrapers.smartrecruiters_scraper import SmartRecruitersScraper
from scrapers.ashby_scraper import AshbyScraper
from scrapers.shopify_scraper import ShopifyScraper
from scrapers.avature_scraper import AvatureScraper
from scrapers.ibm_scraper import IBMScraper
from scrapers.oracle_hcm_scraper import OracleHCMScraper
from scrapers.netflix_scraper import NetflixScraper

logger = logging.getLogger(__name__)


# ── GOOGLE ──────────────────────────────────────────────────────
_GOOGLE_CARD_SELS = [
    "li.lLd3Je", "li[jsmodel]", ".sMn82b",
    "[data-job-id]", "li[class*='job']",
    ".jobs-list li", "ul.jobs li",
    "article[class*='job']",
]
_GOOGLE_TITLE_SELS  = ["h3", "h2", ".QJPWVe", ".job-title", "[class*='title']"]
_GOOGLE_LOC_SELS    = [".r0wTof", ".location", ".job-location", "[class*='location']"]


class GoogleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "li.lLd3Je, li[jsmodel], [data-job-id], li[class*='job']")
                )
            )
        except TimeoutException:
            pass
        self.slow_scroll(driver)
        time.sleep(2)

        cards = []
        for sel in _GOOGLE_CARD_SELS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 1:
                logger.info(f"[Google] {len(cards)} cards with: {sel}")
                break

        if not cards:
            logger.warning("[Google] No job cards — trying link extraction")
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/results/']")
            jobs = []
            for link in links[:30]:
                title = self.safe_text(link)
                url = self.safe_attr(link, "href")
                if title and len(title) > 5:
                    jobs.append(self.build_job(title=title, location="Canada", url=url))
            return jobs

        jobs = []
        for card in cards[:25]:
            try:
                title, url, location = "", "", ""
                for tsel in _GOOGLE_TITLE_SELS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        if title:
                            break
                    except NoSuchElementException:
                        continue
                try:
                    url = self.safe_attr(card.find_element(By.CSS_SELECTOR, "a"), "href")
                except NoSuchElementException:
                    pass
                for lsel in _GOOGLE_LOC_SELS:
                    try:
                        location = self.safe_text(card.find_element(By.CSS_SELECTOR, lsel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue
                if title:
                    jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue
        return jobs


# ── AMAZON ──────────────────────────────────────────────────────
_AMAZON_API = "https://www.amazon.jobs/en/search.json"
_AMAZON_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


class AmazonScraper(BaseScraper):
    def scrape(self, _driver) -> list:
        jobs = []
        offset = 0
        limit  = 100
        while True:
            try:
                r = requests.get(_AMAZON_API, headers=_AMAZON_HEADERS, timeout=15, params={
                    "base_query":  "data engineer",
                    "country":     "CAN",
                    "result_limit": limit,
                    "offset":       offset,
                })
                if r.status_code != 200:
                    break
                d        = r.json()
                postings = d.get("jobs", [])
                if not postings:
                    break
                for job in postings:
                    title = job.get("title", "")
                    if not self.is_data_role(title):
                        continue
                    raw_loc = job.get("location", "Canada")
                    parts   = [p.strip() for p in raw_loc.split(",")]
                    location = (f"{parts[2]}, {parts[1]}, Canada"
                                if len(parts) == 3 else raw_loc)
                    path = job.get("job_path", "")
                    url  = f"https://www.amazon.jobs{path}" if path else ""
                    jobs.append(self.build_job(
                        title=title, location=location, url=url,
                        posted=job.get("posted_date", "Recent"),
                    ))
                offset += limit
                if offset >= d.get("hits", 0):
                    break
            except Exception as e:
                logger.error(f"[Amazon] API error: {e}")
                break
        logger.info(f"[Amazon / AWS Canada] {len(jobs)} Canada data jobs")
        return jobs


# ── MICROSOFT ───────────────────────────────────────────────────
_MS_API = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
_MS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept":     "application/json",
}


class MicrosoftScraper(BaseScraper):
    def scrape(self, _driver) -> list:
        jobs  = []
        page  = 1
        total = None
        while True:
            try:
                r = requests.get(_MS_API, headers=_MS_HEADERS, timeout=15, params={
                    "q":    "data engineer",
                    "lc":   "Canada",
                    "pgSz": 20,
                    "pg":   page,
                    "l":    "en_us",
                })
                if r.status_code != 200:
                    logger.warning(f"[Microsoft] API {r.status_code} — page {page}")
                    break
                res = r.json().get("operationResult", {}).get("result", {})
                if total is None:
                    total = res.get("totalJobs", 0)
                    logger.info(f"[Microsoft] API: {total} total jobs")
                for job in res.get("jobs", []):
                    title = job.get("title", "")
                    if not self.is_data_role(title):
                        continue
                    location = job.get("primaryLocation", "Canada")
                    if not self.is_canada_job(location):
                        continue
                    job_id = job.get("jobId", "")
                    url = (f"https://jobs.careers.microsoft.com/global/en/job/{job_id}/"
                           if job_id else "")
                    jobs.append(self.build_job(
                        title=title, location=location, url=url,
                        posted=job.get("postingDate", "Recent"),
                    ))
                fetched = page * 20
                if fetched >= (total or 0) or not res.get("jobs"):
                    break
                page += 1
            except Exception as e:
                logger.error(f"[Microsoft] API error: {e}")
                break
        logger.info(f"[Microsoft Canada] {len(jobs)} Canada data jobs")
        return jobs


# ── META ────────────────────────────────────────────────────────
_META_CARD_SELS  = [
    "[data-testid='job-card']", "div[data-testid='job-listing-card']",
    "._8muv", "._8iwr", "div[class*='job']",
    ".jobs-list-item", "li[class*='job']",
    "a[href*='/jobs/']",
]
_META_TITLE_SELS = [
    "[data-testid='job-title']", "a span", "._8hq4 span",
    "h3", "h2", "[class*='title']",
]
_META_LOC_SELS   = [
    "[data-testid='job-listing-location']", "._8hq6",
    "[class*='location']", ".location",
]


class MetaScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(6)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='job-card'], ._8muv, a[href*='/jobs/']")
                )
            )
        except TimeoutException:
            pass
        self.slow_scroll(driver)
        time.sleep(2)

        cards = []
        for sel in _META_CARD_SELS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 1:
                logger.info(f"[Meta] {len(cards)} cards with: {sel}")
                break

        jobs = []
        for card in cards[:25]:
            try:
                title, url, location = "", "", ""
                for tsel in _META_TITLE_SELS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        if title:
                            break
                    except NoSuchElementException:
                        continue
                if not title:
                    title = self.safe_text(card)
                try:
                    url = self.safe_attr(card.find_element(By.CSS_SELECTOR, "a"), "href")
                except NoSuchElementException:
                    pass
                for lsel in _META_LOC_SELS:
                    try:
                        location = self.safe_text(card.find_element(By.CSS_SELECTOR, lsel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue
                if title and len(title) > 4:
                    jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue
        return jobs


# ── APPLE ───────────────────────────────────────────────────────
_APPLE_CARD_SELS  = [
    "tbody tr", ".table-row",
    "[class*='table-row']", "li[class*='job']",
    "[data-id]", "div[class*='job']",
]
_APPLE_TITLE_SELS = [
    "a.table--advanced-search__title", "a[href*='/details/']",
    "a", "h3", "h2",
]


class AppleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tbody tr, [class*='table-row'], a[href*='/details/']")
                )
            )
        except TimeoutException:
            pass
        self.slow_scroll(driver)

        cards = []
        for sel in _APPLE_CARD_SELS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 1:
                logger.info(f"[Apple] {len(cards)} cards with: {sel}")
                break

        if not cards:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/details/'], a[href*='jobs.apple.com']")
            jobs = []
            for link in links[:30]:
                title = self.safe_text(link)
                url = self.safe_attr(link, "href")
                if title and len(title) > 5:
                    jobs.append(self.build_job(title=title, location="Canada", url=url))
            return jobs

        jobs = []
        for card in cards[:25]:
            try:
                title, url, location = "", "", ""
                for tsel in _APPLE_TITLE_SELS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        url = self.safe_attr(el, "href")
                        if title:
                            break
                    except NoSuchElementException:
                        continue
                if url and not url.startswith("http"):
                    url = "https://jobs.apple.com" + url
                try:
                    location = self.safe_text(card.find_element(
                        By.CSS_SELECTOR, ".table-col-2, .location, [class*='location'], td:nth-child(2)"))
                except NoSuchElementException:
                    pass
                if title:
                    jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue
        return jobs




# ── TD BANK ─────────────────────────────────────────────────────
class TDBankScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            ".job-listing, .job-result, article[class*='job']")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "a, h2, h3")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    "[class*='location'], .job-location"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── SCOTIABANK ──────────────────────────────────────────────────
class ScotiabankScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            ".jobs-search__item, .job-result-card")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR,
                    "a.job-name, h2 a, h3 a")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    ".job-location, .location"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── SCOTIABANK (SAP SuccessFactors) ─────────────────────────────
_SCOT_SEARCH = "https://jobs.scotiabank.com/search-results?keywords=data+engineer&location=Canada"

_SAP_SF_TITLE_SELS = [
    "td.jobTitle a",
    "a.jobTitle",
    ".jobTitle a",
    "a[href*='/job/']",
    ".jdDefaultLocFont a",
]
_SAP_SF_LOCATION_SELS = [
    "td.jobLocation",
    ".jobLocation",
    "span.jobLocation",
    ".location",
]
_SAP_SF_ROW_SELS = [
    "tr.even, tr.odd",
    "table.resultTable tbody tr",
    "ul.results li",
    ".searchResultsItem",
    ".job-listing-item",
]


class ScotiabankScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_SCOT_SEARCH)
        time.sleep(5)
        self.slow_scroll(driver)

        rows = []
        for sel in _SAP_SF_ROW_SELS:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                rows = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(rows) > 1:
                    break
            except TimeoutException:
                continue

        if not rows:
            rows = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
            jobs = []
            for link in rows[:30]:
                title = self.safe_text(link)
                url   = self.safe_attr(link, "href")
                if title and self.is_data_role(title):
                    jobs.append(self.build_job(title=title, location="Canada", url=url))
            logger.info(f"[Scotiabank] link fallback: {len(jobs)} jobs")
            return jobs

        jobs = []
        for row in rows[:30]:
            try:
                title, url, location = "", "", ""
                for sel in _SAP_SF_TITLE_SELS:
                    try:
                        el    = row.find_element(By.CSS_SELECTOR, sel)
                        title = self.safe_text(el)
                        url   = self.safe_attr(el, "href")
                        if title:
                            break
                    except NoSuchElementException:
                        continue
                if not title:
                    continue
                for sel in _SAP_SF_LOCATION_SELS:
                    try:
                        location = self.safe_text(row.find_element(By.CSS_SELECTOR, sel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue
                jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue

        logger.info(f"[Scotiabank] SAP SF Selenium: {len(jobs)} jobs")
        return jobs


# ── GENERIC FALLBACK ────────────────────────────────────────────
class GenericScraper(BaseScraper):
    """
    ਕਿਸੇ ਵੀ company ਲਈ fallback
    Common job listing patterns try ਕਰਦਾ ਹੈ
    """
    CARD_SELECTORS = [
        "li[class*='job'], li[class*='result']",
        "article[class*='job'], div[class*='job-card']",
        ".job-listing, .job-result, .job-item",
        "[data-job-id], [data-requisition-id]",
        ".jv-job-list-result",
        ".opportunity-row",
    ]
    TITLE_SELECTORS = [
        "h2 a, h3 a, h4 a",
        "a[href*='/job'], a[href*='/career']",
        ".job-title a, .position-title a",
        "[class*='job-title'], [class*='position-name']",
    ]

    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs  = []
        cards = []

        for sel in self.CARD_SELECTORS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) > 2:
                break

        for card in cards[:20]:
            try:
                title = ""
                url   = ""
                for sel in self.TITLE_SELECTORS:
                    try:
                        el    = card.find_element(By.CSS_SELECTOR, sel)
                        title = self.safe_text(el)
                        url   = self.safe_attr(el, "href")
                        break
                    except NoSuchElementException:
                        title = self.safe_text(card)
                        url   = self.safe_attr(card, "href")

                if not title or len(title) < 5:
                    continue

                location = ""
                for loc_sel in [".location", "[class*='location']", ".city"]:
                    try:
                        location = self.safe_text(
                            card.find_element(By.CSS_SELECTOR, loc_sel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue

                jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue

        return jobs


# ── SCRAPER FACTORY ─────────────────────────────────────────────
def get_scraper(company: dict):
    """
    Company dict ਦੇ ਹਿਸਾਬ ਨਾਲ
    ਸਹੀ scraper return ਕਰਦਾ ਹੈ
    """
    name         = company["name"]
    scraper_type = company.get("scraper", "custom")

    # Dedicated scrapers
    dedicated = {
        "Google Canada":       GoogleScraper,
        "Amazon / AWS Canada": AmazonScraper,
        "Microsoft Canada":    MicrosoftScraper,
        "Meta Canada":         MetaScraper,
        "Apple Canada":        AppleScraper,
        "Netflix Canada":      NetflixScraper,   # API-based
        "Shopify":             ShopifyScraper,
        "IBM Canada":          IBMScraper,
        "Scotiabank":          ScotiabankScraper,
    }
    if name in dedicated:
        return dedicated[name](company)

    # Type-based scrapers
    type_map = {
        "greenhouse":        GreenhouseScraper,
        "lever":             LeverScraper,
        "workday":           WorkdayScraper,
        "phenom":            PhenomScraper,
        "smartrecruiters":   SmartRecruitersScraper,
        "ashby":             AshbyScraper,
        "avature":           AvatureScraper,
        "oracle_hcm":        OracleHCMScraper,
        "custom":            GenericScraper,
    }
    cls = type_map.get(scraper_type, GenericScraper)
    return cls(company)