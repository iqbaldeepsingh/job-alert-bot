import re
import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_CAREERS_URL = "https://www.shopify.com/careers"
_UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
_DATE = r'\d{4}-\d{2}-\d{2}'

# RSC data pattern: "uuid","title","uuid2","date","https://www.shopify.com/careers?ashby_jid=uuid
_JOB_PATTERN = re.compile(
    r'\\"(' + _UUID + r')\\"'
    r',\\"([^\\"]{5,150})\\"'
    r',\\"' + _UUID + r'\\"'
    r',\\"' + _DATE + r'\\"'
    r',\\"https://www\.shopify\.com/careers\?ashby_jid='
)

# Shopify workplace type appears near the job data
_REMOTE_SIGNAL = re.compile(r'workplaceType[\\"\s,:]+Remote', re.IGNORECASE)


class ShopifyScraper(BaseScraper):

    def scrape(self, driver) -> list:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        try:
            r = requests.get(_CAREERS_URL, headers=headers, timeout=20)
            if r.status_code != 200:
                logger.warning(f"[Shopify] HTTP {r.status_code}")
                return []
            html = r.text
        except Exception as e:
            logger.error(f"[Shopify] Error: {e}")
            return []

        raw_jobs = _JOB_PATTERN.findall(html)
        seen = set()
        jobs = []

        for uuid, title in raw_jobs:
            if uuid in seen:
                continue
            seen.add(uuid)

            if not self.is_data_role(title):
                continue

            # Shopify is remote-first from Canada (Ottawa, Toronto, Remote)
            location = "Remote Canada"

            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            apply_url = f"{_CAREERS_URL}/{slug}_{uuid}"

            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                posted="Recent",
            ))

        logger.info(f"[Shopify] {len(jobs)} Canada data jobs")
        return jobs
