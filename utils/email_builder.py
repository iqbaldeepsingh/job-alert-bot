"""
Email Builder + Sender
ਸੁੰਦਰ HTML email ਬਣਾਉਂਦਾ ਹੈ ਅਤੇ Gmail ਤੇ ਭੇਜਦਾ ਹੈ
"""

import smtplib
import ssl
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import EMAIL_CONFIG, COMPANIES

logger = logging.getLogger(__name__)

# Inline style constants
_HDR  = "background:linear-gradient(135deg,#0C447C,#185FA5);border-radius:12px;padding:22px 26px;margin-bottom:18px;"
_H1   = "color:#fff;font-size:20px;margin:0 0 5px;"
_SUB  = "color:#B5D4F4;font-size:12px;margin:0;"
_WRAP = "max-width:640px;margin:0 auto;padding:20px 10px;font-family:Arial,sans-serif;background:#f5f5f5;"
_JOBS = "background:#fff;border-radius:12px;padding:18px 22px;border:1px solid #eee;"
_FTR  = "text-align:center;color:#bbb;font-size:11px;padding:14px 0;"
_CH   = "font-size:13px;font-weight:700;color:#333;margin:16px 0 4px;border-left:3px solid #185FA5;padding-left:8px;"
_JR   = "padding:12px 0;border-bottom:1px solid #eee;"
_JT   = "color:#0C447C;font-size:14px;font-weight:600;"
_SAL  = "color:#888;font-size:11px;margin-left:6px;"
_JM   = "color:#777;font-size:11px;margin:4px 0;"
_BTN  = "display:inline-block;margin-top:7px;padding:5px 16px;background:#0C447C;color:#fff;text-decoration:none;border-radius:6px;font-size:12px;font-weight:600;"

STAT_STYLES = {
    "total":  ("background:#fff;border:1px solid #eee;",      "#0C447C", "#888"),
    "senior": ("background:#FAEEDA;border:1px solid #FAC775;","#633806", "#854F0B"),
    "mid":    ("background:#E6F1FB;border:1px solid #85B7EB;","#0C447C", "#185FA5"),
    "entry":  ("background:#EAF3DE;border:1px solid #C0DD97;","#27500A", "#3B6D11"),
}

BADGE_STYLES = {
    "lead":   "background:#F3E8FB;color:#5B1A8A;",
    "senior": "background:#FAEEDA;color:#633806;",
    "mid":    "background:#E6F1FB;color:#0C447C;",
    "entry":  "background:#EAF3DE;color:#27500A;",
}

_BADGE_BASE = "display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;vertical-align:middle;margin-left:6px;"
_SK_BASE    = "display:inline-block;background:#EEF4FB;color:#1A5FA5;border:1px solid #C5D9F0;border-radius:4px;padding:1px 7px;font-size:10px;margin:3px 3px 0 0;"


def _badge(level: str) -> str:
    l = level.lower()
    if "staff" in l or "lead" in l:
        return f'<span style="{_BADGE_BASE}{BADGE_STYLES["lead"]}">Staff / Lead</span>'
    if "senior" in l:
        return f'<span style="{_BADGE_BASE}{BADGE_STYLES["senior"]}">Senior</span>'
    if "entry" in l:
        return f'<span style="{_BADGE_BASE}{BADGE_STYLES["entry"]}">Entry Level</span>'
    return f'<span style="{_BADGE_BASE}{BADGE_STYLES["mid"]}">Mid-Level</span>'


def _stat_cell(label: str, value: int, key: str) -> str:
    bg, num_color, lbl_color = STAT_STYLES[key]
    return (f'<td style="text-align:center;border-radius:8px;padding:6px;{bg}">'
            f'<div style="font-size:22px;font-weight:700;color:{num_color};">{value}</div>'
            f'<div style="font-size:11px;color:{lbl_color};">{label}</div></td>')


def build_job_row(job: dict) -> str:
    url    = job.get("url", "")
    level  = job.get("level", "")
    posted = job.get("posted", "")
    salary = job.get("salary", "")
    skills = job.get("skills", [])[:5]
    apply  = f'<a style="{_BTN}" href="{url}">Apply Now →</a>' if url else ""
    skill_pills = "".join(f'<span style="{_SK_BASE}">{s}</span>' for s in skills)
    meta = (f'🏢 {job["company"]} &nbsp;·&nbsp; '
            f'📍 {job.get("location","Canada")} &nbsp;·&nbsp; '
            f'🏢 Full-time'
            f'{(" &nbsp;·&nbsp; 📅 " + posted) if posted else ""}')
    sal_span  = f'<span style="{_SAL}">💰 {salary}</span>' if salary else ""
    skill_div = f'<div style="margin-top:4px;">{skill_pills}</div>' if skill_pills else ""
    return (f'<div style="{_JR}">'
            f'<b style="{_JT}">{job["title"]}</b>{_badge(level)}{sal_span}<br>'
            f'<div style="{_JM}">{meta}</div>'
            f'{skill_div}'
            f'{apply}'
            f'</div>')


def build_email_html(jobs: list, run_time: str) -> str:
    n_companies = len(COMPANIES)
    if not jobs:
        return f"""<div style="{_WRAP}">
  <div style="{_HDR}">
    <h1 style="{_H1}">✅ Job Alert Bot — Running Fine</h1>
    <p style="{_SUB}">{run_time} &nbsp;·&nbsp; {n_companies} companies monitored</p>
  </div>
  <div style="{_JOBS}text-align:center;padding:30px;">
    <p style="font-size:32px;margin:0 0 10px;">😴</p>
    <h2 style="color:#0C447C;font-size:18px;margin:0 0 8px;">No New Jobs Today</h2>
    <p style="color:#777;font-size:11px;">All {n_companies} companies were checked. No new Canada data engineering roles since last run.</p>
  </div>
  <div style="{_FTR}">🤖 Job Alert Bot &nbsp;·&nbsp; 9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {n_companies} companies</div>
</div>"""

    total  = len(jobs)
    senior = sum(1 for j in jobs if "Senior" in j.get("level", ""))
    mid    = sum(1 for j in jobs if "Mid" in j.get("level", ""))
    entry  = sum(1 for j in jobs if "Entry" in j.get("level", ""))

    by_cat = {}
    for job in jobs:
        by_cat.setdefault(job.get("category", "Other"), []).append(job)

    cat_icons = {
        "Banks": "🏦", "Fintech": "💳", "Big Tech": "💻",
        "Consulting": "🤝", "Data & Analytics": "📊",
        "Telecom": "📡", "Healthcare": "🏥", "Retail": "🛒",
        "Energy": "⚡", "Government": "🏛️", "Startups": "🚀",
    }

    sections = ""
    for cat, cat_jobs in by_cat.items():
        icon = cat_icons.get(cat, "📁")
        rows = "".join(build_job_row(j) for j in cat_jobs)
        sections += (f'<div style="{_CH}">{icon} {cat} '
                     f'<span style="font-weight:400;color:#aaa;font-size:11px;">({len(cat_jobs)} jobs)</span></div>'
                     f'{rows}')

    return f"""<div style="{_WRAP}">
  <div style="{_HDR}">
    <h1 style="{_H1}">🔔 Daily Job Alert — Data Engineering Canada</h1>
    <p style="{_SUB}">{run_time} &nbsp;·&nbsp; {total} new openings &nbsp;·&nbsp; {n_companies} companies monitored</p>
  </div>
  <table style="width:100%;margin-bottom:18px;border-collapse:collapse;"><tr>
    {_stat_cell("Total Jobs", total, "total")}
    <td width="8"></td>
    {_stat_cell("Senior", senior, "senior")}
    <td width="8"></td>
    {_stat_cell("Mid-Level", mid, "mid")}
    <td width="8"></td>
    {_stat_cell("Entry Level", entry, "entry")}
  </tr></table>
  <div style="{_JOBS}">{sections}</div>
  <div style="{_FTR}">🤖 Job Alert Bot &nbsp;·&nbsp; Selenium + GitHub Actions &nbsp;·&nbsp; 9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {n_companies} companies</div>
</div>"""


def send_broad_summary_email(company_counts: list, run_label: str = "Broad Test") -> bool:
    """Send a plain summary table: company name + job count for each company."""
    cfg = EMAIL_CONFIG
    now = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    total_companies = len(company_counts)
    working = sum(1 for _, n in company_counts if n > 0)
    total_jobs = sum(n for _, n in company_counts)
    subject = f"🔍 Broad Test Report: {working}/{total_companies} companies returning jobs — {datetime.now().strftime('%b %d, %Y')}"

    rows = ""
    for company, count in sorted(company_counts, key=lambda x: -x[1]):
        color = "#27500A" if count > 0 else "#999"
        icon  = "✅" if count > 0 else "❌"
        rows += (f'<tr><td style="padding:4px 10px;border-bottom:1px solid #eee;">{icon} {company}</td>'
                 f'<td style="padding:4px 10px;border-bottom:1px solid #eee;text-align:right;color:{color};font-weight:600;">{count}</td></tr>')

    html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="{_HDR}">
    <h1 style="{_H1}">🔍 Broad Test Report</h1>
    <p style="{_SUB}">{now} &nbsp;·&nbsp; {working}/{total_companies} companies working &nbsp;·&nbsp; {total_jobs} total jobs found</p>
  </div>
  <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #eee;border-radius:8px;">
    <tr style="background:#f5f5f5;">
      <th style="padding:8px 10px;text-align:left;font-size:12px;color:#555;">Company</th>
      <th style="padding:8px 10px;text-align:right;font-size:12px;color:#555;">Jobs Found</th>
    </tr>
    {rows}
  </table>
  <p style="color:#bbb;font-size:11px;text-align:center;margin-top:14px;">🤖 Job Alert Bot — Broad Test Run</p>
</div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["sender_email"]
    msg["To"]      = cfg["recipient_email"]
    msg.attach(MIMEText(html, "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=30, context=ctx) as server:
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        logger.info(f"✅ Broad summary email sent: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail auth failed — check App Password in .env file")
        return False
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


def send_email(jobs: list, run_label: str = "Daily") -> bool:
    cfg = EMAIL_CONFIG
    now = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    if not jobs:
        subject = f"✅ Job Alert [{run_label}]: No New Jobs — {datetime.now().strftime('%b %d, %Y')}"
    else:
        subject = f"🔔 Job Alert [{run_label}]: {len(jobs)} Data Engineering Jobs — {datetime.now().strftime('%b %d, %Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["sender_email"]
    msg["To"]      = cfg["recipient_email"]
    msg.attach(MIMEText(build_email_html(jobs, now), "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=30, context=ctx) as server:
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        logger.info(f"✅ Email sent: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail auth failed — check App Password in .env file")
        return False
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False
