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
                if title and self.is_data_role(title):
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
                if not title or not self.is_data_role(title):
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
_MS_SEARCH_URL = ("https://jobs.careers.microsoft.com/global/en/search"
                  "?q=data%20engineer&lc=Canada&l=en_us&pgSz=20&o=Recent")
_MS_CARD_SELS = [
    "a[href*='/global/en/job/']",
    "[class*='jobCard'] a",
    "[class*='job-card'] a",
    "a[href*='/en/job/']",
]
_MS_TITLE_SELS = [
    "[class*='jobTitle']", "[class*='job-title']",
    "h2", "h3", "[class*='title']",
]
_MS_LOC_SELS = [
    "[class*='jobLocation']", "[class*='location']",
    "[class*='Location']", "span[class*='loc']",
]


class MicrosoftScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_MS_SEARCH_URL)
        time.sleep(6)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[href*='/global/en/job/'], a[href*='/en/job/']")
                )
            )
        except TimeoutException:
            logger.warning("[Microsoft] Timed out waiting for job links")

        self.slow_scroll(driver)

        links = []
        for sel in _MS_CARD_SELS:
            links = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(links) > 1:
                logger.info(f"[Microsoft] {len(links)} job links with: {sel}")
                break

        jobs = []
        seen_urls = set()
        for link in links[:30]:
            try:
                url = self.safe_attr(link, "href")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = ""
                for tsel in _MS_TITLE_SELS:
                    try:
                        el = link.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        if title:
                            break
                    except NoSuchElementException:
                        continue
                if not title:
                    title = self.safe_text(link)
                if not title or not self.is_data_role(title):
                    continue

                location = ""
                parent = link
                for _ in range(4):
                    try:
                        parent = parent.find_element(By.XPATH, "..")
                    except Exception:
                        break
                    for lsel in _MS_LOC_SELS:
                        try:
                            location = self.safe_text(parent.find_element(By.CSS_SELECTOR, lsel))
                            if location:
                                break
                        except NoSuchElementException:
                            continue
                    if location:
                        break

                if not self.is_canada_job(location or "Canada"):
                    continue

                jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue

        logger.info(f"[Microsoft Canada] {len(jobs)} Canada data jobs via Selenium")
        return jobs


# ── META ────────────────────────────────────────────────────────
_META_CARD_SELS  = [
    "[data-testid='job-card']",
    "div[data-testid='job-listing-card']",
    "div[class*='job']",
    ".jobs-list-item",
    "li[class*='job']",
]
_META_TITLE_SELS = [
    "[data-testid='job-title']",
    "h3", "h2", "[class*='title']", "a span", "span",
]
_META_LOC_SELS   = [
    "[data-testid='job-listing-location']",
    "[class*='location']", ".location",
]


class MetaScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(6)
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "[data-testid='job-card'], a[href*='/profile/job_details/'], div[class*='job']")
                )
            )
        except TimeoutException:
            pass
        self.slow_scroll(driver)
        time.sleep(2)

        cards = []
        for sel in _META_CARD_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                cards = found
                logger.info(f"[Meta] {len(cards)} cards with: {sel}")
                break

        jobs = []
        if not cards:
            # fallback: extract directly from job detail links
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/job_details/']")
            seen: set = set()
            for link in links[:50]:
                try:
                    url = self.safe_attr(link, "href")
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    title = self.safe_text(link)
                    if not title:
                        try:
                            parent = link.find_element(By.XPATH, "..")
                            title = self.safe_text(parent)
                        except Exception:
                            pass
                    if not title or not self.is_data_role(title):
                        continue
                    location = ""
                    try:
                        parent = link.find_element(By.XPATH, "..")
                        location = self.safe_text(parent.find_element(
                            By.CSS_SELECTOR, "[class*='location'], span"))
                    except Exception:
                        pass
                    jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
                except Exception:
                    continue
            logger.info(f"[Meta] {len(jobs)} Canada data jobs (link fallback)")
            return jobs

        seen = set()
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
                if not title or not self.is_data_role(title):
                    continue
                try:
                    url = self.safe_attr(card.find_element(By.CSS_SELECTOR, "a"), "href")
                except NoSuchElementException:
                    pass
                if url in seen:
                    continue
                seen.add(url)
                for lsel in _META_LOC_SELS:
                    try:
                        location = self.safe_text(card.find_element(By.CSS_SELECTOR, lsel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue
                jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue

        logger.info(f"[Meta] {len(jobs)} Canada data jobs")
        return jobs


# ── APPLE ───────────────────────────────────────────────────────
_APPLE_CARD_SELS  = [
    "tr.table-row",
    "div.table-row",
    "tbody tr",
    "[class*='table-row']",
    "li[class*='job']",
]
_APPLE_TITLE_SELS = [
    "a.table--advanced-search__title",
    "a[href*='/details/']",
    "a",
]
_APPLE_LOC_SELS = [
    "span.table--advanced-search__job-location",
    ".table-col-2",
    "[class*='location']",
    "td:nth-child(2)",
]


class AppleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[href*='/details/'], tr.table-row, div.table-row")
                )
            )
        except TimeoutException:
            pass
        self.slow_scroll(driver)

        cards = []
        for sel in _APPLE_CARD_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                cards = found
                logger.info(f"[Apple] {len(cards)} cards with: {sel}")
                break

        jobs = []
        if not cards:
            # fallback: extract from job detail links directly
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/details/']")
            seen: set = set()
            for link in links[:50]:
                try:
                    url = self.safe_attr(link, "href")
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    title = self.safe_text(link)
                    if not title:
                        # parse title from URL slug: /details/{id}/{slug}?team=X
                        slug = url.split("/details/")[-1].split("?")[0]
                        parts = slug.split("/")
                        if len(parts) > 1:
                            title = parts[-1].replace("-", " ").title()
                    if not title or not self.is_data_role(title):
                        continue
                    location = ""
                    try:
                        parent = link.find_element(By.XPATH, "..")
                        location = self.safe_text(parent.find_element(
                            By.CSS_SELECTOR, "span[class*='location'], span[class*='subtitle']"))
                    except Exception:
                        pass
                    jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
                except Exception:
                    continue
            logger.info(f"[Apple] {len(jobs)} Canada data jobs (link fallback)")
            return jobs

        seen = set()
        for card in cards[:50]:
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
                if not title or not self.is_data_role(title):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                if url and not url.startswith("http"):
                    url = "https://jobs.apple.com" + url
                for lsel in _APPLE_LOC_SELS:
                    try:
                        location = self.safe_text(card.find_element(By.CSS_SELECTOR, lsel))
                        if location:
                            break
                    except NoSuchElementException:
                        continue
                jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue

        logger.info(f"[Apple] {len(jobs)} Canada data jobs")
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


# ── GENERIC j2w (SAP SuccessFactors Jobs2Web) SELENIUM ──────────
# Reusable for Scotiabank, Deloitte, SAP Canada, TELUS Health, etc.
# Uses self.careers_url from settings.py (must be the search-results page)

_J2W_UNIFY_SELS = [
    "[class*='jobResultsCard'] a",
    "[class*='jobResults'] a[href*='/job/']",
    ".jobResultsCardHeader a",
    ".jobResultsCardBody a",
    "div[class*='jobResult'] a",
]
_J2W_LEGACY_SELS = [
    "tr.even a.jobTitle, tr.odd a.jobTitle",
    "a.jobTitle",
    "td.jobTitle a",
    "a[href*='/job/'][class*='jd']",
]


class J2WScraper(BaseScraper):
    """Generic SAP SuccessFactors j2w Unify Selenium scraper."""

    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(10)
        self.slow_scroll(driver)
        time.sleep(3)

        links = []
        for sel in _J2W_UNIFY_SELS + _J2W_LEGACY_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                links = found
                logger.info(f"[{self.company_name}] {len(found)} links via: {sel}")
                break

        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
            if links:
                logger.info(f"[{self.company_name}] link fallback: {len(links)}")
            else:
                logger.warning(f"[{self.company_name}] no job links found in DOM")
                return []

        seen_urls: set = set()
        jobs = []
        for link in links[:50]:
            try:
                title = self.safe_text(link)
                url   = self.safe_attr(link, "href")
                if not title or not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                if not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            except Exception:
                continue

        logger.info(f"[{self.company_name}] j2w: {len(jobs)} jobs")
        return jobs


# ── SCOTIABANK (j2w — hardcoded search URL) ──────────────────────
_SCOT_SEARCH = (
    "https://jobs.scotiabank.com/search-results"
    "?keywords=data+engineer&location=Canada&locale=en_US"
)


class ScotiabankScraper(J2WScraper):
    def scrape(self, driver) -> list:
        self.careers_url = _SCOT_SEARCH
        return super().scrape(driver)


# ── BANK OF CANADA (j2w RSS — domestic employer, all jobs are Canada) ──
_BOC_RSS = (
    "https://careers.bankofcanada.ca/services/rss/job/"
    "?locale=en_US&keywords=data+engineer"
)


class BankOfCanadaScraper(BaseScraper):
    def scrape(self, driver) -> list:
        try:
            import xml.etree.ElementTree as ET
            r = requests.get(_BOC_RSS, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code != 200:
                logger.warning(f"[Bank of Canada] RSS {r.status_code}")
                return []
            root = ET.fromstring(r.content)
            jobs = []
            for item in root.findall(".//item"):
                raw_title = (item.findtext("title") or "").strip()
                url       = (item.findtext("link") or "").strip()
                title = raw_title.split("(")[0].strip() if "(" in raw_title else raw_title
                if not self.is_data_role(title):
                    continue
                try:
                    loc_str = raw_title[raw_title.index("(")+1 : raw_title.rindex(")")]
                    location = loc_str.split(",")[0].strip()
                except ValueError:
                    location = "Ottawa"
                jobs.append(self.build_job(title=title, location=location, url=url))
            logger.info(f"[Bank of Canada] RSS: {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.warning(f"[Bank of Canada] RSS failed: {e}")
            return []


# ── UBER CANADA ─────────────────────────────────────────────────
_UBER_URL = "https://www.uber.com/global/en/careers/list/?query=data+engineer&location=Toronto"
_UBER_JOB_SELS = [
    "a[href*='/careers/list/']",
    "[data-testid='job-title'] a",
    "li[class*='job'] a",
    ".job-title a",
]

class UberScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_UBER_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _UBER_JOB_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Uber] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/careers/']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Toronto", url=url))
        logger.info(f"[Uber] {len(jobs)} jobs")
        return jobs


# ── INTUIT CANADA ────────────────────────────────────────────────
_INTUIT_URL = "https://jobs.intuit.com/search-jobs?k=data+engineer&l=Canada"
_INTUIT_SELS = [
    ".job-listing-name a",
    ".job-title-link",
    "a.job-title",
    "h3.job-title a",
    "ul.jobs-list li a",
    ".search-result-jobTitle a",
    "a[href*='/job/'][href*='intuit']",
]

class IntuitScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_INTUIT_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _INTUIT_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                links = found
                logger.info(f"[Intuit] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[Intuit] {len(jobs)} jobs")
        return jobs


# ── CLIO ─────────────────────────────────────────────────────────
_CLIO_URL = "https://jobs.ashbyhq.com/clio"
_CLIO_SELS = [
    "a[href*='/clio/']",
    "[class*='ashby-job'] a",
    "[class*='posting'] a",
    "div[class*='job'] a",
    "li a[href*='ashbyhq']",
]

class ClioScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_CLIO_URL)
        time.sleep(6)
        self.slow_scroll(driver)
        time.sleep(2)
        links = []
        for sel in _CLIO_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Clio] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='ashbyhq']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[Clio] {len(jobs)} jobs")
        return jobs


# ── COVEO ─────────────────────────────────────────────────────────
_COVEO_URL = "https://www.coveo.com/en/company/careers/open-positions"
_COVEO_SELS = [
    "li.opening a",
    ".opening a",
    "a[href*='/careers/']",
    "[class*='job'] a",
    "li a",
]

class CoveoScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_COVEO_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _COVEO_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Coveo] {len(links)} links with: {sel}")
                break
        seen: set = set()
        jobs = []
        for link in links[:80]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Quebec City", url=url))
        logger.info(f"[Coveo] {len(jobs)} jobs")
        return jobs


# ── ATLASSIAN CANADA ─────────────────────────────────────────────
_ATLASSIAN_URL = (
    "https://www.atlassian.com/company/careers/all-jobs"
    "?team=Engineering&location=Canada"
)
_ATLASSIAN_SELS = [
    "a[href*='/careers/details/']",
    "[class*='job-listing'] a",
    "[class*='job-card'] a",
    "[class*='JobResult'] a",
    "li[class*='job'] a",
]

class AtlassianScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_ATLASSIAN_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _ATLASSIAN_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Atlassian] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/careers/']")
        seen: set = set()
        jobs = []
        for link in links[:60]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[Atlassian] {len(jobs)} jobs")
        return jobs


# ── COGNIZANT CANADA ─────────────────────────────────────────────
_COGNIZANT_URL = "https://careers.cognizant.com/ca-en/search-results?keywords=data+engineer"
_COGNIZANT_SELS = [
    "[class*='job-title'] a",
    "[class*='jobTitle'] a",
    ".job-list-item a",
    "li[class*='job'] a",
    "a[href*='/ca-en/job/']",
    "a[href*='/jobs/']",
]

class CognizantScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_COGNIZANT_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _COGNIZANT_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Cognizant] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[Cognizant] {len(jobs)} jobs")
        return jobs


# ── TCS CANADA ───────────────────────────────────────────────────
_TCS_URL = "https://ibegin.tcsapps.com/candidate/jobs?searchTerm=data+engineer&countryId=38"
_TCS_SELS = [
    ".job-title a",
    "[class*='job-title'] a",
    ".iBeginJobCard a",
    "a[href*='/candidate/jobs/']",
    "[class*='job-listing'] a",
    ".card-body a",
]

class TCSScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_TCS_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _TCS_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[TCS] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/candidate/jobs/']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[TCS] {len(jobs)} jobs")
        return jobs


# ── KINAXIS ───────────────────────────────────────────────────────
_KINAXIS_URL = (
    "https://careers-kinaxis.icims.com/jobs/search"
    "?ss=1&searchKeyword=data+engineer&searchLocation=Canada"
)
_KINAXIS_SELS = [
    ".iCIMS_JobListingRow .iCIMS_Anchor",
    ".iCIMS_Anchor",
    "a.iCIMS_Anchor",
    ".iCIMS_JobTitleText a",
    "table.iCIMS_JobsTable a",
]

class KinaxisScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_KINAXIS_URL)
        time.sleep(6)
        self.slow_scroll(driver)
        time.sleep(2)
        links = []
        for sel in _KINAXIS_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                links = found
                logger.info(f"[Kinaxis] {len(links)} links with: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='icims.com/jobs/']")
        seen: set = set()
        jobs = []
        for link in links[:50]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if not title or not url or url in seen:
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location="Ottawa", url=url))
        logger.info(f"[Kinaxis] {len(jobs)} jobs")
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
        "Google Canada":              GoogleScraper,
        "Amazon / AWS Canada":        AmazonScraper,
        "Microsoft Canada":           MicrosoftScraper,
        "Meta Canada":                MetaScraper,
        "Apple Canada":               AppleScraper,
        "Netflix Canada":             NetflixScraper,
        "Shopify":                    ShopifyScraper,
        "IBM Canada":                 IBMScraper,
        "Scotiabank":                 ScotiabankScraper,
        # j2w (SAP SuccessFactors) Selenium scrapers
        "Deloitte Canada":            J2WScraper,
        "SAP Canada":                 J2WScraper,
        "TELUS Health":               J2WScraper,
        "Scotiabank Digital Factory": J2WScraper,
        # j2w RSS scraper
        "Bank of Canada":             BankOfCanadaScraper,
        # Custom Selenium scrapers
        "Atlassian Canada":            AtlassianScraper,
        "Cognizant Canada":            CognizantScraper,
        "TCS Canada":                  TCSScraper,
        # j2w (SAP SuccessFactors) — Wipro and Capgemini use same platform
        "Wipro Canada":                J2WScraper,
        "Capgemini Canada":            J2WScraper,
        "Uber Canada":                UberScraper,
        "Intuit Canada":              IntuitScraper,
        "Clio":                       ClioScraper,
        "Coveo":                      CoveoScraper,
        "Kinaxis":                    KinaxisScraper,
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