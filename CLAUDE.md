# Job Alert Bot — CLAUDE.md

## What this bot does
Scrapes 200+ Canadian company career pages for Data Engineering jobs (Senior DE, Analytics Engineer, Data Platform Engineer, etc.) and sends a daily Gmail digest. Scrapes company career sites **directly** (not job boards) so alerts arrive before others.

## Stack
- Python 3.9, Selenium (Chrome headless), requests, smtplib
- GitHub Actions runs `python main.py` on a schedule

## Architecture
```
main.py              → orchestrates scraping, deduplication, email
config/settings.py   → COMPANIES list (200+ entries with scraper type + URL)
scrapers/
  base_scraper.py    → BaseScraper (Chrome setup, is_canada_job, is_data_role, build_job)
  custom_scrapers.py → get_scraper() dispatcher
  greenhouse_scraper.py  → Greenhouse boards API (no Selenium needed)
  lever_scraper.py       → Lever jobs API (no Selenium needed)
  workday_scraper.py     → Workday (POST /wday/cxs/.../jobs; Selenium fallback on 422)
  phenom_scraper.py      → Phenom People (regex on HTML, no Selenium)
  oracle_hcm_scraper.py  → Oracle Fusion HCM REST API
  ashby_scraper.py       → Ashby HQ API
  smartrecruiters_scraper.py → SmartRecruiters API
  avature_scraper.py     → Avature (Bloomberg)
  ibm_scraper.py         → IBM careers
  shopify_scraper.py     → Shopify custom
utils/
  deduplicator.py    → seen_jobs.json tracks job URLs already emailed
  email_builder.py   → builds and sends HTML email via Gmail SMTP
```

## Running
```bash
python main.py                  # daily run
python main.py --test-email     # send test email
python main.py --no-headless    # show Chrome window for debugging
python main.py --clear-cache    # reset seen_jobs.json
```

## Scraper types in COMPANIES list
| `scraper` value    | How it works                          |
|--------------------|---------------------------------------|
| `greenhouse`       | REST API, no auth, fast               |
| `lever`            | REST API, no auth, fast               |
| `workday`          | POST API; 422 = CSRF → Selenium       |
| `phenom`           | Regex on HTML page                    |
| `oracle_hcm`       | Oracle HCM REST API                   |
| `ashby`            | Ashby HQ API                          |
| `smartrecruiters`  | SmartRecruiters API                   |
| `avature`          | Avature (Bloomberg)                   |
| `ibm`              | IBM custom scraper                    |
| `custom`           | Selenium / not yet implemented        |

## Key constants
- Canada locationCountry param for Workday: `a30a87ed25634629aa6c3958aa2b91ea`
- Greenhouse API: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
- Lever API: `https://api.lever.co/v0/postings/{slug}?mode=json`

## Audit confidence (run audit.py to refresh)
- **100/204 confirmed** via API scrapers (✅ jobs found + ⚠️ scraper works, 0 jobs today)
- **18 Selenium** companies need Chrome to verify (Google, Microsoft, Amazon, Meta, Apple, Netflix, IBM, + 11 Workday 422 fallbacks)
- **86 GenericScraper** companies expected to return 0 (complex/auth-walled ATS)
- **0 errors** across all API scrapers

## Known issues / pending work
- **`custom` scraper = not implemented** for: Goldman Sachs (Apollo GraphQL), Tesla (Akamai), Atlassian (Workday auth-required), Intuit (Radancy), Citibank (Radancy), Deloitte (SAP SF), Great-West Lifeco (SAP SF), Capgemini (Radancy)
- **Workday 422** (CSRF) companies — use Selenium fallback in production: National Bank, Sun Life, Desjardins, Equifax, Ontario Health, Export Dev Canada, Ceridian, Morgan Stanley, OpenText
- **Loblaw** — Workday 422 (domain fixed to loblaw.wd3); uses Selenium fallback
- **Sun Life** — Workday board name unknown, uses search URL + Selenium fallback
- **HashiCorp Canada**: Acquired by IBM 2024; no active board found — `custom` (GenericScraper)

## Data flow
1. main.py splits companies: API scrapers (GH + Lever, 10 parallel) → Selenium scrapers (5 parallel)
2. Each scraper returns list of `build_job()` dicts
3. filter_new_jobs() checks against data/seen_jobs.json
4. New jobs sorted by seniority, emailed via Gmail SMTP

## Session tips
- `/compact` after finishing each scraper type (e.g. after all GH slug fixes)
- Start fresh sessions for unrelated work (email template changes vs. adding new companies)
- Use `curl -s "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs" | python3 -m json.tool | head -5` to verify GH slugs quickly
