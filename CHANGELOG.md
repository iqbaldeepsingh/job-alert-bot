# Job Alert Bot — Changelog

All notable changes to this project are documented here.
Each section covers one bot run cycle: what was broken → what was fixed → result.

---

## Branch Workflow (from 2026-05-12 onwards)

```
1. Create branch: fix/short-description or feat/short-description
2. Make all related changes on that branch
3. Merge to main
4. Run bot to test
5. Review email results
6. Repeat
```

---

## 2026-05-11 — Session: Filters, Email, Audit

### Run #17 — Baseline test (old code)
**Issues found:**
- TD Bank: 2 jobs found in logs but missing from email — GH Actions cache (`seen-jobs-*`) was preserving old `seen_jobs.json` across runs
- Only ~30 jobs in email despite 170 API companies being monitored
- Multi-location remote jobs (e.g. "Remote - Arizona; Remote - Canada") being rejected

**Root causes:**
- `is_canada_job()` had a non-Canada blocklist that rejected jobs containing any US city, even if Canada was also present
- `is_data_role()` had only ~15 keywords, missing Data Scientist, ML Engineer, Data Governance, BI Developer, etc.
- `MAX_JOBS_PER_EMAIL = 50` silently capped email at 50 jobs; header still showed full count

---

### fix/filter-fixes → `85eba66`
**Problem:** Bot was rejecting valid Canada jobs and missing many job titles.

**Changes — `scrapers/base_scraper.py`:**
- `is_canada_job()`: Removed the non-Canada blocklist entirely. Now accepts any location string that contains a Canadian keyword (city/province/remote-canada). Multi-location remote jobs like "Remote - Canada; Remote - California" now correctly pass.
- `is_data_role()`: Expanded from 15 → 50+ keywords:
  - Added: data scientist, data science, ML engineer, machine learning engineer
  - Added: data governance, data management, data product, data quality
  - Added: mlops, ml platform, data pipeline, data streaming, lakehouse
  - Added: BI engineer, BI developer, business intelligence, analytics platform
  - Added: solutions engineer, solutions architect, cloud architect
  - Added: chief data, vp of data, svp of data (executive roles)
  - Added: French titles: ingénieur de données, architecte de données
  - Added: forward deployed, distributed systems, managing director

**Result:** Jobs from Databricks, Cohere, ServiceNow, Reddit, Pinterest, Shopify, Intuit now appearing. ~50 → 213 jobs found.

---

### fix/email-cap → `7f322ec`
**Problem:** `MAX_JOBS_PER_EMAIL = 50` was cutting email body at 50 jobs but header still showed the full count (212). 162 jobs were silently dropped.

**Changes:**
- `config/settings.py`: Removed `MAX_JOBS_PER_EMAIL = 50`
- `utils/email_builder.py`: Removed `jobs[:MAX_JOBS_PER_EMAIL]` slice, now iterates all jobs

**Result:** All jobs now passed to email builder.

---

### feat/audit-broad-mode → `bbf4a5f`
**Problem:** `audit.py` tested scrapers with `data+engineer` keyword. A company returning 0 jobs could mean "scraper broken" OR "no data engineering jobs today" — impossible to distinguish.

**Changes — `audit.py`:**
- Added `--broad` flag: replaces `data+engineer` with `engineer` in all URLs, patches `is_data_role` to always return True
- Usage: `python audit.py --broad` → confirms all API scrapers are reachable regardless of data job availability

---

### fix/gmail-clip → `757a7a2` + `4877bfc`
**Problem:** Gmail clips emails over ~102KB. With 213 jobs × 5-line HTML rows, email was ~180KB — Gmail cut it off mid-email showing only ~58 jobs.

**Changes — `utils/email_builder.py`:**
- `build_job_row()` rewritten: 5-line card → 2-line compact row
- Line 1: Title (bold) + Level badge + Salary + inline `Apply →` button
- Line 2: Company · Location · Posted date · Skills (comma-separated, no pill badges)
- Removed large padding, border-radius decorations, multi-line skill tags

**Result:** All 213 jobs fit in email under Gmail's 102KB limit.

---

## 2026-05-11 — Session: Scraper Expansion (PR #1)

### fix/post-email-review → merged as `159b1a8`

**Problem:** audit.py showed only 71 companies working out of 205. Remaining 134 were falling through to GenericScraper returning 0 jobs.

**Changes:**
- `main.py`: Fixed API_TYPES check — was only treating `greenhouse` and `lever` as API scrapers, so Workday/Phenom/Ashby companies were being run through Selenium even when they have API scrapers
- Added scrapers for 30+ companies:
  - Cognizant, TCS, Wipro, Capgemini (Selenium)
  - Atlassian (Selenium)
  - Uber, Intuit, Clio, Coveo, Kinaxis (Selenium)
  - City of Toronto, PSP Investments (Workday)
  - Mackenzie Investments (iCIMS)
  - Aviva Canada (Workday)
  - Infosys Canada (Selenium)
  - 17 more via Workday, Phenom, Greenhouse, Dayforce
- Fixed Citibank (Phenom URL), Barclays + Zendesk (Workday slugs)
- Fixed PwC Canada (Workday → Phenom), KPMG (SmartRecruiters → iCIMS)
- Fixed IBM: added `is_data_role` + `is_canada_job` to Selenium path
- Added `test_company.py` for quick single-company testing
- Updated `audit.py` CUSTOM_WITH_DEDICATED list

---

## 2026-05-10

### Fix scrapers: Netflix, IBM, Greenhouse + Selenium improvements — `8c709c6`
- Netflix: switched from broken API to Selenium card scraper
- IBM: fixed careers URL (old URL returned 404)
- Added missing Greenhouse slugs for several companies
- Improved Selenium fallback stability

### Fix SMTP — `639913f`
**Problem:** Email sending was silently failing.
- Switched from port 587 (STARTTLS) to port 465 (SSL) for Gmail SMTP

---

## 2026-05-08

### ChromeDriver fix — `8dd9f58`
**Problem:** GitHub Actions Chrome version mismatched ChromeDriver version, causing all Selenium scrapers to crash.
- Added `browser-actions/setup-chrome@v1` to workflow — auto-matches Chrome + ChromeDriver versions

### Email improvements — `bb3c949` `3c1332b` `089157b`
- Fixed email subject labels (morning/evening/daily)
- Made company count dynamic from COMPANIES list
- Added "No New Jobs" status email so you always know the bot ran (instead of sending nothing)

### Schedule change — `bd70c00` `277618a`
- Shifted evening run from 7 PM → 6 PM EDT

### GenericScraper cleanup — `9449424`
- Reduced companies falling through to GenericScraper: 157 → 71
- Identified and documented which companies need dedicated scrapers

---

## Known Issues (as of 2026-05-11)

### Selenium companies returning 0 jobs (broken CSS selectors)
These Workday companies have a Selenium fallback but `li.css-1q2dra3` selector fails:
- National Bank of Canada
- Sun Life Financial
- Morgan Stanley Canada
- Desjardins
- Ontario Health
- Loblaw Companies
- Export Development Canada
- OpenText
- Ceridian / Dayforce
- Scotiabank

**Next fix:** Update Workday Selenium selector or switch to API where possible.

### Companies still on GenericScraper (0 jobs always)
Goldman Sachs, Uber, Tesla, TELUS Health, Government of Canada, Statistics Canada, Bank of Canada, Kinaxis (iCIMS slug unknown), Clio, Coveo, Layer6 AI, Scotiabank Digital Factory, SAP Canada, Deloitte Canada, Wayfair, Intuit (Radancy ATS)
