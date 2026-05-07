"""
Custom Scrapers
Google, Amazon, Microsoft, Meta, Apple, Netflix,
Uber, LinkedIn, Spotify, Deloitte, CGI, TD Bank,
Scotiabank, Rogers, Telus, Bell, + Generic fallback
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from scrapers.base_scraper import BaseScraper
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.workday_scraper import WorkdayScraper

logger = logging.getLogger(__name__)


# ── GOOGLE ──────────────────────────────────────────────────────
class GoogleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            "li.lLd3Je, .sMn82b, li[jsmodel], .job-result")
        for card in cards[:20]:
            try:
                title = self.safe_text(
                    card.find_element(By.CSS_SELECTOR, "h3, .QJPWVe, .job-title"))
                location = self.safe_text(
                    card.find_element(By.CSS_SELECTOR, ".r0wTof, .location, .job-location"))
                try:
                    url = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                except NoSuchElementException:
                    url = ""
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── AMAZON ──────────────────────────────────────────────────────
class AmazonScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            "div[data-test='result'], .job-tile, .result-container")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR,
                    "h3 a, .job-title a, a[href*='/jobs/']")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    ".location-and-id, .job-location, [class*='location']"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── MICROSOFT ───────────────────────────────────────────────────
class MicrosoftScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            "div[class*='ms-List-cell'], li.ms-List-cell")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR,
                    "a[href*='/global/en/job/']")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    "span[aria-label*='location'], .location"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── META ────────────────────────────────────────────────────────
class MetaScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            "div[data-testid='job-listing-card'], ._8muv")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR,
                    "a span, ._8hq4 span")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(
                    card.find_element(By.CSS_SELECTOR, "a"), "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    "[data-testid='job-listing-location'], ._8hq6"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── APPLE ───────────────────────────────────────────────────────
class AppleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            "tbody tr, .table--advanced-search__title")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR,
                    "a, .table--advanced-search__title")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                if url and not url.startswith("http"):
                    url = "https://jobs.apple.com" + url
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    ".table-col-2, .location"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception:
                continue
        return jobs


# ── NETFLIX ─────────────────────────────────────────────────────
class NetflixScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(4)
        self.slow_scroll(driver)
        jobs = []
        cards = driver.find_elements(By.CSS_SELECTOR,
            ".opportunity, li[class*='css-'], .job-result")
        for card in cards[:20]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "a, h3")
                title    = self.safe_text(title_el)
                url      = self.safe_attr(title_el, "href")
                location = self.safe_text(card.find_element(By.CSS_SELECTOR,
                    "[class*='location'], .location"))
                if title:
                    jobs.append(self.build_job(title=title, location=location, url=url))
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
        "Netflix Canada":      NetflixScraper,
        "TD Bank":             TDBankScraper,
        "Scotiabank":          ScotiabankScraper,
    }
    if name in dedicated:
        return dedicated[name](company)

    # Type-based scrapers
    type_map = {
        "greenhouse": GreenhouseScraper,
        "lever":      LeverScraper,
        "workday":    WorkdayScraper,
        "custom":     GenericScraper,
    }
    cls = type_map.get(scraper_type, GenericScraper)
    return cls(company)