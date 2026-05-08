import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Oracle Fusion HCM tenants: {company_name: (domain, site_number)}
ORACLE_HCM_TENANTS = {
    "JP Morgan Canada":       ("jpmc.fa.oraclecloud.com", "CX_1001"),
    "American Express Canada": ("egug.fa.us2.oraclecloud.com", "CX_1"),
}

_API = "https://{domain}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

# Oracle HCM paginates at 25 per page max; scan up to 50 pages (1250 jobs)
MAX_PAGES = 50


class OracleHCMScraper(BaseScraper):

    def scrape(self, driver) -> list:
        config = ORACLE_HCM_TENANTS.get(self.company_name)
        if not config:
            logger.warning(f"[{self.company_name}] No Oracle HCM config found")
            return []

        domain, site_number = config
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        jobs = []
        offset = 0
        limit = 25

        for page in range(MAX_PAGES):
            try:
                r = requests.get(
                    _API.format(domain=domain),
                    params={
                        "onlyData": "true",
                        "finder": f"findReqs;siteNumber={site_number}",
                        "limit": limit,
                        "offset": offset,
                        "expand": "requisitionList",
                    },
                    headers=headers,
                    timeout=15,
                )
                if r.status_code != 200:
                    logger.warning(f"[{self.company_name}] Oracle HCM {r.status_code} at offset {offset}")
                    break

                data = r.json()
                item = data.get("items", [{}])[0]

                if page == 0:
                    total = item.get("TotalJobsCount", 0)
                    logger.info(f"[{self.company_name}] Oracle HCM: {total} total jobs")

                req_list = item.get("requisitionList", [])
                if not req_list:
                    break

                for job in req_list:
                    country = job.get("PrimaryLocationCountry", "")
                    if country != "CA":
                        continue

                    title = job.get("Title", "")
                    if not self.is_data_role(title):
                        continue

                    location = job.get("PrimaryLocation", "Canada")
                    job_id = job.get("Id", "")
                    url = (
                        f"https://{domain}/hcmUI/CandidateExperience/en/sites"
                        f"/{site_number}/requisitions/{job_id}"
                        if job_id else self.careers_url
                    )
                    posted = job.get("PostedDate", "Recent") or "Recent"

                    jobs.append(self.build_job(
                        title=title,
                        location=location,
                        url=url,
                        posted=posted,
                    ))

                offset += limit

            except Exception as e:
                logger.error(f"[{self.company_name}] Oracle HCM error at offset {offset}: {e}")
                break

        logger.info(f"[{self.company_name}] Oracle HCM: {len(jobs)} Canada data jobs")
        return jobs
