# Job Alert Bot — CLAUDE.md

## What this bot does
Scrapes 204 Canadian company career pages for Data Engineering jobs (Senior DE, Analytics Engineer, Data Platform Engineer, etc.) and sends a daily Gmail digest at **9 AM and 6 PM EDT**. Scrapes company career sites **directly** (not job boards) so alerts arrive before others.

Always sends an email — if no new jobs, sends a "No New Jobs" status email so you know the bot ran successfully.

## Stack
- Python 3.9, Selenium (Chrome headless), requests, smtplib
- GitHub Actions runs `python main.py` on a cron schedule
- `browser-actions/setup-chrome@v1` ensures Chrome + ChromeDriver always match

## Architecture
```
main.py              → orchestrates scraping, deduplication, email
config/settings.py   → COMPANIES list (204 entries with scraper type + URL)
audit.py             → tests all API scrapers without Selenium, prints report
scrapers/
  base_scraper.py        → BaseScraper (Chrome setup, is_canada_job, is_data_role, build_job)
  custom_scrapers.py     → get_scraper() dispatcher + AmazonScraper, MicrosoftScraper,
                           GoogleScraper, MetaScraper, AppleScraper, NetflixScraper,
                           ShopifyScraper, IBMScraper, ScotiabankScraper
  greenhouse_scraper.py  → Greenhouse boards API (no Selenium needed)
  lever_scraper.py       → Lever jobs API (no Selenium needed)
  workday_scraper.py     → Workday POST API; 422 = CSRF → Selenium fallback
  phenom_scraper.py      → Phenom People API (no Selenium needed)
  oracle_hcm_scraper.py  → Oracle Fusion HCM REST API
  ashby_scraper.py       → Ashby HQ API
  smartrecruiters_scraper.py → SmartRecruiters API
  avature_scraper.py     → Avature (Bloomberg)
  ibm_scraper.py         → IBM careers (Selenium)
  shopify_scraper.py     → Shopify (Selenium)
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
python audit.py                 # test all API scrapers, print confidence report
```

## Scraper types in COMPANIES list
| `scraper` value    | How it works                                    |
|--------------------|-------------------------------------------------|
| `greenhouse`       | REST API, no auth, fast                         |
| `lever`            | REST API, no auth, fast                         |
| `workday`          | POST API; 422 = CSRF → Selenium fallback        |
| `phenom`           | Phenom People API                               |
| `oracle_hcm`       | Oracle HCM REST API                             |
| `ashby`            | Ashby HQ API                                    |
| `smartrecruiters`  | SmartRecruiters API                             |
| `avature`          | Avature (Bloomberg)                             |
| `custom`           | Dedicated scraper (Amazon, Microsoft, IBM etc.) |

## Key constants
- Canada locationCountry param for Workday: `a30a87ed25634629aa6c3958aa2b91ea`
- Greenhouse API: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
- Lever API: `https://api.lever.co/v0/postings/{slug}?mode=json`

## Schedule (GitHub Actions)
- **9 AM EDT** → `--run morning` → subject: `Morning (9 AM)`
- **6 PM EDT** → `--run evening` → subject: `Evening (6 PM)`
- **Manual trigger** → `--run daily` → subject: `Daily`

## Audit confidence (run audit.py to refresh)
- **101/204 confirmed** via API scrapers (✅ jobs found + ⚠️ scraper works, 0 jobs today)
- **17 Selenium** companies need Chrome (Google, Microsoft, Amazon, Meta, Apple, Netflix, IBM, Shopify, Scotiabank + 8 Workday 422 fallbacks)
- **86 GenericScraper** companies return 0 (planned: add scrapers or skip permanently)
- **0 errors** across all API scrapers

## Known issues / pending work
- **ChromeDriver**: uses `browser-actions/setup-chrome@v1` to auto-match versions
- **`custom` scraper = not implemented** for: Goldman Sachs (Apollo GraphQL), Tesla (Akamai), Atlassian (Workday auth), Intuit (Radancy), Deloitte (SAP SF), Uber, TELUS Health, Canadian Tire, Kinaxis, Clio, Coveo
- **Workday 422** (CSRF) companies — Selenium fallback: National Bank, Sun Life, Desjardins, Equifax, Ontario Health, Export Dev Canada, Ceridian, Morgan Stanley, OpenText, Loblaw
- **Sun Life** — Workday board slug unknown; loads search URL via Selenium
- **HashiCorp Canada** — Acquired by IBM 2024; no active board → GenericScraper
- **Priority companies to add**: Jobber, Zendesk, Okta, Fortinet, PayPal, Snap, Ubisoft, Uber, Deloitte, TCS, Wipro, Infosys, Cognizant, Capgemini, Citibank, Aviva, Oracle, Robinhood, Affirm, City of Toronto

## Data flow
1. `main.py` splits companies: API scrapers (10 parallel) → Selenium scrapers (5 parallel)
2. Each scraper returns list of `build_job()` dicts
3. `filter_new_jobs()` checks against `data/seen_jobs.json`
4. New jobs sorted by seniority, emailed via Gmail SMTP
5. If 0 new jobs → sends status email "No New Jobs" instead of skipping

## Session tips
- `/compact` after finishing each scraper type
- Start fresh sessions for unrelated work
- Verify Greenhouse slugs: `curl -s "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs" | python3 -m json.tool | head -5`
- Verify Lever slugs: `curl -s "https://api.lever.co/v0/postings/{slug}?mode=json" | python3 -m json.tool | head -5`
- Run `python audit.py` after adding new companies to confirm they work
