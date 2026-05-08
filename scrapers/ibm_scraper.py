import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_SEARCH_URL = (
    "https://careers.ibm.com/jobs"
    "?field_keyword_08[0]=data%20engineer"
    "&field_country_tax_name[0]=Canada"
)

_JOB_LINK_SELECTORS = [
    "a[href*='/job/']",
    ".job-list-item a",
    "li.ibm-job-result a",
    ".ibm--grid a[href*='jobId']",
    "a[data-jobid]",
]

_TITLE_SELECTORS = [
    ".job-title", "h3", "h2", "[class*='title']",
]

_LOCATION_SELECTORS = [
    ".job-location", ".location", "[class*='location']",
]

_CARD_SELECTORS = [
    ".ibm-col-sm-4.ibm-col-medium-4",
    "li.ibm-job-result",
    ".job-listing-item",
    ".job-result",
    "article",
]


class IBMScraper(BaseScraper):

    def scrape(self, driver) -> list:
        driver.get(_SEARCH_URL)
        time.sleep(6)

        # Wait for job listings to appear
        cards = []
        for sel in _CARD_SELECTORS:
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(cards) > 1:
                    logger.info(f"[IBM] Found {len(cards)} cards with: {sel}")
                    break
            except TimeoutException:
                continue

        # Fallback: try job links directly
        if not cards:
            self.slow_scroll(driver)
            time.sleep(3)
            for sel in _CARD_SELECTORS:
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(cards) > 1:
                    break

        if not cards:
            # Last resort: grab all job-related links
            logger.warning("[IBM] No job cards found — trying link extraction")
            return self._extract_from_links(driver)

        self.slow_scroll(driver)
        time.sleep(2)

        jobs = []
        for card in cards[:25]:
            try:
                title, url, location = "", "", ""

                for tsel in _TITLE_SELECTORS:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        if title:
                            break
                    except NoSuchElementException:
                        continue

                if not title:
                    try:
                        link_el = card.find_element(By.CSS_SELECTOR, "a")
                        title = self.safe_text(link_el)
                        url = self.safe_attr(link_el, "href")
                    except NoSuchElementException:
                        continue

                if not title:
                    continue

                if not url:
                    try:
                        url = self.safe_attr(card.find_element(By.CSS_SELECTOR, "a"), "href")
                    except NoSuchElementException:
                        pass

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

                jobs.append(self.build_job(title=title, location=location, url=url))
            except Exception as e:
                logger.debug(f"[IBM] Card error: {e}")
                continue

        logger.info(f"[IBM] Selenium: {len(jobs)} jobs before filter")
        return jobs

    def _extract_from_links(self, driver) -> list:
        jobs = []
        for sel in _JOB_LINK_SELECTORS:
            links = driver.find_elements(By.CSS_SELECTOR, sel)
            if links:
                for link in links[:25]:
                    title = self.safe_text(link)
                    url = self.safe_attr(link, "href")
                    if title and len(title) > 5:
                        jobs.append(self.build_job(title=title, location="Canada", url=url))
                break
        return jobs
