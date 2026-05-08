"""
Base Scraper
ਸਾਰੇ scrapers ਇਸ ਤੋਂ inherit ਕਰਦੇ ਨੇ
Chrome setup, helpers, filters ਇੱਥੇ ਨੇ
"""

import time
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

KNOWN_SKILLS = [
    "Python", "PySpark", "Spark", "SQL", "dbt", "Airflow",
    "Databricks", "Snowflake", "Azure", "AWS", "GCP", "Kafka",
    "Delta Lake", "BigQuery", "Terraform", "Docker", "Kubernetes",
    "Trino", "Flink", "Iceberg", "MLflow", "Redshift", "Hudi",
    "Unity Catalog", "ADF",
]

KNOWN_SKILLS_LOWER = [s.lower() for s in KNOWN_SKILLS]

HTTP_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    prefs = {"profile.managed_default_content_settings.images": 2}
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver


class BaseScraper:

    def __init__(self, company: dict):
        self.company_name = company["name"]
        self.careers_url  = company["careers_url"]
        self.category     = company["category"]
        self.titles       = company.get("titles", [])
        self.stack        = company.get("stack", [])
        self.salary       = company.get("salary_range", "")

    # ── Helpers ─────────────────────────────────────────────────

    def wait_for(self, driver, css: str, timeout: int = 10):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css))
            )
        except TimeoutException:
            return None

    def safe_text(self, el) -> str:
        try:
            return el.text.strip() if el else ""
        except Exception:
            return ""

    def safe_attr(self, el, attr: str) -> str:
        try:
            return el.get_attribute(attr).strip() if el else ""
        except Exception:
            return ""

    def slow_scroll(self, driver, pause: float = 0.5):
        last = driver.execute_script("return document.body.scrollHeight")
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(pause)
            new = driver.execute_script("return document.body.scrollHeight")
            if new == last:
                break
            last = new

    # ── Filters ─────────────────────────────────────────────────

    def is_canada_job(self, location: str) -> bool:
        if not location:
            return False
        loc = location.lower()

        # Must have an explicit Canadian location first
        canada_keywords = [
            "canada", "toronto", "vancouver", "calgary", "edmonton",
            "halifax", "ontario", "british columbia", "alberta",
            "montreal", "ottawa", "waterloo", "mississauga", "brampton",
            "quebec", "winnipeg", "burnaby", "kitchener", "oakville",
            "stellarton", "saskatoon", "st. john", "remote - canada",
            "remote – canada", "remote canada",
        ]
        if not any(k in loc for k in canada_keywords):
            return False

        # Has a Canadian keyword — now reject if it also mentions non-Canada
        non_canada = [
            "remote - us", "remote – us", "remote - us:", "united states",
            ", usa", "(usa)", "california", "new york", "texas",
            "seattle", "san francisco", "chicago", "boston", "austin",
            "germany", "united kingdom", "ireland", "india", "singapore",
            "australia", "netherlands", "france", "remote - eu",
            "bangalore", "bengaluru", "mumbai",
            "kuala lumpur", "malaysia", "putrajaya",
            "poland", "warsaw", "krakow", "czech", "prague",
            "philippines", "manila", "jakarta", "indonesia",
        ]
        if any(kw in loc for kw in non_canada):
            return False

        return True

    def is_data_role(self, title: str) -> bool:
        t = title.lower()
        keywords = [
            "data engineer", "data platform", "analytics engineer",
            "big data", "databricks", "spark", "pyspark", "etl", "elt",
            "data architect", "dataops", "ml engineer", "data scientist",
            "data analyst", "pipeline engineer", "data infrastructure",
            "bi engineer", "bi developer", "business intelligence",
            "data reliability", "cloud data", "data ops",
        ]
        return any(k in t for k in keywords)

    def detect_level(self, title: str) -> str:
        t = title.lower()
        if any(w in t for w in ["staff", "principal", "lead", "director", "architect"]):
            return "Staff / Lead"
        if any(w in t for w in ["senior", " sr.", " sr "]):
            return "Senior"
        if any(w in t for w in ["associate", "junior", "jr.", "entry", "ii", "iii"]):
            return "Entry Level"
        if any(w in t for w in ["mid", "intermediate", "level 2"]):
            return "Mid-Level"
        return "Mid-Level"

    def extract_skills(self, text: str, limit: int = 6) -> list:
        lower = text.lower()
        return [KNOWN_SKILLS[i] for i, s in enumerate(KNOWN_SKILLS_LOWER) if s in lower][:limit]

    def build_job(self, title: str, location: str = "",
                  level: str = "", job_type: str = "Full-time",
                  posted: str = "Recent", url: str = "",
                  skills: list = None) -> dict:
        return {
            "title":    title.strip(),
            "company":  self.company_name,
            "category": self.category,
            "location": location.strip() or "Canada",
            "level":    level or self.detect_level(title),
            "type":     job_type,
            "posted":   posted,
            "url":      url,
            "skills":   skills or self.stack[:5],
            "salary":   self.salary,
        }

    # ── Entry point ─────────────────────────────────────────────

    def run(self, driver) -> list:
        try:
            logger.info(f"[{self.company_name}] Scraping → {self.careers_url}")
            jobs = self.scrape(driver)
            filtered = [
                j for j in jobs
                if self.is_canada_job(j.get("location", ""))
                and self.is_data_role(j.get("title", ""))
            ]
            logger.info(f"[{self.company_name}] ✅ {len(filtered)} jobs found")
            return filtered
        except Exception as e:
            logger.error(f"[{self.company_name}] ❌ Failed: {e}")
            return []

    def scrape(self, driver) -> list:
        raise NotImplementedError