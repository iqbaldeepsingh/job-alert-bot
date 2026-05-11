import time
import logging
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# IBM Canada job search — updated URL (old /jobs path returns 404)
_SEARCH_URL = (
    "https://careers.ibm.com/en_US/careers/search"
    "?q=data+engineer&location=Canada"
)

# IBM uses a custom SPA; selectors as of 2025
_CARD_SELECTORS = [
    "[data-ph-id]",                        # IBM PeopleHQ job cards
    ".job-tile",
    ".ibm-job-tile",
    "li.job-listing-item",
    "li[class*='job']",
    ".positions-list li",
    "article[class*='job']",
    ".job-result-card",
    "[class*='job-card']",
    "[class*='position']",
]

_TITLE_SELECTORS = [
    "[data-ph-id='ph-job-title'] a",
    ".job-title a",
    ".position-title a",
    "h3 a", "h2 a",
    "a[href*='/careers/JobDetail']",
    "a[href*='/en_US/careers/']",
    ".title a",
    "a",
]

_LOCATION_SELECTORS = [
    "[data-ph-id='ph-job-location']",
    ".job-location",
    ".location",
    "[class*='location']",
    "[class*='city']",
]


class IBMScraper(BaseScraper):

    def scrape(self, driver) -> list:
        # Try API first (IBM uses a GraphQL/REST endpoint internally)
        jobs = self._try_api()
        if jobs is not None:
            return jobs

        # Fall back to Selenium
        return self._scrape_selenium(driver)

    def _try_api(self):
        """IBM careers API — returns None if unavailable."""
        try:
            r = requests.get(
                "https://careers.ibm.com/api/jobs/v1/search",
                params={"keyword": "data engineer", "country": "Canada",
                        "start": 0, "limit": 50},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            jobs = []
            for item in data.get("jobs", data.get("results", [])):
                title = item.get("title", "") or item.get("jobTitle", "")
                if not self.is_data_role(title):
                    continue
                location = (item.get("location", "") or
                            item.get("primaryLocation", "") or "Canada")
                if not self.is_canada_job(location):
                    continue
                url = (item.get("url", "") or
                       item.get("applyUrl", "") or
                       f"https://careers.ibm.com/en_US/careers/JobDetail?jobId={item.get('jobId','')}")
                jobs.append(self.build_job(title=title, location=location, url=url))
            logger.info(f"[IBM Canada] API: {len(jobs)} jobs")
            return jobs
        except Exception:
            return None

    def _scrape_selenium(self, driver) -> list:
        driver.get(_SEARCH_URL)
        time.sleep(5)
        # Detect AWS WAF challenge — page has no useful content
        page_src = driver.page_source
        if "AwsWafIntegration" in page_src or "challenge-container" in page_src:
            logger.warning("[IBM] AWS WAF bot-protection detected — skipping")
            return []

        cards = []
        for sel in _CARD_SELECTORS:
            try:
                WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                found = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(found) > 1:
                    cards = found
                    logger.info(f"[IBM] {len(cards)} cards with: {sel}")
                    break
            except TimeoutException:
                continue

        if not cards:
            self.slow_scroll(driver)
            time.sleep(3)
            for sel in _CARD_SELECTORS:
                found = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(found) > 1:
                    cards = found
                    break

        if not cards:
            # Last resort: grab all job-related links
            logger.warning("[IBM] No cards found — extracting links")
            return self._extract_from_links(driver)

        self.slow_scroll(driver)
        time.sleep(2)

        jobs = []
        for card in cards[:30]:
            try:
                title, url, location = "", "", ""

                for tsel in _TITLE_SELECTORS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        url = self.safe_attr(el, "href")
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

                if not title or len(title) < 4 or not self.is_data_role(title):
                    continue

                for lsel in _LOCATION_SELECTORS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, lsel)
                        location = self.safe_text(el)
                        if location:
                            break
                    except NoSuchElementException:
                        continue

                if not location:
                    location = "Canada"
                if not self.is_canada_job(location):
                    continue

                jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception as e:
                logger.debug(f"[IBM] Card error: {e}")
                continue

        logger.info(f"[IBM] Selenium: {len(jobs)} jobs before filter")
        return jobs

    def _extract_from_links(self, driver) -> list:
        jobs = []
        links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/careers/JobDetail'], a[href*='/en_US/careers/'], a[href*='jobId']")
        for link in links[:30]:
            title = self.safe_text(link)
            url = self.safe_attr(link, "href")
            if title and len(title) > 5 and self.is_data_role(title):
                jobs.append(self.build_job(title=title, location="Canada", url=url))
        logger.info(f"[IBM] Link extraction: {len(jobs)} jobs")
        return jobs
