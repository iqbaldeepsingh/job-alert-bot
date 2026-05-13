# 🔔 Job Alert Bot — Data Engineering Canada

> Scrapes **206 Canadian company career pages directly** and emails new Data Engineering jobs twice a day — before they show up on LinkedIn or Indeed.

No job boards. No scraping aggregators. Direct ATS API calls.

---

## ✨ How It Works

```
8:00 AM & 5:00 PM UTC  (targets 9 AM & 6 PM EDT, scheduled early to offset GitHub Actions delay)
        ↓
GitHub Actions spins up Ubuntu + Chrome
        ↓
206 companies scraped in parallel (API-first, Selenium fallback)
        ↓
Filter: Canada only + Data Engineering roles only (no Data Scientist)
        ↓
Deduplicate: skip any job already seen in previous runs
        ↓
Sort by seniority: Staff/Lead → Senior → Mid → Entry
        ↓
Chunk into 50-job emails if large batch
        ↓
📧 HTML digest lands in Gmail
```

---

## 📊 Coverage — 206 Companies

### 🏦 Banks & Finance (~20)
RBC, TD Bank, Scotiabank, CIBC, BMO, Intact Financial, Great-West Lifeco, Aviva Canada,
Capital One Canada, Citibank Canada, Barclays Canada, CPP Investments, Ontario Teachers Pension Plan,
HOOPP, PSP Investments, Fidelity Canada, TMX Group, Bloomberg Canada, Desjardins, Caisse de dépôt (CDPQ)

### 💳 Fintech (~18)
Stripe Canada, Affirm Canada, Mastercard Canada, PayPal Canada, Neo Financial, Koho, Trulioo,
Clearco, Robinhood Canada, Equifax Canada, TransUnion Canada, Wave Financial, Finastra Canada,
Klarna Canada, Coinbase Canada, Nuvei, Questrade, Wealthsimple

### 💻 Big Tech (~35)
Google, Microsoft, Amazon/AWS, Meta, Apple, Netflix, Shopify, Uber, Airbnb, Spotify,
Databricks, Snowflake, Confluent, Cohere AI, OpenAI, Atlassian, Adobe, Intuit, Workday,
ServiceNow, Autodesk, Oracle, Hootsuite, Reddit, Dropbox, Pinterest, Lyft, DoorDash,
HubSpot, Twilio, Cloudflare, Okta, Salesforce, SAP, Nvidia

### 📊 Data & Analytics (~10)
dbt Labs, Fivetran, Datadog, Elastic, MongoDB, Airbyte, Splunk, Astronomer, Palantir, Veeva Systems

### 🤝 Consulting (~15)
Accenture, Deloitte, PwC, EY, McKinsey, KPMG, CGI Group, Capco, IBM, Wipro,
Cognizant, HCL Technologies, TCS, Infosys, Capgemini

### 🏥 Healthcare (~8)
PointClickCare, League Inc, Sanofi Canada, Pfizer Canada, Ontario Health, TELUS Health,
LifeLabs, Roche Canada

### 🛒 Retail & E-Commerce (~12)
Walmart Canada, Canadian Tire, Best Buy Canada, Restaurant Brands International, Lululemon,
Loblaw, Sobeys, Wayfair, Faire, Instacart Canada, Air Canada, WestJet

### 🏛️ Government (~8)
City of Toronto, Bank of Canada, PSP Investments, Export Dev Canada, Statistics Canada,
Government of Canada, Ontario Digital Service, CMHC

### 🚀 Startups & Scale-ups (~30+)
Thomson Reuters, Geotab, Lightspeed Commerce, Coveo, D2L, Jobber, Clio, OpenText,
Ceridian/Dayforce, Kinaxis, Borealis AI, TouchBistro, Benevity, Ecobee, Ritual,
Procore, SS&C Technologies, NielsenIQ, and more...

---

## ✅ Confirmed Working vs ❌ Not Working

Out of 206 companies in config:

| Status | Count | Notes |
|--------|-------|-------|
| ✅ Confirmed working | **~97** | Appeared in actual email runs |
| ❌ Not working / 0 results | **~42** | Broken URL, JS-rendered page, wrong ATS |
| ❓ Untested | **~67** | In config, never returned jobs yet |

### ❌ Known broken (priority fix list)
| Company | Category | Issue |
|---------|----------|-------|
| Manulife | Banks | Phenom page went SPA (needs Selenium) |
| National Bank of Canada | Banks | Unknown |
| Sun Life Financial | Banks | Unknown |
| Goldman Sachs Canada | Banks | JS-rendered careers page |
| JP Morgan Canada | Banks | Oracle HCM returning 0 |
| Morgan Stanley Canada | Banks | Unknown |
| HSBC Canada | Banks | Phenom ATS returning 0 |
| Wealthsimple | Fintech | Lever returning 0 |
| Visa Canada | Fintech | SmartRecruiters returning 0 |
| LinkedIn Canada | Big Tech | Wrong scraper assigned |
| Salesforce Canada | Big Tech | Workday returning 0 |
| IBM Canada | Consulting | Custom scraper failing |
| Loblaw Companies | Retail | Workday returning 0 |
| Ontario Health | Healthcare | Workday returning 0 |
| TELUS Health | Healthcare | Custom scraper failing |
| Export Dev Canada | Government | Taleo JS-rendered |

---

## 📧 Email Format

Each email contains:
- **Header**: date, total count, companies monitored (dark blue banner)
- **Stats cards**: Total · Senior (orange) · Mid-Level (blue) · Entry Level (green)
- **Jobs grouped by category**, each job showing:
  - Title + seniority badge + salary range
  - Company · Location · Work type · Posted date
  - Tech stack pills (Azure, dbt, Spark...)
  - Apply Now button linking directly to the job posting

Large batches (>50 jobs) split into multiple emails labeled `(1/3)`, `(2/3)` etc.

---

## 🏗️ Architecture

```
job-alert-bot/
├── main.py                        # Orchestrator: scrape → dedup → sort → email
├── config/
│   └── settings.py                # 206 companies (name, URL, ATS type, stack, salary)
├── scrapers/
│   ├── base_scraper.py            # BaseScraper: is_data_role(), is_canada_job(), build_job()
│   ├── greenhouse_scraper.py      # Greenhouse JSON API (no Selenium)
│   ├── lever_scraper.py           # Lever REST API (no Selenium)
│   ├── workday_scraper.py         # Workday POST API (wd3/wd5/wd10/wd12 variants)
│   ├── phenom_scraper.py          # Phenom People HTML regex (no Selenium)
│   ├── ashby_scraper.py           # Ashby HQ REST API (no Selenium)
│   ├── smartrecruiters_scraper.py # SmartRecruiters REST API
│   ├── oracle_hcm_scraper.py      # Oracle HCM REST API
│   ├── avature_scraper.py         # Avature (Bloomberg)
│   └── custom_scrapers.py         # Amazon, Microsoft, Google, Meta, Shopify + GenericScraper fallback
├── utils/
│   ├── deduplicator.py            # seen_jobs.json — never sends same job twice
│   └── email_builder.py           # Inline-styled HTML email via Gmail SMTP
├── .github/
│   └── workflows/job_alert.yml    # GitHub Actions: 12:00 UTC + 21:00 UTC daily
└── data/
    └── seen_jobs.json             # Persisted via GitHub Actions cache between runs
```

### Parallelism
- **Phase 1** — API scrapers: 10 threads, no Chrome, fast (~30s)
- **Phase 2** — Selenium scrapers: 5 threads, each gets own Chrome instance
- Both phases complete before dedup + email

---

## ⚙️ Supported ATS Platforms

| Platform | Method | Example Companies |
|----------|--------|-------------------|
| **Greenhouse** | JSON API | Stripe, Databricks, Datadog, Airbnb, Okta, Hootsuite |
| **Lever** | REST API | Spotify, Klarna, PointClickCare, Wealthsimple |
| **Workday** | POST API | TD, CIBC, Intact, Autodesk, Nvidia, Salesforce, Adobe |
| **Phenom People** | HTML regex | RBC, BMO, Bell Canada, Air Canada, PwC |
| **Ashby HQ** | REST API | Cohere AI, Confluent, Snowflake, Koho, Lightspeed, Jobber |
| **SmartRecruiters** | REST API | Visa, Accenture, EA, Zynga, KUBRA |
| **Oracle HCM** | REST API | JP Morgan, Oracle, American Express |
| **Avature** | Custom | Bloomberg Canada |
| **Custom / Selenium** | Headless Chrome | Amazon, Microsoft, Google, Meta, Shopify, Scotiabank |
| **GenericScraper** | Selenium fallback | Companies with no dedicated scraper |

---

## 🎯 Role Filter

Only these title keywords pass the filter (`base_scraper.py → is_data_role()`):

```
data engineer · analytics engineer · data platform · big data · databricks · spark
pyspark · etl · elt · data architect · dataops · ml engineer · machine learning engineer
data analyst · pipeline engineer · data infrastructure · bi engineer · bi developer
business intelligence · data reliability · cloud data · data management · data product
data developer · data governance · ml platform · mlops · data pipeline · data quality
data integration · data warehouse · lakehouse · data migration · data streaming
streaming data · feature engineer · analytics platform · dbt developer · kafka engineer
snowflake engineer · flink engineer · airflow engineer · solutions engineer
solutions architect · feeds engineer · data security engineer · forward deployed
```

> **Excluded on purpose:** `data scientist`, `data science` — separate career track, too much noise

---

## 📅 Schedule

| Run | Cron (UTC) | Target (EDT) | Email Subject |
|-----|------------|--------------|---------------|
| Morning | `0 12 * * *` | ~9:00 AM EDT | `🔔 Job Alert [Morning (9 AM)]: N jobs` |
| Evening | `0 21 * * *` | ~6:00 PM EDT | `🔔 Job Alert [Evening (6 PM)]: N jobs` |
| No new jobs | Both | Both | `✅ No New Jobs — bot is running fine` |
| Manual trigger | On demand | Anytime | `🔔 Job Alert [Daily]: N jobs` |

> **Note:** GitHub Actions cron has 30–90 min delays during peak hours. Scheduled 1 hour early to compensate so emails arrive around the target time.

---

## 🚀 Local Setup

### 1. Clone & install
```bash
git clone https://github.com/iqbaldeepsingh/job-alert-bot.git
cd job-alert-bot
pip install -r requirements.txt
```

### 2. Create `.env`
```env
GMAIL_SENDER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password   # Gmail → Manage Account → App Passwords
GMAIL_RECIPIENT=alerts@youremail.com
```

### 3. Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions** and add:
- `GMAIL_SENDER`
- `GMAIL_APP_PASSWORD`
- `GMAIL_RECIPIENT`

### 4. Done — GitHub Actions runs automatically

---

## 🛠️ CLI Commands

```bash
# Full run
python main.py --run morning

# Send test email with 3 dummy jobs (no scraping)
python main.py --test-email

# Show Chrome window (debug Selenium scrapers)
python main.py --no-headless

# Clear seen-jobs cache (next run resends all jobs)
python main.py --clear-cache

# Broad mode: accept ALL job titles, sends company-count summary email
python main.py --broad
```

---

## ➕ Adding a New Company

1. Add to `COMPANIES` in [config/settings.py](config/settings.py):

```python
{
    "name": "Company Name",
    "careers_url": "https://company.greenhouse.io/boards/company",
    "category": "Fintech",      # Banks | Fintech | Big Tech | Consulting | Healthcare | Retail | Government | Startups
    "scraper": "greenhouse",    # greenhouse | lever | workday | phenom | ashby | smartrecruiters | oracle_hcm | avature | custom
    "top100": False,
    "titles": ["Senior Data Engineer", "Analytics Engineer"],
    "stack": ["Python", "Spark", "dbt"],
    "locations": ["Toronto", "Remote"],
    "salary_range": "$100K-$160K"
}
```

2. **For Workday**: find the tenant from the URL → `company.wd3.myworkdayjobs.com/BoardName`
   Add `locationCountry=a30a87ed25634629aa6c3958aa2b91ea` to URL to filter Canada only.

3. **Test it**:
```bash
python main.py --no-headless --broad
```

---

## 📈 Stats

| Metric | Value |
|--------|-------|
| Companies in config | **206** |
| Confirmed working | **~97** |
| ATS platforms supported | **9** |
| Emails per day | **2** (morning + evening) |
| Max jobs per email | **50** (chunked if more) |
| Duplicates ever sent | **0** |
| Roles tracked | Data Engineer, Analytics Engineer, ML Engineer |
| Roles excluded | Data Scientist, Data Science |

---

## 🧠 Key Design Decisions

| Decision | Reason |
|----------|--------|
| Direct ATS APIs, not job boards | Jobs appear 1–3 days earlier than LinkedIn/Indeed |
| Inline CSS in HTML emails | Gmail strips `<style>` blocks — inline styles only reliable method |
| GitHub Actions cache for `seen_jobs.json` | Free persistent storage between runs |
| 50-job email chunks | Gmail clips emails >102KB; chunking ensures full HTML renders |
| Phase 1 API → Phase 2 Selenium | APIs are fast and stable; Selenium only for JS-required sites |
| Canada filter before role filter | Avoids processing thousands of US jobs to find 10 Canadian ones |
| Cron scheduled 1 hour early | GitHub Actions has 30–90 min delays on scheduled workflows |
| Data Scientist excluded from role filter | Separate career track; creates too much noise for DE-focused alerts |

---

*Built with Python 3.11 · Runs free on GitHub Actions · Direct ATS scraping · No job boards used*
