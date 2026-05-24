import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_scraper import BaseScraper, HTTP_HEADERS, get_session

logger = logging.getLogger(__name__)

JOB_CARD_SELECTORS = [
    "[data-automation-id='jobItem']",
    "li[data-automation-id='jobItem']",
    "[data-automation-id='compositeContainer'] li",
    "ul[data-automation-id='jobResults'] li",
    "li[class*='css-'][data-automation-id]",
    # 2025+ Workday DOM — data-automation-id based (more stable than class names)
    "[data-automation-id='jobResults'] [data-automation-id='jobItem']",
    "section[data-automation-id='jobResults'] li",
    "ul[role='list'] > li",
    "li[class*='css-']",
    "li.css-1q2dra3",  # old selector — kept as last resort
    "[class*='job-listing'] li",
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

    def _location_facets(self) -> dict:
        """Extract locationCountry/locationHierarchy facet IDs from the careers URL."""
        from urllib.parse import urlparse, parse_qs
        params = parse_qs(urlparse(self.careers_url).query)
        facets: dict = {}
        if "locationCountry" in params:
            facets["locationCountry"] = params["locationCountry"]
        if "locationHierarchy" in params:
            facets["locationHierarchy"] = params["locationHierarchy"]
        return facets

    def _scrape_api(self):
        if not self._tenant:
            return None

        api_url = (f"https://{self._tenant}.{self._wd}.myworkdayjobs.com"
                   f"/wday/cxs/{self._tenant}/{self._board}/jobs")

        location_facets = self._location_facets()

        try:
            # Workday limit: some tenants reject limit>20, so use 20 for safety
            PAGE = 20
            all_postings = []
            offset = 0
            while True:
                body = {"appliedFacets": location_facets, "limit": PAGE, "offset": offset, "searchText": "data engineer"}
                session = get_session()
                r = session.post(api_url, headers=HTTP_HEADERS, json=body, timeout=8)
                if r.status_code == 400 and location_facets and offset == 0:
                    location_facets = {}
                    body["appliedFacets"] = {}
                    r = session.post(api_url, headers=HTTP_HEADERS, json=body, timeout=8)
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
                # Some Workday tenants (e.g. Accenture) return empty locationsText even when
                # locationCountry facet is applied — fall back to bulletFields for location text
                if not location:
                    bullets = p.get("bulletFields", [])
                    location = next((b for b in bullets if any(
                        kw in b.lower() for kw in ["canada","toronto","montreal","vancouver","ottawa","calgary","remote"]
                    )), "Canada")
                if not self.is_canada_job(location):
                    continue
                path = p.get("externalPath", "")
                job_url = (f"https://{self._tenant}.{self._wd}.myworkdayjobs.com/{self._board}{path}"
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

    def _extract_from_links(self, driver) -> list:
        """Extract jobs directly from <a> tags — fallback when card selectors fail.
        Trusts the locationCountry facet already applied in the URL, so skips is_canada_job."""
        try:
            links = driver.find_elements(By.CSS_SELECTOR,
                "a[data-automation-id='jobTitle'], a[href*='/job/'], a[href*='myworkdayjobs']")
            seen, jobs = set(), []
            for link in links[:60]:
                title = self.safe_text(link)
                url   = self.safe_attr(link, "href")
                if not title or not url or url in seen:
                    continue
                seen.add(url)
                if not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            if jobs:
                logger.info(f"[{self.company_name}] link fallback: {len(jobs)} jobs")
            return jobs
        except Exception:
            return []

    def _selenium_url(self) -> str:
        """Return a clean Workday URL for Selenium — strip ?q= so the SPA renders the full
        job board instead of a filtered search results page (which uses a different DOM)."""
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        parsed = urlparse(self.careers_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Keep locationCountry/locationHierarchy (Canada filter), drop keyword search
        params.pop("q", None)
        params.pop("keywords", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    def _scrape_selenium(self, driver) -> list:
        url = self._selenium_url()
        driver.get(url)
        time.sleep(10)  # Workday SPAs need extra time

        # Wait for job results container
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "[data-automation-id='jobItem'], [data-automation-id='jobResults'], "
                     "ul[role='list'], li[class*='css-'], a[data-automation-id='jobTitle']")
                )
            )
        except TimeoutException:
            pass

        cards = []
        for sel in JOB_CARD_SELECTORS:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(cards) > 1:
                    logger.info(f"[{self.company_name}] Selenium cards with: {sel}")
                    break
            except Exception:
                continue

        if not cards:
            try:
                self.slow_scroll(driver)
                time.sleep(5)
                self.slow_scroll(driver)
                time.sleep(3)
                cards = self._find_job_cards(driver)
            except Exception:
                pass

        if not cards:
            # Last resort: extract job links directly from page
            jobs = self._extract_from_links(driver)
            if jobs:
                return jobs
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
