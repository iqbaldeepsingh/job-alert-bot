import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

GREENHOUSE_SLUGS = {
    "Shopify":             "shopify",
    "Shopify (Platform)":  "shopify",
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

        # Try different slug variations
        slugs_to_try = [slug, slug.replace("-", ""), slug + "inc", slug + "hq"]

        all_jobs = []
        for s in slugs_to_try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true"
            try:
                resp = requests.get(url, timeout=15,
                                    headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    all_jobs = resp.json().get("jobs", [])
                    logger.info(f"[{self.company_name}] {len(all_jobs)} jobs with slug: {s}")
                    break
                else:
                    logger.debug(f"[{self.company_name}] Slug '{s}' returned {resp.status_code}")
            except Exception as e:
                logger.error(f"[{self.company_name}] Error: {e}")
                continue

        if not all_jobs:
            logger.warning(f"[{self.company_name}] No jobs found with any slug")
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
