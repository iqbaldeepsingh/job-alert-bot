"""
Custom Scrapers
Google, Amazon, Microsoft, Meta, Apple, Netflix,
Uber, LinkedIn, Spotify, Deloitte, CGI, TD Bank,
Scotiabank, Rogers, Telus, Bell, + Generic fallback
"""

import re
import json
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
_META_OFFICES = [
    "Toronto, ON", "Ottawa, Canada", "Montreal, Canada",
    "Remote, Canada", "Vancouver, Canada",
]
_META_GQL_URL = "https://www.metacareers.com/graphql"
_META_DOC_ID  = "29615178951461218"  # CareersJobSearchResultsDataQuery


class MetaScraper(BaseScraper):
    def scrape(self, driver) -> list:
        page_url = (
            "https://www.metacareers.com/jobsearch?"
            "offices[0]=Toronto%2C%20ON&offices[1]=Ottawa%2C%20Canada"
            "&offices[2]=Montreal%2C%20Canada&offices[3]=Remote%2C%20Canada"
            "&offices[4]=Vancouver%2C%20Canada"
        )
        driver.get(page_url)
        time.sleep(8)

        # Extract session LSD token from page source
        lsd = ""
        m = re.search(r'"LSD",\[\],\{"token":"([^"]+)"\}', driver.page_source)
        if m:
            lsd = m.group(1)

        if lsd:
            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
            variables = {
                "search_input": {
                    "q": None, "divisions": [], "offices": _META_OFFICES,
                    "roles": [], "leadership_levels": [], "saved_jobs": [],
                    "saved_searches": [], "sub_teams": [], "teams": [],
                    "is_leadership": False, "is_remote_only": False,
                    "sort_by_new": False, "results_per_page": None,
                }
            }
            payload = {
                "__a": "1", "__comet_req": "31",
                "lsd": lsd,
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CareersJobSearchResultsDataQuery",
                "variables": json.dumps(variables),
                "server_timestamps": "true",
                "doc_id": _META_DOC_ID,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.metacareers.com",
                "Referer": page_url,
                "x-fb-lsd": lsd,
                "x-asbd-id": "359341",
                "x-fb-friendly-name": "CareersJobSearchResultsDataQuery",
            }
            try:
                r = requests.post(_META_GQL_URL, data=payload, headers=headers,
                                  cookies=cookies, timeout=15)
                if r.status_code == 200:
                    all_jobs = (r.json().get("data", {})
                                .get("job_search_with_featured_jobs", {})
                                .get("all_jobs", []))
                    jobs = []
                    for job in all_jobs:
                        title = job.get("title", "")
                        if not self.is_data_role(title):
                            continue
                        locations = job.get("locations", [])
                        location = next(
                            (l for l in locations if self.is_canada_job(l)), "Canada"
                        )
                        job_url = f"https://www.metacareers.com/jobs/{job.get('id', '')}/"
                        jobs.append(self.build_job(title=title, location=location, url=job_url))
                    logger.info(f"[Meta] GraphQL: {len(jobs)} Canada data jobs")
                    return jobs
                logger.warning(f"[Meta] GraphQL {r.status_code}")
            except Exception as e:
                logger.debug(f"[Meta] GraphQL error: {e}")

        # Fallback: extract from rendered DOM links
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/job_details/']")
        seen: set = set()
        jobs = []
        for link in links[:60]:
            try:
                url = self.safe_attr(link, "href")
                if not url or url in seen:
                    continue
                seen.add(url)
                title = self.safe_text(link) or self.safe_text(
                    link.find_element(By.XPATH, ".."))
                if not title or not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            except Exception:
                continue
        logger.info(f"[Meta] DOM fallback: {len(jobs)} Canada data jobs")
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
        time.sleep(8)
        # Dismiss cookie banners (Cornerstone/SAP SuccessFactors sites)
        for sel in ["#cookie-accept", "button.cookiemanageracceptall",
                    "button#onetrust-accept-btn-handler",
                    "//button[contains(text(),'Accept All Cookies')]",
                    "//button[contains(text(),'Accept Cookies')]"]:
            try:
                btn = (driver.find_element(By.XPATH, sel) if sel.startswith("//")
                       else driver.find_element(By.CSS_SELECTOR, sel))
                if btn.is_displayed():
                    btn.click()
                    time.sleep(3)
                    break
            except Exception:
                continue
        time.sleep(3)
        try:
            self.slow_scroll(driver)
        except Exception:
            pass
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


# ── EY CANADA (careers.ey.com — SuccessFactors, link selector works) ──
class EYScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/ey/job/']")
        seen, jobs = set(), []
        for link in links[:60]:
            try:
                url   = self.safe_attr(link, "href")
                title = self.safe_text(link)
                if not url or url in seen:
                    continue
                seen.add(url)
                if not title:
                    slug = url.split("/ey/job/")[-1].strip("/").split("/")[0]
                    title = slug.replace("-", " ").title()
                if not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            except Exception:
                continue
        logger.info(f"[EY Canada] {len(jobs)} data jobs")
        return jobs


# ── LULULEMON CANADA (iCIMS careers site) ──
class LululemonScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/JobDetail/']")
        seen, jobs = set(), []
        for link in links[:60]:
            try:
                url   = self.safe_attr(link, "href")
                title = self.safe_text(link)
                if not url or not title or url in seen:
                    continue
                seen.add(url)
                if not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            except Exception:
                continue
        logger.info(f"[Lululemon Canada] {len(jobs)} data jobs")
        return jobs


# ── CGI GROUP (Njoyn ATS at cgi.njoyn.com) ──
_CGI_NJOYN = "https://cgi.njoyn.com/CORP/xweb/xweb.asp?NTNK=c&clid=21001&Page=joblisting"

class CGIScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_CGI_NJOYN)
        time.sleep(6)

        # Fill keyword search box and submit
        try:
            box = driver.find_element(By.CSS_SELECTOR,
                "input[name='q'], input[name='keyword'], input[id*='keyword'], input[type='text']")
            box.clear()
            box.send_keys("data engineer")
            btn = driver.find_element(By.CSS_SELECTOR,
                "input[type='submit'], button[type='submit'], input[value='Search']")
            btn.click()
            time.sleep(6)
        except Exception:
            pass

        self.slow_scroll(driver)
        time.sleep(2)

        # Njoyn job links — job detail pages
        links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='Page=jobdetails'], a[href*='njoyn.com'][href*='job'], "
            ".joblisting a, table a[href*='xweb.asp']")
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='njoyn.com']")

        seen, jobs = set(), []
        for link in links[:100]:
            try:
                url = self.safe_attr(link, "href")
                if not url or url in seen:
                    continue
                seen.add(url)

                title = ""
                location = ""
                # Njoyn: <a>(code) is inside <td> inside <tr>
                # ../.. goes to <tr>; getting TDs from there gives just this row's cells
                try:
                    tr = link.find_element(By.XPATH, "../..")
                    tds = tr.find_elements(By.TAG_NAME, "td")
                    # Njoyn columns: [job_code] [title] [department] [location] [country]
                    for td in tds[1:]:
                        t = self.safe_text(td).strip()
                        if t and not re.match(r'^J\d{4}-\d{4}', t):
                            title = t
                            break
                    # Extract location (col 3) and country (col 4) if present
                    if len(tds) >= 5:
                        location = self.safe_text(tds[3]) + " " + self.safe_text(tds[4])
                    elif len(tds) >= 4:
                        location = self.safe_text(tds[3])
                except Exception:
                    pass

                # Fallback: strip job code prefix from row text
                if not title:
                    row = self.safe_text(link)
                    for tr_xpath in ["../../..", "../..", ".."]:
                        try:
                            row = self.safe_text(link.find_element(By.XPATH, tr_xpath))
                            if row:
                                break
                        except Exception:
                            continue
                    title = re.sub(r'^J\d{4}-\d{4}\s*', '', row).strip()

                if not title or not self.is_data_role(title):
                    continue
                # Use extracted location; fall back to "Canada" only if empty
                job_location = location.strip() if location.strip() else "Canada"
                if not self.is_canada_job(job_location) and job_location != "Canada":
                    continue
                jobs.append(self.build_job(title=title, location=job_location, url=url))
            except Exception:
                continue
        logger.info(f"[CGI Group] {len(jobs)} data jobs")
        return jobs


# ── McKINSEY CANADA (mckinsey.com custom careers) ──
class McKinseyScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(10)
        self.slow_scroll(driver)
        time.sleep(3)
        links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/careers/'][href*='job'], a[href*='mckinsey.com/careers'], "
            "[class*='job'] a, [class*='result'] a")
        seen, jobs = set(), []
        for link in links[:60]:
            try:
                url   = self.safe_attr(link, "href")
                title = self.safe_text(link)
                if not url or not title or url in seen:
                    continue
                seen.add(url)
                if not self.is_data_role(title):
                    continue
                jobs.append(self.build_job(title=title, location="Canada", url=url))
            except Exception:
                continue
        logger.info(f"[McKinsey Canada] {len(jobs)} data jobs")
        return jobs


# ── CITIBANK CANADA (TalentBrew — jobs.citi.com) ──
class CitibankScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(self.careers_url)
        time.sleep(6)
        # Dismiss cookie consent popup
        for sel in ["button[data-ph-id*='cookie'] ", "button.onetrust-accept-btn-handler",
                    "//button[contains(text(),'Accept Cookies')]",
                    "//button[contains(text(),'Reject Cookies')]"]:
            try:
                if sel.startswith("//"):
                    btn = driver.find_element(By.XPATH, sel)
                else:
                    btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(2)
                    break
            except Exception:
                continue
        time.sleep(4)
        try:
            self.slow_scroll(driver)
        except Exception:
            pass
        time.sleep(2)
        links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/job/'], a[href*='jobs.citi.com/job'], "
            "[class*='job-title'] a, [class*='jobTitle'] a, h2 a, h3 a")
        seen, jobs = set(), []
        for link in links[:60]:
            try:
                url   = self.safe_attr(link, "href")
                title = self.safe_text(link)
                if not url or not title or url in seen:
                    continue
                seen.add(url)
                if not self.is_data_role(title):
                    continue
                location = ""
                try:
                    parent = link.find_element(By.XPATH, "../..")
                    location = self.safe_text(parent.find_element(By.CSS_SELECTOR,
                        "[class*='location'], [class*='Location'], span:nth-child(2)"))
                except Exception:
                    pass
                if location and not self.is_canada_job(location):
                    continue
                jobs.append(self.build_job(title=title, location=location or "Canada", url=url))
            except Exception:
                continue
        logger.info(f"[Citibank Canada] {len(jobs)} data jobs")
        return jobs


# ── SCOTIABANK (j2w — direct search URL, locationsearch param works) ──
class ScotiabankScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get("https://jobs.scotiabank.com/search/?q=data+engineer&locationsearch=Canada")
        time.sleep(7)

        # Dismiss cookie consent popup if present
        for sel in ["button#onetrust-accept-btn-handler", "button.accept-btn",
                    "button[aria-label*='Accept']"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(2)
                    break
            except Exception:
                continue

        self.slow_scroll(driver)
        time.sleep(3)

        # Extract job links — Scotiabank j2w uses /job/<slug>/<id>/ pattern
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
        if not links:
            logger.warning("[Scotiabank] no job links found")
            return []

        logger.info(f"[Scotiabank] {len(links)} raw links found")
        seen_urls: set = set()
        jobs = []
        for link in links[:80]:
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

        logger.info(f"[Scotiabank] {len(jobs)} data jobs")
        return jobs


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


# ── DAYFORCE HCM ─────────────────────────────────────────────────
# Used by: Questrade (qfg), LifeLabs (lifelabs)
_DAYFORCE_SELS = [
    ".job-list-item a",
    "[class*='job-title'] a",
    "[class*='JobTitle'] a",
    "h2 a, h3 a",
    "a[href*='/jobs/']",
]

class DayforceHCMScraper(BaseScraper):
    def __init__(self, company, slug):
        super().__init__(company)
        self._url = f"https://jobs.dayforcehcm.com/en-US/{slug}/CANDIDATEPORTAL/jobs"

    def scrape(self, driver) -> list:
        driver.get(self._url)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _DAYFORCE_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                logger.info(f"[Dayforce/{self.company_name}] {len(links)} links: {sel}")
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/']")
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
        logger.info(f"[Dayforce/{self.company_name}] {len(jobs)} jobs")
        return jobs


# ── BAMBOOHR ─────────────────────────────────────────────────────
class BambooHRScraper(BaseScraper):
    """BambooHR public job board API."""
    def __init__(self, company, slug):
        super().__init__(company)
        self._slug = slug

    def scrape(self, driver) -> list:
        try:
            r = requests.get(
                f"https://{self._slug}.bamboohr.com/careers/list",
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                timeout=15,
            )
            if r.status_code != 200:
                logger.warning(f"[BambooHR/{self.company_name}] {r.status_code}")
                return []
            all_jobs = r.json().get("result", [])
        except Exception as e:
            logger.error(f"[BambooHR/{self.company_name}] error: {e}")
            return []

        _CA_PROVINCES = {
            "british columbia", "ontario", "quebec", "alberta", "manitoba",
            "saskatchewan", "nova scotia", "new brunswick", "prince edward island",
            "newfoundland", "northwest territories", "nunavut", "yukon",
            "bc", "on", "qc", "ab", "mb", "sk", "ns", "nb", "pe", "nl",
        }
        jobs = []
        for item in all_jobs:
            title = item.get("jobOpeningName") or item.get("title") or ""
            if isinstance(title, dict):
                title = title.get("label", "")
            if not self.is_data_role(title):
                continue
            loc = item.get("location") or {}
            city = (loc.get("city") or "").strip() if isinstance(loc, dict) else ""
            state = (loc.get("state") or "").strip() if isinstance(loc, dict) else ""
            country = (loc.get("country") or "").strip() if isinstance(loc, dict) else ""
            is_canada = (
                "canada" in country.lower() or
                state.lower() in _CA_PROVINCES or
                city.lower() in {"toronto", "vancouver", "montreal", "calgary",
                                  "edmonton", "ottawa", "saskatoon", "winnipeg"}
            )
            if not is_canada:
                continue
            location = f"{city}, {state}, Canada" if city and state else (city or state or "Canada")
            job_id = item.get("id", "")
            url = f"https://{self._slug}.bamboohr.com/careers/{job_id}"
            jobs.append(self.build_job(title=title, location=location, url=url))
        logger.info(f"[BambooHR/{self.company_name}] {len(jobs)} Canada data jobs")
        return jobs


# ── iA FINANCIAL ─────────────────────────────────────────────────
_IA_URL = "https://ia.ca/en/carrieres"
_IA_SELS = [
    "a[href*='/carrieres/job/']",
    "a[href*='/careers/job/']",
    "[class*='job'] a",
    "[class*='posting'] a",
]

class IAFinancialScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_IA_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _IA_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
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
        logger.info(f"[iA Financial] {len(jobs)} jobs")
        return jobs


# ── PAYPAL CANADA ─────────────────────────────────────────────────
_PAYPAL_URL = "https://paypal.eightfold.ai/careers?query=data+engineer&location=Canada"
_PAYPAL_SELS = [
    "[data-ph-id] a",
    "[class*='job-card'] a",
    "[class*='position'] a",
    "a[href*='/careers/job/']",
    "li[class*='job'] a",
]

class PayPalScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_PAYPAL_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _PAYPAL_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='eightfold.ai']")
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
        logger.info(f"[PayPal] {len(jobs)} jobs")
        return jobs


# ── ORACLE CANADA ─────────────────────────────────────────────────
_ORACLE_URL = "https://careers.oracle.com/en/sites/jobsearch/requisitions?keyword=data+engineer&location=Canada&locationId=300000000149325&locationLevel=country"
_ORACLE_SELS = [
    "[class*='job-title'] a",
    "li[class*='job'] a",
    "a[href*='/job/']",
    "[class*='requisition'] a",
]

class OracleScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_ORACLE_URL)
        time.sleep(8)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _ORACLE_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='careers.oracle.com']")
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
        logger.info(f"[Oracle] {len(jobs)} jobs")
        return jobs


# ── WELL HEALTH ───────────────────────────────────────────────────
_WELL_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    "?cid=812e2e6b-3e13-494b-9abe-72b6ef39cd69&ccId=19000101_000001&lang=en_CA"
)
_WELL_SELS = [
    ".job-posting a",
    "[class*='jobTitle'] a",
    "[class*='job-title'] a",
    "a[class*='jobtitle']",
    ".jobDetails a",
    "a[href*='jobId']",
]

class WELLHealthScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_WELL_URL)
        time.sleep(10)
        self.slow_scroll(driver)
        time.sleep(3)
        links = []
        for sel in _WELL_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='jobId'], a[href*='recruitment']")
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
            jobs.append(self.build_job(title=title, location="Vancouver", url=url))
        logger.info(f"[WELL Health] {len(jobs)} jobs")
        return jobs


# ── STANTEC ───────────────────────────────────────────────────────
_STANTEC_URL = "https://stantec.jobs/search/?q=data+engineer&locationsearch=Canada"
_STANTEC_SELS = [
    ".job-title a",
    "a[href*='/job/']",
    "[class*='job-listing'] a",
    "h2 a",
]

class StantecScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_STANTEC_URL)
        time.sleep(6)
        self.slow_scroll(driver)
        time.sleep(2)
        links = []
        for sel in _STANTEC_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='stantec.jobs']")
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
        logger.info(f"[Stantec] {len(jobs)} jobs")
        return jobs


# ── PFIZER CANADA ─────────────────────────────────────────────────
_PFIZER_URL = "https://www.pfizer.ca/en/careers?field_job_categories_tid=All&field_job_locations_tid=Canada&search_api_fulltext=data+engineer"
_PFIZER_SELS = [
    "a[href*='/careers/job']",
    ".job-title a",
    "[class*='job'] a",
    "h3 a",
    "h2 a",
]

class PfizerScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_PFIZER_URL)
        time.sleep(6)
        self.slow_scroll(driver)
        time.sleep(2)
        links = []
        for sel in _PFIZER_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
        if not links:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='pfizer']")
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
        logger.info(f"[Pfizer] {len(jobs)} jobs")
        return jobs


# ── KLICK HEALTH ──────────────────────────────────────────────────
_KLICK_URL = "https://careers.klick.com/"
_KLICK_SELS = [
    "a[href*='/roles/']",
    "[class*='job'] a",
    "[class*='role'] a",
    "[class*='posting'] a",
]

class KlickScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_KLICK_URL)
        time.sleep(6)
        self.slow_scroll(driver)
        time.sleep(2)
        links = []
        for sel in _KLICK_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 1:
                links = found
                break
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
            jobs.append(self.build_job(title=title, location="Toronto", url=url))
        logger.info(f"[Klick] {len(jobs)} jobs")
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
        try:
            driver.set_page_load_timeout(25)
            driver.get(_TCS_URL)
        except Exception as e:
            logger.warning(f"[TCS] Page load timeout/error: {e}")
            return []
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


# ── iCIMS (generic Selenium) ──────────────────────────────────────
_ICIMS_SELS = [
    ".iCIMS_JobListingRow .iCIMS_Anchor",
    ".iCIMS_Anchor",
    "a.iCIMS_Anchor",
    ".iCIMS_JobTitleText a",
    "table.iCIMS_JobsTable a",
    # iCIMS JDX (modern SPA — careers.kpmg.ca style)
    "a[data-details-url]",
    "[class*='job-title'] a",
    "[class*='jobTitle'] a",
    "h2 a[href*='/jobs/']",
    "a[href*='/jobs/'][aria-label]",
]

class ICIMSScraper(BaseScraper):
    """Generic iCIMS Selenium scraper. Pass search URL and default location."""
    def __init__(self, company, search_url, default_location="Canada"):
        super().__init__(company)
        self._search_url = search_url
        self._default_location = default_location

    def scrape(self, driver) -> list:
        driver.get(self._search_url)
        time.sleep(10)  # Angular SPA needs extra time to render job listings
        try:
            self.slow_scroll(driver)
            time.sleep(3)
        except Exception:
            pass
        links = []
        for sel in _ICIMS_SELS:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                links = found
                logger.info(f"[iCIMS/{self.company_name}] {len(links)} links: {sel}")
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
            if title.lower() in ("apply now", "apply", "view job", "learn more"):
                continue
            seen.add(url)
            if not self.is_data_role(title):
                continue
            jobs.append(self.build_job(title=title, location=self._default_location, url=url))
        logger.info(f"[iCIMS/{self.company_name}] {len(jobs)} jobs")
        return jobs


class KinaxisScraper(ICIMSScraper):
    def __init__(self, company):
        super().__init__(
            company,
            "https://careers-kinaxis.icims.com/jobs/search?ss=1&searchKeyword=data+engineer&searchLocation=Canada",
            "Ottawa",
        )


# ── INFOSYS ──────────────────────────────────────────────────────
_INFOSYS_URL = (
    "https://digitalcareers.infosys.com/global-careers/search-jobs"
    "?searchText=data+engineer&location=Canada"
)

class InfosysScraper(BaseScraper):
    def scrape(self, driver) -> list:
        driver.get(_INFOSYS_URL)
        time.sleep(8)
        # Detect Akamai/bot block — page redirects to infosys.com/404
        if "infosys.com/404" in driver.current_url or "Access Denied" in driver.page_source[:500]:
            logger.warning("[Infosys] Bot protection detected — skipping")
            return []
        self.slow_scroll(driver)
        time.sleep(3)
        links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/company-job/'], a[href*='/reqid/'], .job-title a, .jobTitle a, h3 a, h2 a")
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
        logger.info(f"[Infosys] {len(jobs)} jobs")
        return jobs


# ── GENERIC FALLBACK ────────────────────────────────────────────
class CanadaLifeScraper(BaseScraper):
    """Taleo-based board at jobs.canadalife.com."""

    _SEARCH = "https://jobs.canadalife.com/search?q=data+engineer"

    def scrape(self, driver) -> list:
        import re as _re
        import requests as _req
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        try:
            r = _req.get(self._SEARCH, headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"[{self.company_name}] CanadaLife HTTP {r.status_code}")
                return []
        except Exception as e:
            logger.error(f"[{self.company_name}] CanadaLife error: {e}")
            return []

        html = r.text
        jobs = []
        # Each job appears twice (desktop + mobile) — deduplicate by URL
        seen = set()
        # Pattern: <a href="/job/..." class="jobTitle-link">Title</a>
        for m in _re.finditer(
            r'<a href="(/job/[^"]+)" class="jobTitle-link">([^<]+)</a>',
            html,
        ):
            url_path = m.group(1)
            if url_path in seen:
                continue
            seen.add(url_path)
            title = m.group(2).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()
            if not self.is_data_role(title):
                continue
            # Location: <span class="jobLocation">City, ON, CA</span>
            window = html[m.end():m.end() + 2000]
            lm = _re.search(r'<span class="jobLocation">\s*([^<]+?)\s*</span>', window)
            location = lm.group(1).strip() if lm else "Canada"
            location = _re.sub(r',\s*CA\s*$', ', Canada', location)
            if not self.is_canada_job(location):
                continue
            jobs.append(self.build_job(
                title=title,
                location=location,
                url="https://jobs.canadalife.com" + url_path,
                skills=[],
                posted="Recent",
            ))
        logger.info(f"[{self.company_name}] {len(jobs)} jobs")
        return jobs


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
        # Consulting firms — custom Selenium scrapers
        "EY Canada":                  EYScraper,
        "Lululemon Canada":           LululemonScraper,
        "CGI Group":                  CGIScraper,
        "McKinsey Canada":            McKinseyScraper,
        "Citibank Canada":            CitibankScraper,
        # j2w (SAP SuccessFactors) Selenium scrapers
        "Deloitte Canada":            J2WScraper,
        "SAP Canada":                 J2WScraper,
        "TELUS Health":               J2WScraper,
        "Scotiabank Digital Factory": J2WScraper,
        # j2w RSS scraper
        "Bank of Canada":             BankOfCanadaScraper,
        # Custom Selenium scrapers
        "Atlassian Canada":            AtlassianScraper,
        # Dayforce HCM companies
        "Questrade":                   lambda c: DayforceHCMScraper(c, "qfg"),
        "LifeLabs":                    lambda c: DayforceHCMScraper(c, "lifelabs"),
        "MindBridge AI":               lambda c: DayforceHCMScraper(c, "mindbridge"),
        "Vendasta":                    lambda c: BambooHRScraper(c, "vendasta"),
        # Custom Selenium
        "iA Financial Group":          IAFinancialScraper,
        "PayPal Canada":               PayPalScraper,
        "WELL Health Technologies":    WELLHealthScraper,
        "Stantec":                     StantecScraper,
        "Pfizer Canada":               PfizerScraper,
        "Klick Health":                KlickScraper,
        # j2w
        "HCL Technologies Canada":     J2WScraper,
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
        # j2w (SAP SuccessFactors)
        "City of Toronto":            J2WScraper,
        "Infosys Canada":             InfosysScraper,
        "Great-West Lifeco":          CanadaLifeScraper,
        # iCIMS
        "KPMG Canada":                lambda c: ICIMSScraper(
            c,
            "https://careers.kpmg.ca/jobs?keyword=data+engineer&location=Canada",
            "Canada",
        ),
        "Mackenzie Investments":      lambda c: ICIMSScraper(
            c,
            "https://careersen-mackenzieinvestments.icims.com/jobs/search?ss=1&searchKeyword=data+engineer&searchLocation=Canada",
            "Toronto",
        ),
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