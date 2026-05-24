# Job Alert Bot — CLAUDE.md

## What this bot does
Scrapes **206** Canadian company career pages for Data Engineering jobs and sends a Gmail digest at **9 AM and 6 PM EDT**. Scrapes company ATS directly (not job boards) so alerts arrive before LinkedIn/Indeed.

Roles tracked: Data Engineer, Analytics Engineer, ML Engineer, Data Platform Engineer, etc.
Roles excluded: Data Scientist, Data Science (too much noise, different career track).

Always sends an email — if no new jobs, sends a "No New Jobs" status email so the bot run is confirmed.

---

## Stack
- Python 3.11, Selenium (Chrome headless), requests, smtplib
- GitHub Actions cron: `0 12 * * *` (morning) + `0 21 * * *` (evening) UTC
- Targets 9 AM + 6 PM EDT. Scheduled 1 hour early to offset GitHub Actions delay (30–90 min)
- `browser-actions/setup-chrome@v1` ensures Chrome + ChromeDriver always match

---

## Architecture
```
main.py              → orchestrates scraping, deduplication, email
config/settings.py   → COMPANIES list (206 entries with scraper type + URL)
scrapers/
  base_scraper.py        → BaseScraper: is_canada_job(), is_data_role(), build_job(), Chrome setup
  custom_scrapers.py     → get_scraper() dispatcher + dedicated scrapers for Amazon, Microsoft,
                           Google, Meta, Apple, Netflix, Shopify, Scotiabank, IBM, etc.
  greenhouse_scraper.py  → Greenhouse boards JSON API (no Selenium)
  lever_scraper.py       → Lever jobs API (no Selenium)
  workday_scraper.py     → Workday POST API; 422/CSRF → Selenium fallback
  phenom_scraper.py      → Phenom People HTML regex (no Selenium)
  oracle_hcm_scraper.py  → Oracle Fusion HCM REST API
  ashby_scraper.py       → Ashby HQ REST API (no Selenium)
  smartrecruiters_scraper.py → SmartRecruiters REST API (no Selenium)
  avature_scraper.py     → Avature (Bloomberg)
utils/
  deduplicator.py    → seen_jobs.json tracks URLs already emailed (GitHub Actions cache)
  email_builder.py   → inline-styled HTML email via Gmail SMTP port 465
.github/workflows/
  job_alert.yml      → cron 0 12 + 0 21 UTC, Chrome install, pip cache, seen_jobs cache
```

---

## Scraper Types
| `scraper` value      | Method                                   | Selenium? |
|----------------------|------------------------------------------|-----------|
| `greenhouse`         | JSON API `/v1/boards/{slug}/jobs`        | No        |
| `lever`              | REST API `api.lever.co/v0/postings`      | No        |
| `workday`            | POST API; CSRF 422 → Selenium fallback   | Sometimes |
| `phenom`             | HTML regex on jobSeqNo                   | No        |
| `oracle_hcm`         | Oracle HCM REST API                      | No        |
| `ashby`              | Ashby HQ REST API                        | No        |
| `smartrecruiters`    | SmartRecruiters REST API                 | No        |
| `avature`            | Avature custom (Bloomberg only)          | No        |
| `custom`             | Dedicated class in custom_scrapers.py    | Usually   |

---

## Running
```bash
python main.py                  # full run (daily label)
python main.py --run morning    # run with morning label
python main.py --run evening    # run with evening label
python main.py --test-email     # send test email (no scraping)
python main.py --no-headless    # show Chrome window for debugging
python main.py --clear-cache    # reset seen_jobs.json (next run resends all)
python main.py --broad          # accept ALL job titles, sends company-count summary
```

---

## Key Constants
- Canada `locationCountry` for Workday API: `a30a87ed25634629aa6c3958aa2b91ea`
- USA `locationCountry` for Workday API: `bc33aa3152ec42d4995f4791a106ed09`
- Greenhouse API: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
- Lever API: `https://api.lever.co/v0/postings/{slug}?mode=json`

---

## Scraper Status (~206 companies)
| Status | Count |
|--------|-------|
| ✅ Confirmed working | ~97 |
| ❌ Not working / 0 results | ~42 |
| ❓ Untested | ~67 |

### Known broken (priority fix list)
| Company | Issue |
|---------|-------|
| Manulife | Phenom page went SPA (JS-rendered, needs Selenium) |
| National Bank | Workday CSRF → Selenium fallback (untested) |
| Sun Life Financial | Workday CSRF → Selenium fallback |
| Goldman Sachs | Apollo GraphQL, no scraper |
| JP Morgan Canada | Oracle HCM scanning 7000+ jobs — likely OOM/slow |
| Morgan Stanley | Workday returning 0 |
| HSBC Canada | Phenom 404 |
| Wealthsimple | Lever returning 0 |
| Visa Canada | SmartRecruiters returning 0 |
| LinkedIn Canada | Wrong scraper type assigned |
| Salesforce Canada | Workday returning 0 |
| IBM Canada | Custom scraper failing |
| Loblaw Companies | Workday returning 0 |
| Ontario Health | Workday returning 0 |
| TELUS Health | Custom scraper failing |
| Export Dev Canada | Taleo JS-rendered |

---

## Email Design
- **Inline CSS only** — Gmail strips `<style>` blocks, inline styles are the only reliable method
- **50-job chunks** — Gmail clips emails >102KB; chunked emails labeled `(1/3)`, `(2/3)` etc.
- **Sorted by seniority**: Staff/Lead → Senior → Mid-Level → Entry Level
- **Grouped by category**: Banks, Fintech, Big Tech, Consulting, Healthcare, Retail, Government, Startups
- **No-jobs email**: Always sends status email when 0 new jobs so you know the bot ran

---

## Data Flow
1. `main.py` splits 206 companies into API scrapers (Phase 1, 10 threads) + Selenium (Phase 2, 5 threads)
2. Each scraper returns list of `build_job()` dicts
3. `filter_new_jobs()` checks against `data/seen_jobs.json` (persisted via GitHub Actions cache)
4. New jobs sorted by seniority level, chunked into 50-job emails
5. Sent via Gmail SMTP (port 465 SSL)

---

## Adding a New Company
1. Add to `COMPANIES` in `config/settings.py`:
```python
{
    "name": "Company Name",
    "careers_url": "https://...",
    "category": "Fintech",       # Banks | Fintech | Big Tech | Consulting | Healthcare | Retail | Government | Startups
    "scraper": "greenhouse",     # see scraper types above
    "top100": False,
    "titles": ["Senior Data Engineer"],
    "stack": ["Python", "Spark"],
    "locations": ["Toronto"],
    "salary_range": "$100K-$160K"
}
```
2. Verify slug works:
   - Greenhouse: `curl -s "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs" | head -c 200`
   - Lever: `curl -s "https://api.lever.co/v0/postings/{slug}?mode=json" | head -c 200`
3. Run `python main.py --broad --no-headless` to confirm jobs appear

---

## Session Tips
- `/compact` after finishing each major feature or scraper fix
- Start fresh sessions for unrelated work (job-alert-bot vs code-review-graph)
- Always commit and push at end of session — work is not done until pushed
- When fixing a broken scraper: test with `--broad` first to see raw job count, then normal run

## Future Roadmap
- Fix ~42 broken scrapers (priority: Manulife, National Bank, Goldman Sachs, JP Morgan)
- Multi-role: Software Engineer, DevOps in addition to Data Engineering

### Multi-User Support (planned)
Support a second user (sister — Full Stack Developer, 8 yrs exp, TD Canada + Amdocs India) alongside Iqbal.

**Key changes needed:**
- `config/users.py` — per-user profile: name, email, countries, role_type
- `is_fullstack_role()` in base_scraper.py — new role filter (React, Node, Java, Spring Boot, Angular, etc.)
- Location filter per user: Iqbal = Canada only, Sister = Canada + US
- Separate dedup cache per user: `data/seen_jobs_iqbal.json`, `data/seen_jobs_sister.json`
- Scrape once, filter per user — no double scraping
- GitHub Actions: two cache keys, email sent to each user independently
