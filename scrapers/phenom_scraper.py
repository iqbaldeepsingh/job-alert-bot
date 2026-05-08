import re
import logging
import requests
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Companies confirmed to use Phenom People ATS
PHENOM_CONFIGS = {
    "BMO Financial Group": {
        "search_url":       "https://jobs.bmo.com/ca/en/search-results?keywords=data+engineer",
        "job_url_template": "https://jobs.bmo.com/ca/en/job/{jobSeqNo}/{slug}",
    },
    "RBC": {
        "search_url":       "https://jobs.rbc.com/ca/en/search-results?keywords=data+engineer",
        "job_url_template": "https://jobs.rbc.com/ca/en/job/{jobSeqNo}/{slug}",
    },
    "Manulife": {
        "search_url":       "https://careers.manulife.com/global/en/search-results?keywords=data+engineer",
        "job_url_template": "https://careers.manulife.com/global/en/job/{jobSeqNo}/{slug}",
    },
    "Air Canada": {
        "search_url":       "https://careers.aircanada.com/ca/en/search-results?keywords=data+engineer",
        "job_url_template": "https://careers.aircanada.com/ca/en/job/{jobSeqNo}/{slug}",
    },
    "Bell Canada": {
        "search_url":       "https://jobs.bell.ca/ca/en/search-results?keywords=data+engineer",
        "job_url_template": "https://jobs.bell.ca/ca/en/job/{jobSeqNo}/{slug}",
    },
    "Restaurant Brands International": {
        "search_url":       "https://careers.rbi.com/global/en/search-results?keywords=data+engineer",
        "job_url_template": "https://careers.rbi.com/global/en/job/{jobSeqNo}/{slug}",
    },
    "Splunk Canada": {
        "search_url":       "https://careers.cisco.com/global/en/search-results?keywords=data+engineer",
        "job_url_template": "https://careers.cisco.com/global/en/job/{jobSeqNo}/{slug}",
    },
    "HSBC Canada": {
        "search_url":       "https://mycareer.hsbc.com/en_GB/external/search-results?keywords=data+engineer",
        "job_url_template": "https://mycareer.hsbc.com/en_GB/external/job/{jobSeqNo}/{slug}",
    },
}


def _field(text: str, key: str) -> str:
    m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', text)
    return m.group(1).strip() if m else ""


class PhenomScraper(BaseScraper):

    def scrape(self, driver) -> list:
        config = PHENOM_CONFIGS.get(self.company_name)
        if not config:
            logger.warning(f"[{self.company_name}] No Phenom config found")
            return []

        try:
            headers = {
                "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/120.0.0.0 Safari/537.36"),
            }
            r = requests.get(config["search_url"], headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"[{self.company_name}] Phenom {r.status_code}")
                return []

            html = r.text

            # jobSeqNo is unique per job and appears right after "title" in Phenom HTML.
            # Anchor on jobSeqNo and look back 2000 chars for title, city, state.
            seq_nos = re.findall(r'"jobSeqNo"\s*:\s*"([^"]+)"', html)
            seen = set()
            jobs = []

            for seq_no in seq_nos:
                if seq_no in seen:
                    continue
                seen.add(seq_no)

                m = re.search(rf'"jobSeqNo"\s*:\s*"{re.escape(seq_no)}"', html)
                if not m:
                    continue
                pos = m.start()

                # Look back 2000 chars — title/city/state are in this range
                window = html[max(0, pos - 2000): pos + 100]

                # Take the LAST occurrence of each field in the window
                # (avoids picking up values from the previous job object)
                titles = re.findall(r'"title"\s*:\s*"([^"]+)"', window)
                cities = re.findall(r'"city"\s*:\s*"([^"]+)"', window)
                states = re.findall(r'"state"\s*:\s*"([^"]+)"', window)

                title = titles[-1] if titles else ""
                city  = cities[-1] if cities else ""
                state = states[-1] if states else ""

                if not title or not self.is_data_role(title):
                    continue

                location = f"{city}, {state}, Canada" if city else "Canada"
                if not self.is_canada_job(location):
                    continue

                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                job_url = config["job_url_template"].format(jobSeqNo=seq_no, slug=slug)

                jobs.append(self.build_job(
                    title=title,
                    location=location,
                    url=job_url,
                    posted="Recent",
                ))

            logger.info(f"[{self.company_name}] Phenom: {len(jobs)} Canada data jobs")
            return jobs

        except Exception as e:
            logger.error(f"[{self.company_name}] Phenom error: {e}")
            return []
