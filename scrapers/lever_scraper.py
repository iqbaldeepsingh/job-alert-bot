"""
Lever Scraper
Wealthsimple, Snowflake, Palantir
Lever ਵੀ JSON API ਦਿੰਦਾ ਹੈ — fast ਅਤੇ reliable
"""

import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

LEVER_SLUGS = {
    "Wealthsimple":    "wealthsimple",
    "Snowflake Canada":"snowflake",
    "Palantir Canada": "palantir",
}

KNOWN_SKILLS = [
    "Python", "PySpark", "Spark", "SQL", "dbt", "Airflow",
    "Databricks", "Snowflake", "Azure", "AWS", "GCP", "Kafka",
    "Delta Lake", "BigQuery", "Terraform", "Docker", "Kubernetes",
    "Trino", "Flink", "Iceberg", "MLflow", "Redshift",
]


class LeverScraper(BaseScraper):

    def scrape(self, driver) -> list:
        slug = LEVER_SLUGS.get(self.company_name)
        if not slug:
            logger.warning(f"[{self.company_name}] No Lever slug found")
            return []

        url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=200"

        try:
            resp = requests.get(url, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                logger.warning(f"[{self.company_name}] Lever API {resp.status_code}")
                return []
            all_jobs = resp.json()
            logger.info(f"[{self.company_name}] {len(all_jobs)} total jobs from Lever")
        except Exception as e:
            logger.error(f"[{self.company_name}] Lever API error: {e}")
            return []

        jobs = []
        for job in all_jobs:
            title = job.get("text", "")
            if not self.is_data_role(title):
                continue

            categories = job.get("categories", {})
            location   = categories.get("location", "")

            if not self.is_canada_job(location):
                continue

            apply_url = job.get("hostedUrl", "")
            desc      = (job.get("descriptionPlain", "") + " " +
                         job.get("additionalPlain", ""))
            skills    = self._extract_skills(desc)

            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                skills=skills,
                posted="Recent",
            ))

        return jobs

    def _extract_skills(self, text: str) -> list:
        found = []
        lower = text.lower()
        for skill in KNOWN_SKILLS:
            if skill.lower() in lower:
                found.append(skill)
        return found[:6]