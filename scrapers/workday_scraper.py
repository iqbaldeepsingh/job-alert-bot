import re
import time
import logging
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_scraper import BaseScraper, HTTP_HEADERS

logger = logging.getLogger(__name__)

JOB_CARD_SELECTORS = [
    "[data-automation-id='jobItem']",
    "li[class*='css-'][data-automation-id]",
    "li.css-1q2dra3",
    "[data-automation-id='compositeContainer']",
    "ul[role='list'] li",
    ".css-1q2dra3",
    "li[class*='css-']",
]


def _parse_workday_url(url: str):
    m = re.search(r"https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/([^/?]+)", url)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None, None, None


class WorkdayScraper(BaseScraper):

    def __init__(self, company: dict):
        super().__init__(company)
        self._tenant, self._wd, self._board = _parse_workday_url(self.careers_url)

    def scrape(self, driver) -> list:
        jobs = self._scrape_api()
        if jobs is not None:
            return jobs
        logger.info(f"[{self.company_name}] API failed — falling back to Selenium")
        return self._scrape_selenium(driver)

    # ── Workday JSON API (fast, no browser needed) ───────────────

    def _scrape_api(self):
        if not self._tenant:
            return None

        api_url = (f"https://{self._tenant}.{self._wd}.myworkdayjobs.com"
                   f"/wday/cxs/{self._tenant}/{self._board}/jobs")

        try:
            # Workday limit: some tenants reject limit>20, so use 20 for safety
            PAGE = 20
            all_postings = []
            offset = 0
            while True:
                body = {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": "data engineer"}
                r = requests.post(api_url, headers=HTTP_HEADERS, json=body, timeout=12)
                if r.status_code != 200:
                    return None
                data = r.json()
                page_postings = data.get("jobPostings", [])
                all_postings.extend(page_postings)
                total = data.get("total", 0)
                if offset == 0:
                    logger.info(f"[{self.company_name}] API: {total} total postings")
                offset += PAGE
                if offset >= total or not page_postings:
                    break

            postings = all_postings
            jobs = []
            for p in postings:
                title = p.get("title", "")
                if not self.is_data_role(title):
                    continue
                location = p.get("locationsText", "") or p.get("primaryLocation", "")
                if not self.is_canada_job(location):
                    continue
                path = p.get("externalPath", "")
                job_url = (f"https://{self._tenant}.{self._wd}.myworkdayjobs.com{path}"
                           if path else self.careers_url)
                posted = p.get("postedOn", "Recent")
                jobs.append(self.build_job(title=title, location=location, url=job_url, posted=posted))

            return jobs

        except Exception as e:
            logger.debug(f"[{self.company_name}] API error: {e}")
            return None

    # ── Selenium fallback ────────────────────────────────────────

    def _find_job_cards(self, driver):
        for sel in JOB_CARD_SELECTORS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                return cards
        return []

    def _scrape_selenium(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(5)

        cards = []
        for sel in JOB_CARD_SELECTORS:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    logger.info(f"[{self.company_name}] Selenium cards with: {sel}")
                    break
            except TimeoutException:
                continue

        if not cards:
            try:
                driver.execute_script("window.scrollTo(0, 500)")
                time.sleep(3)
                cards = self._find_job_cards(driver)
            except Exception:
                pass

        if not cards:
            logger.warning(f"[{self.company_name}] Selenium: no job cards found")
            return []

        self.slow_scroll(driver)
        time.sleep(2)
        cards = self._find_job_cards(driver)

        jobs = []
        for card in cards[:25]:
            try:
                title, url, location, posted = "", "", "", "Recent"

                for tsel in [
                    "[data-automation-id='jobTitle']",
                    "a[data-automation-id='jobTitle']",
                    "h3 a", "h2 a",
                    "a[href*='/job/']",
                    "a[href*='myworkdayjobs']",
                    ".css-19uc56f",
                    "a",
                ]:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, tsel)
                        title = self.safe_text(el)
                        url = self.safe_attr(el, "href")
                        if title:
                            break
                    except NoSuchElementException:
                        continue

                if not title:
                    continue

                for lsel in [
                    "[data-automation-id='locations']",
                    "[data-automation-id='location']",
                    "dd[class*='css-']",
                    ".css-129m7dg",
                    "[class*='location']",
                    "dl dd",
                ]:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, lsel)
                        location = self.safe_text(el)
                        if location:
                            break
                    except NoSuchElementException:
                        continue

                for dsel in [
                    "[data-automation-id='postedOn']",
                    "dd[class*='css-']:last-child",
                ]:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, dsel)
                        posted = self.safe_text(el) or "Recent"
                        if posted:
                            break
                    except NoSuchElementException:
                        continue

                jobs.append(self.build_job(title=title, location=location, posted=posted, url=url))

            except Exception as e:
                logger.debug(f"[{self.company_name}] Card error: {e}")
                continue

        return jobs
