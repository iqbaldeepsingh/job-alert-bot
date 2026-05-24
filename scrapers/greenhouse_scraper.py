import logging
from scrapers.base_scraper import BaseScraper, get_session

logger = logging.getLogger(__name__)

GREENHOUSE_SLUGS = {
    # ── Verified working ──
    "Databricks Canada":           "databricks",
    "Fivetran Canada":             "fivetran",
    "Geotab":                      "geotab",
    "dbt Labs Canada":             "dbtlabsinc",
    "Airbnb Canada":               "airbnb",
    "Datadog Canada":              "datadog",
    "MongoDB Canada":              "mongodb",
    "Elastic Canada":              "elastic",
    "Stripe Canada":               "stripe",
    "Unity Technologies Canada":   "unity3d",
    "Affirm Canada":               "affirm",
    "Okta Canada":                 "okta",
    "Robinhood Canada":            "robinhood",
    "D2L / Desire2Learn":          "d2l",
    "Tulip Retail":                "tulip",
    "Flipp":                       "flipp",
    "AbCellera Biologics":         "abcellera",
    "Ritual":                      "ritual",
    "Capco Canada":                "capco",
    # ── Active Greenhouse boards ──
    "Hootsuite":                   "hootsuite",
    "DoorDash Canada":             "doordashusa",
    "Reddit Canada":               "reddit",
    "Dropbox Canada":              "dropbox",
    "Pinterest Canada":            "pinterest",
    "Lyft Canada":                 "lyft",
    "HubSpot Canada":              "hubspot",
    "Twilio Canada":               "twilio",
    "Cloudflare Canada":           "cloudflare",
    "TouchBistro":                 "touchbistro",
    "Benevity":                    "benevity",
    "Ecobee":                      "ecobee",
    "Faire":                       "faire",
    "League Inc":                  "leagueinc",
    "Instacart Canada":            "instacart",
    "Dagster":                     "dagsterlabs",
    "Borealis AI (RBC)":           "borealisai",
    "Procore Technologies Canada": "procore",
    "Coinbase Canada":             "coinbase",
    "Nuvei":                       "nuveinc",
    "Canva Canada":                "canva",
    # ── New companies ──
    "Figma Canada":                "figma",
    "Square / Block Canada":       "block",
    "LinkedIn Canada":             "linkedin",
    # ML / AI companies
    "Scale AI":                    "scaleai",
    "Anthropic":                   "anthropic",
    "Stability AI":                "stabilityai",
    "Together AI":                 "togetherai",
    "xAI":                         "xai",
    "Inflection AI":               "inflectionai",
    "Roblox":                      "roblox",
    "Riot Games":                  "riotgames",
    "Epic Games":                  "epicgames",
    "Roku":                        "roku",
    "GitLab":                      "gitlab",
    "Waymo":                       "waymo",
    "Jane Street":                 "janestreet",
    "Point72":                     "point72",
    "Jump Trading":                "jumptrading",
    "WorldQuant":                  "worldquant",
    "PDT Partners":                "pdtpartners",
}

# Slugs verified to work — skip +inc/+hq fallbacks for these
VERIFIED_SLUGS = {
    "Databricks Canada", "Fivetran Canada", "Geotab", "dbt Labs Canada",
    "Airbnb Canada", "Datadog Canada", "MongoDB Canada", "Borealis AI (RBC)",
    "Wayfair Canada",
}


class GreenhouseScraper(BaseScraper):

    def scrape(self, driver) -> list:
        slug = GREENHOUSE_SLUGS.get(self.company_name)
        if not slug:
            logger.warning(f"[{self.company_name}] No slug found")
            return []

        if self.company_name in VERIFIED_SLUGS:
            slugs_to_try = [slug]
        else:
            slugs_to_try = [slug, slug.replace("-", ""), slug + "inc", slug + "hq"]

        all_jobs = []
        session = get_session()
        for s in slugs_to_try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true"
            try:
                resp = session.get(url, timeout=8)
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
            skills = self.extract_skills(job.get("content", ""))
            jobs.append(self.build_job(
                title=title,
                location=location,
                url=apply_url,
                skills=skills,
                posted="Recent",
            ))
        return jobs
