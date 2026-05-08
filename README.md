# 🔔 Job Alert Bot — Data Engineering Canada

> Scrapes **204 Canadian company career pages** directly and emails you new Data Engineering jobs twice a day — before they show up on LinkedIn or Indeed.

---

## ✨ How It Works

```
9:00 AM & 6:00 PM EDT
        ↓
GitHub Actions spins up
        ↓
Scrapes 204 company career pages directly
        ↓
Filters: Canada + Data Engineering roles only
        ↓
Deduplicates (never sends the same job twice)
        ↓
📧 Gmail digest arrives in your inbox
```

---

## 📊 Coverage

| Category | Companies | Method |
|----------|-----------|--------|
| Banks & Finance | RBC, TD, CIBC, BMO, Scotiabank, Capital One, Bloomberg... | Workday API, Phenom, Avature |
| Big Tech | Amazon, Microsoft, Google, Meta, Apple, Netflix, Shopify | Custom API / Selenium |
| Data & Analytics | Databricks, Snowflake, Confluent, Cohere, dbt Labs, Datadog... | Greenhouse, Ashby, Lever |
| Consulting | Accenture, KPMG, EY, McKinsey, CGI... | SmartRecruiters API |
| SaaS & Startups | Stripe, Spotify, Airbnb, PointClickCare, Wealthsimple... | Greenhouse, Lever |
| Healthcare & Gov | Manulife, Sun Life, Ontario Health, Sanofi... | Phenom, Workday |

**204 companies monitored · 9 ATS platforms supported · 0 job boards used**

---

## 📧 Email Preview

```
🔔 Job Alert [Morning (9 AM)]: 57 Data Engineering Jobs — May 08, 2026

┌──────────────────────────────────────────────┐
│  57 Total  │  18 Senior  │  23 Mid  │  10 Entry  │
└──────────────────────────────────────────────┘

🏦 Banks (24 jobs)
  Lead Data Engineer, GFT        [Staff/Lead] $85K-$215K
  RBC · Toronto, Ontario · Azure · Databricks · Spark

  Principal Data Engineer        [Senior] $82K-$215K
  BMO · Toronto, Ontario · Azure · Python · dbt
  ...
```

---

## 🏗️ Architecture

```
main.py                      → orchestrates scraping, dedup, email
config/settings.py           → 204 companies (name, URL, scraper type, stack, salary)
scrapers/
  greenhouse_scraper.py      → Greenhouse API  (no Selenium)
  lever_scraper.py           → Lever API       (no Selenium)
  workday_scraper.py         → Workday API     (Selenium fallback on CSRF)
  phenom_scraper.py          → Phenom People   (no Selenium)
  ashby_scraper.py           → Ashby HQ API    (no Selenium)
  smartrecruiters_scraper.py → SmartRecruiters API
  oracle_hcm_scraper.py      → Oracle HCM API
  avature_scraper.py         → Avature (Bloomberg)
  custom_scrapers.py         → Amazon, Microsoft, Google, IBM, Shopify...
utils/
  deduplicator.py            → tracks seen jobs in seen_jobs.json
  email_builder.py           → HTML email via Gmail SMTP
audit.py                     → test all scrapers without Chrome
```

---

## ⚙️ Setup

### 1. Clone & install
```bash
git clone https://github.com/iqbaldeepsingh/job-alert-bot.git
cd job-alert-bot
pip install -r requirements.txt
```

### 2. Create `.env`
```env
GMAIL_SENDER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
GMAIL_RECIPIENT=alerts@youremail.com
```

### 3. Add GitHub Secrets
Go to **Settings → Secrets → Actions** and add:
- `GMAIL_SENDER`
- `GMAIL_APP_PASSWORD`
- `GMAIL_RECIPIENT`

### 4. Enable GitHub Actions
The workflow runs automatically at **9 AM and 6 PM EDT** via `.github/workflows/job_alert.yml`.

---

## 🚀 Running Locally

```bash
# Full run
python main.py

# Send test email (doesn't scrape)
python main.py --test-email

# Show Chrome window for debugging
python main.py --no-headless

# Reset job history (resend all jobs)
python main.py --clear-cache

# Audit all scrapers (no Chrome needed, ~50s)
python audit.py
```

---

## 🔍 Supported ATS Platforms

| Platform | How | Example Companies |
|----------|-----|-------------------|
| Greenhouse | REST API | Stripe, Databricks, Datadog, LinkedIn, Airbnb |
| Lever | REST API | Spotify, Snowflake, Wealthsimple, PointClickCare |
| Workday | POST API | TD, CIBC, Intact, Autodesk, Nvidia, Salesforce |
| Phenom People | API | RBC, BMO, Manulife, Bell, Air Canada |
| Ashby HQ | REST API | Cohere, OpenAI, Confluent, Lightspeed, Koho |
| SmartRecruiters | REST API | Visa, Accenture, EY, McKinsey, KPMG, EA |
| Oracle HCM | REST API | JP Morgan, American Express |
| Avature | Custom | Bloomberg |
| Custom / Selenium | Headless Chrome | Amazon, Microsoft, Google, IBM, Shopify |

---

## 📅 Schedule

| Run | Time | Email Subject |
|-----|------|---------------|
| Morning | 9:00 AM EDT | `🔔 Job Alert [Morning (9 AM)]: N jobs` |
| Evening | 6:00 PM EDT | `🔔 Job Alert [Evening (6 PM)]: N jobs` |
| No new jobs | Either | `✅ Job Alert: No New Jobs — bot running fine` |
| Manual trigger | Anytime | `🔔 Job Alert [Daily]: N jobs` |

---

## 🛠️ Adding New Companies

1. Add entry to `COMPANIES` in [config/settings.py](config/settings.py):
```python
{
    "name": "Company Name",
    "careers_url": "https://...",
    "category": "Fintech",
    "scraper": "greenhouse",
    "top100": False,
    "titles": ["Senior Data Engineer"],
    "stack": ["Python", "Spark"],
    "locations": ["Toronto"],
    "salary_range": "$100K-$160K"
}
```
2. Add slug to the matching scraper's slug dict
3. Run `python audit.py` to verify

---

## 📈 Stats

| Metric | Value |
|--------|-------|
| Companies monitored | 204 |
| ATS platforms supported | 9 |
| API scrapers (no Chrome) | 101 confirmed |
| Selenium scrapers | 17 companies |
| Emails per day | 2 (9 AM + 6 PM EDT) |
| Duplicates sent | 0 (ever) |

---

*Built with Python · Runs free on GitHub Actions · Scrapes direct — not job boards*
