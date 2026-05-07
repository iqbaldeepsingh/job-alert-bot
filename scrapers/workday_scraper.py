"""
Workday Scraper
RBC, CIBC, BMO, National Bank, Manulife, Bell Canada,
Loblaw, Walmart Canada, Thomson Reuters, Nvidia, etc.
ਸਾਰੇ Workday sites ਦਾ same DOM structure ਹੈ
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):

    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(3)

        # Workday job list ਲੋਡ ਹੋਣ ਦੀ ਉਡੀਕ
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "[data-automation-id='jobItem'],"
                    "li[class*='css-'],"
                    ".css-1q2dra3"
                ))
            )
        except TimeoutException:
            logger.warning(f"[{self.company_name}] Workday job list not found")
            return []

        self.slow_scroll(driver)
        time.sleep(1)

        # Job cards ਲੱਭੋ
        cards = []
        for sel in [
            "[data-automation-id='jobItem']",
            "li[class*='css-']",
            ".css-1q2dra3",
        ]:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        jobs = []
        for card in cards[:25]:
            try:
                # Title
                title_el = None
                for sel in [
                    "[data-automation-id='jobTitle']",
                    "a[href*='/job/']",
                    "h3 a",
                ]:
                    try:
                        title_el = card.find_element(By.CSS_SELECTOR, sel)
                        break
                    except NoSuchElementException:
                        continue

                title = self.safe_text(title_el)
                if not title:
                    continue

                url = self.safe_attr(title_el, "href") if title_el else ""

                # Location
                location = ""
                for sel in [
                    "[data-automation-id='locations']",
                    "dd[data-automation-id]",
                    ".css-129m7dg",
                ]:
                    try:
                        loc_el   = card.find_element(By.CSS_SELECTOR, sel)
                        location = self.safe_text(loc_el)
                        if location:
                            break
                    except NoSuchElementException:
                        continue

                # Posted date
                posted = "Recent"
                for sel in [
                    "[data-automation-id='postedOn']",
                    "dd[class*='css-']:last-child",
                ]:
                    try:
                        date_el = card.find_element(By.CSS_SELECTOR, sel)
                        posted  = self.safe_text(date_el) or "Recent"
                        if posted:
                            break
                    except NoSuchElementException:
                        continue

                jobs.append(self.build_job(
                    title=title,
                    location=location,
                    posted=posted,
                    url=url,
                ))

            except Exception as e:
                logger.debug(f"[{self.company_name}] Card error: {e}")
                continue

        return jobs