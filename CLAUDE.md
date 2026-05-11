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

## Recently fixed (current session)
- **Apple** — Selenium scraper fixed: correct `a[href*='/details/']` selectors, `is_data_role` added, deduplication added
- **Meta** — Removed unstable auto-generated class selectors (`._8muv` etc.), added `/profile/job_details/` link fallback, added `is_data_role`
- **Google** — Added missing `is_data_role` filter to card loop and link fallback
- **IBM** — Fixed `is_data_role` + `is_canada_job` in Selenium path; API (`/api/jobs/v1/search`) returns 404, Selenium is active path
- **TD Bank** — Confirmed working via WorkdayScraper (92 jobs); `TDBankScraper` class in custom_scrapers.py is dead code
- **Scotiabank** — Two class definitions in custom_scrapers.py (lines ~496 and ~544); Python uses second one (SAP SuccessFactors version) which is correct

## Next session: fix 18 GenericScraper companies
These companies have `"scraper":"custom"` in settings.py but are NOT in the `dedicated` dict in `get_scraper()` → fall through to `GenericScraper` → return 0 jobs.

**Approach for each**: identify actual ATS → either update `"scraper"` type in settings.py OR write dedicated class and add to `dedicated` dict.

| Company | careers_url | Known ATS / notes |
|---------|-------------|-------------------|
| Goldman Sachs Canada | `https://www.goldmansachs.com/careers/search#ss=data+engineer` | Apollo GraphQL |
| Uber Canada | `https://www.uber.com/global/en/careers/list/?query=data+engineer...` | Custom |
| Atlassian Canada | `https://www.atlassian.com/company/careers/all-jobs?team=Engi...` | Likely Workday (auth) |
| Intuit Canada | `https://jobs.intuit.com/search-jobs?k=data+engineer&l=Canada` | Radancy |
| Tesla Canada | `https://www.tesla.com/careers/search?query=data+engineer&loc...` | Akamai-protected |
| Deloitte Canada | `https://careers.deloitte.ca/search-jobs/?k=data+engineer&l=C...` | SAP SuccessFactors |
| TELUS Health | `https://www.telus.com/en/about/careers/search-results?search...` | Custom |
| Canadian Tire Corporation | `https://careers.canadiantire.ca/search/?q=data+engineer` | Custom |
| Wayfair Canada | `https://www.wayfair.com/careers/jobs?country=Canada&query=da...` | Likely Greenhouse |
| Government of Canada | `https://www.canada.ca/en/services/jobs/opportunities/governm...` | GC Jobs API |
| Statistics Canada | `https://www.statcan.gc.ca/en/about/jobs` | GC Jobs API |
| Bank of Canada | `https://careers.bankofcanada.ca/search/?q=data+engineer` | Custom (Taleo?) |
| Kinaxis | `https://www.kinaxis.com/en/careers` | Unknown |
| Clio | `https://www.clio.com/careers` | Likely Greenhouse/Lever |
| Coveo | `https://www.coveo.com/en/company/careers` | Unknown |
| Layer6 AI (TD) | `https://layer6.ai/careers` | Unknown (small team) |
| Scotiabank Digital Factory | `https://www.scotiabank.com/ca/en/about/careers/search-for-jo...` | SAP SuccessFactors |
| SAP Canada | `https://jobs.sap.com/search/?q=data+engineer&location=Canada` | SAP SuccessFactors API |

**Quick wins (API-based, no Selenium)**:
- SAP Canada → SAP SuccessFactors API (same as Scotiabank's existing scraper)
- Wayfair → test `greenhouse` scraper with slug `wayfair`
- Clio → test `greenhouse` scraper with slug `clio`
- Deloitte → SAP SuccessFactors (same API pattern)

## Known issues / pending work
- **ChromeDriver**: uses `browser-actions/setup-chrome@v1` to auto-match versions
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
