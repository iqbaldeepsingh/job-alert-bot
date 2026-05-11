import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_API_URL = "https://explore.jobs.netflix.net/api/apply/v2/jobs"


class NetflixScraper(BaseScraper):

    def scrape(self, _driver) -> list:
        try:
            all_positions = []
            start = 0
            num = 50
            while True:
                r = requests.get(_API_URL, timeout=15,
                                 headers={"User-Agent": "Mozilla/5.0"},
                                 params={"domain": "netflix.com",
                                         "query": "data engineer",
                                         "sort_by": "relevance",
                                         "num": num,
                                         "start": start})
                if r.status_code != 200:
                    logger.warning(f"[Netflix] API {r.status_code}")
                    return []
                data = r.json()
                page = data.get("positions", [])
                all_positions.extend(page)
                if len(all_positions) >= data.get("count", 0) or not page:
                    break
                start += num
            positions = all_positions
            logger.info(f"[Netflix] {len(positions)} total positions, filtering for Canada")
        except Exception as e:
            logger.error(f"[Netflix] API error: {e}")
            return []

        jobs = []
        for pos in positions:
            title = pos.get("name", "")
            if not self.is_data_role(title):
                continue
            location = pos.get("location", "Canada")
            if not self.is_canada_job(location):
                continue
            url = pos.get("canonicalPositionUrl", "")
            jobs.append(self.build_job(title=title, location=location, url=url))
        return jobs
