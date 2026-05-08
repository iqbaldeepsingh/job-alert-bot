import logging
import requests
import xml.etree.ElementTree as ET
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Avature RSS feed: /careers/SearchJobs/{query}/{location}/feed/?jobRecordsPerPage=100
AVATURE_SLUGS = {
    "Bloomberg Canada": "bloomberg.avature.net",
}

_FEED = "https://{host}/careers/SearchJobs/data%20engineer/Canada/feed/?jobRecordsPerPage=100"


class AvatureScraper(BaseScraper):

    def scrape(self, driver) -> list:
        host = AVATURE_SLUGS.get(self.company_name)
        if not host:
            logger.warning(f"[{self.company_name}] No Avature host found")
            return []

        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        try:
            r = requests.get(_FEED.format(host=host), headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"[{self.company_name}] Avature feed {r.status_code}")
                return []
        except Exception as e:
            logger.error(f"[{self.company_name}] Avature error: {e}")
            return []

        try:
            root = ET.fromstring(r.text)
        except ET.ParseError as e:
            logger.error(f"[{self.company_name}] Avature XML parse error: {e}")
            return []

        channel = root.find("channel")
        items = channel.findall("item") if channel else []

        jobs = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            if not title or not self.is_data_role(title):
                continue

            link = (item.findtext("link") or "").strip()
            # Location is not in RSS — infer from title prefix like "[TOR]" or use Canada
            location = "Canada"
            if title.startswith("["):
                bracket = title[1:title.find("]")] if "]" in title else ""
                city_map = {
                    "TOR": "Toronto, Ontario, Canada",
                    "VAN": "Vancouver, BC, Canada",
                    "MTL": "Montreal, Quebec, Canada",
                    "NYC": None, "LON": None, "SGP": None, "HKG": None,
                }
                resolved = city_map.get(bracket.upper())
                if resolved is None:
                    continue  # Non-Canada office
                location = resolved or "Canada"
                # Strip prefix from title
                title = title[title.find("]") + 1:].strip(" -–")

            if not self.is_data_role(title):
                continue

            jobs.append(self.build_job(
                title=title,
                location=location,
                url=link,
                posted="Recent",
            ))

        logger.info(f"[{self.company_name}] Avature: {len(jobs)} Canada data jobs")
        return jobs
