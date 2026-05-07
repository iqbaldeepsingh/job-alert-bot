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
        time.sleep(5)

        jobs = []

        # Try multiple Workday selectors
        JOB_CARD_SELECTORS = [
            "li[class*='css-'][data-automation-id]",
            "[data-automation-id='jobItem']",
            "li.css-1q2dra3",
            "[data-automation-id='compositeContainer']",
            "ul[role='list'] li",
            ".css-1q2dra3",
            "li[class*='css-']",
        ]

        cards = []
        for sel in JOB_CARD_SELECTORS:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(cards) > 0:
                    logger.info(f"[{self.company_name}] Found cards with: {sel}")
                    break
            except TimeoutException:
                continue

        if not cards:
            # Try JavaScript approach
            try:
                driver.execute_script("window.scrollTo(0, 500)")
                time.sleep(3)
                for sel in JOB_CARD_SELECTORS:
                    cards = driver.find_elements(By.CSS_SELECTOR, sel)
                    if cards:
                        break
            except Exception:
                pass

        if not cards:
            logger.warning(f"[{self.company_name}] No job cards found")
            return []

        self.slow_scroll(driver)
        time.sleep(2)

        # Re-fetch after scroll
        for sel in JOB_CARD_SELECTORS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        for card in cards[:25]:
            try:
                title = ""
                url = ""
                location = ""
                posted = "Recent"

                # Title selectors
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

                # Location selectors
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

                # Posted date
                for dsel in [
                    "[data-automation-id='postedOn']",
                    "dd[class*='css-']:last-child",
                    ".css-1q2dra3 dd:last-child",
                ]:
                    try:
                        el = card.find_element(By.CSS_SELECTOR, dsel)
                        posted = self.safe_text(el) or "Recent"
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
