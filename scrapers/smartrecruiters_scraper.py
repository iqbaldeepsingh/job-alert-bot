import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# SmartRecruiters company slugs — exact slug from their API
SMARTRECRUITERS_SLUGS = {
    "Visa Canada":            "Visa",
    "ServiceNow Canada":      "ServiceNow",
    "KPMG Canada":            "KPMG",
    "EY Canada":              "EY",
    "Lululemon Canada":       "lululemon",
    "Electronic Arts Canada": "ElectronicArts",
    "Zynga Canada":           "Zynga",
    # New companies on SmartRecruiters
    "Ubisoft Canada":         "Ubisoft",
    "Randstad Canada":        "Randstad",
    "CGI Group":              "CGI",
}

_API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
_PARAMS = {"q": "data engineer", "limit": 100, "offset": 0}


class SmartRecruitersScraper(BaseScraper):

    def scrape(self, driver) -> list:
        slug = SMARTRECRUITERS_SLUGS.get(self.company_name)
        if not slug:
            logger.warning(f"[{self.company_name}] No SmartRecruiters slug found")
            return []

        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        all_postings = []
        offset = 0
        limit = 100

        while True:
            params = {"q": "data engineer", "limit": limit, "offset": offset}
            try:
                r = requests.get(
                    _API.format(slug=slug),
                    headers=headers,
                    params=params,
                    timeout=15,
                )
                if r.status_code != 200:
                    logger.warning(f"[{self.company_name}] SmartRecruiters {r.status_code}")
                    break
                data = r.json()
                postings = data.get("content", [])
                if not postings:
                    break
                all_postings.extend(postings)
                total = data.get("totalFound", 0)
                offset += limit
                if offset >= total:
                    break
            except Exception as e:
                logger.error(f"[{self.company_name}] SmartRecruiters error: {e}")
                break

        if not all_postings:
            logger.info(f"[{self.company_name}] SmartRecruiters: 0 jobs")
            return []

        jobs = []
        for posting in all_postings:
            title = posting.get("name", "")
            if not self.is_data_role(title):
                continue

            loc = posting.get("location", {})
            # fullLocation is e.g. "Toronto, Ontario, Canada" — use it for Canada check
            full_location = loc.get("fullLocation", "")
            country_code = loc.get("country", "").lower()
            city = loc.get("city", "")

            # SmartRecruiters uses "ca" (lowercase) for Canada country code
            if country_code == "ca":
                location = full_location or (f"{city}, Canada" if city else "Canada")
            elif full_location and self.is_canada_job(full_location):
                location = full_location
            else:
                continue

            job_id = posting.get("id", "")
            apply_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}" if job_id else ""

            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                posted="Recent",
            ))

        logger.info(f"[{self.company_name}] SmartRecruiters: {len(jobs)} Canada data jobs")
        return jobs
