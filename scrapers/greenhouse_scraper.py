import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

GREENHOUSE_SLUGS = {
    "Shopify":             "shopify",
    "Databricks Canada":   "databricks",
    "Confluent Canada":    "confluent",
    "Airbnb Canada":       "airbnb",
    "Datadog Canada":      "datadog",
    "Coveo":               "coveo",
    "Lightspeed Commerce": "lightspeed",
    "Clio":                "cliolegalsoftware",
    "Kinaxis":             "kinaxis",
    "PointClickCare":      "pointclickcare",
    "dbt Labs Canada":     "dbtlabsinc",
    "Fivetran Canada":     "fivetran",
    "Geotab":              "geotab",
    "Borealis AI (RBC)":   "borealisai",
    "OpenAI Canada":       "openai",
    "Cohere AI":           "cohere",
    "Palantir Canada":     "palantir",
    "Wayfair Canada":      "wayfair",
    "Shopify (Platform)":  "shopify",
}

KNOWN_SKILLS = [
    "Python", "PySpark", "Spark", "SQL", "dbt", "Airflow",
    "Databricks", "Snowflake", "Azure", "AWS", "GCP", "Kafka",
    "Delta Lake", "BigQuery", "Terraform", "Docker", "Trino",
    "Flink", "Hudi", "MLflow", "Unity Catalog", "ADF",
]

class GreenhouseScraper(BaseScraper):

    def scrape(self, driver) -> list:
        slug = GREENHOUSE_SLUGS.get(self.company_name)
        if not slug:
            logger.warning(f"[{self.company_name}] No slug found")
            return []

        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"

        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                logger.warning(f"[{self.company_name}] API {resp.status_code}")
                return []
            all_jobs = resp.json().get("jobs", [])
            logger.info(f"[{self.company_name}] {len(all_jobs)} jobs from API")
        except Exception as e:
            logger.error(f"[{self.company_name}] Error: {e}")
            return []

        jobs = []
        for job in all_jobs:
            title = job.get("title", "")
            if not self.is_data_role(title):
                continue
            loc_obj = job.get("location", {})
            location = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)
            if not self.is_canada_job(location):
                continue
            apply_url = job.get("absolute_url", "")
            content = job.get("content", "")
            skills = [s for s in KNOWN_SKILLS if s.lower() in content.lower()][:6]
            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                skills=skills,
                posted="Recent",
            ))
        return jobs
