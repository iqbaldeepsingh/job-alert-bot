import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

ASHBY_SLUGS = {
    "Cohere AI":            "cohere",
    "OpenAI Canada":        "openai",
    "Confluent Canada":     "confluent",
    "Lightspeed Commerce":  "lightspeedhq",
    "Koho":                 "koho",
    "Neo Financial":        "neofinancial",
    "Trulioo":              "trulioo",
    "Airbyte Canada":       "airbyte",
    "Astronomer Canada":    "astronomer",
    "Prefect":              "prefect",
    "Jobber":               "getjobber",
    "Top Hat":              "tophat",
    "Prodigy Education":    "prodigy-education",
    "Clearco":              "clearco",
}

_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

_CANADA_CITIES = {
    "toronto", "vancouver", "montreal", "calgary", "edmonton", "ottawa",
    "waterloo", "mississauga", "brampton", "quebec", "winnipeg", "burnaby",
    "kitchener", "oakville", "stellarton", "saskatoon",
}


def _is_canada_location(loc_str: str, addr: dict) -> bool:
    postal = (addr or {}).get("postalAddress") or {}
    if postal.get("addressCountry") == "Canada":
        return True
    s = (loc_str or "").lower()
    return s == "canada" or any(c in s for c in _CANADA_CITIES)


def _canada_location_str(job: dict) -> str:
    """Return the best Canada location string for a job, or '' if not Canada."""
    loc = job.get("location") or ""
    addr = job.get("address") or {}

    # Primary location is Canada
    if _is_canada_location(loc, addr):
        postal = (addr.get("postalAddress") or {})
        city = postal.get("addressLocality") or loc
        region = postal.get("addressRegion", "")
        if city and region:
            return f"{city}, {region}, Canada"
        return f"{city}, Canada" if city else "Canada"

    # Check secondary locations for Canada
    for sec in (job.get("secondaryLocations") or []):
        sec_loc = sec.get("location") or ""
        sec_addr = sec.get("address") or {}
        if _is_canada_location(sec_loc, sec_addr):
            postal = (sec_addr.get("postalAddress") or {})
            city = postal.get("addressLocality") or sec_loc
            region = postal.get("addressRegion", "")
            if city and city.lower() not in ("canada",):
                return f"{city}, {region}, Canada".strip(", ") if region else f"{city}, Canada"
            return "Canada"

    return ""


class AshbyScraper(BaseScraper):

    def scrape(self, driver) -> list:
        slug = ASHBY_SLUGS.get(self.company_name)
        if not slug:
            logger.warning(f"[{self.company_name}] No Ashby slug found")
            return []

        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        try:
            r = requests.get(_API.format(slug=slug), headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"[{self.company_name}] Ashby {r.status_code}")
                return []
            all_jobs = r.json().get("jobs", [])
        except Exception as e:
            logger.error(f"[{self.company_name}] Ashby error: {e}")
            return []

        jobs = []
        for job in all_jobs:
            title = job.get("title", "")
            if not self.is_data_role(title):
                continue

            location = _canada_location_str(job)
            if not location:
                continue

            apply_url = job.get("jobUrl") or job.get("applyUrl") or ""
            skills = self.extract_skills(job.get("descriptionPlain") or job.get("descriptionHtml") or "")

            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                skills=skills,
                posted="Recent",
            ))

        logger.info(f"[{self.company_name}] Ashby: {len(jobs)} Canada data jobs")
        return jobs
