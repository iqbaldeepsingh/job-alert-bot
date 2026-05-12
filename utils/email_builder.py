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

CSS = """
<style>
body{margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;}
.wrap{max-width:640px;margin:0 auto;padding:20px 10px;}
.hdr{background:linear-gradient(135deg,#0C447C,#185FA5);border-radius:12px;padding:22px 26px;margin-bottom:18px;}
.hdr h1{color:#fff;font-size:20px;margin:0 0 5px;}
.hdr p{color:#B5D4F4;font-size:12px;margin:0;}
.stats{width:100%;margin-bottom:18px;border-collapse:collapse;}
.stat{text-align:center;border-radius:8px;padding:6px;}
.s-total{background:#fff;border:1px solid #eee;}
.s-senior{background:#FAEEDA;border:1px solid #FAC775;}
.s-mid{background:#E6F1FB;border:1px solid #85B7EB;}
.s-entry{background:#EAF3DE;border:1px solid #C0DD97;}
.sn{font-size:22px;font-weight:700;}
.sl{font-size:11px;}
.s-total .sn{color:#0C447C;} .s-total .sl{color:#888;}
.s-senior .sn{color:#633806;} .s-senior .sl{color:#854F0B;}
.s-mid .sn{color:#0C447C;} .s-mid .sl{color:#185FA5;}
.s-entry .sn{color:#27500A;} .s-entry .sl{color:#3B6D11;}
.jobs{background:#fff;border-radius:12px;padding:18px 22px;border:1px solid #eee;}
.ch{font-size:13px;font-weight:700;color:#333;margin:16px 0 4px;border-left:3px solid #185FA5;padding-left:8px;}
.cn{font-weight:400;color:#aaa;font-size:11px;}
.jr{padding:12px 0;border-bottom:1px solid #eee;}
.jt{color:#0C447C;font-size:14px;font-weight:600;}
.sal{color:#888;font-size:11px;margin-left:6px;}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;vertical-align:middle;margin-left:6px;}
.b-lead{background:#F3E8FB;color:#5B1A8A;}
.b-senior{background:#FAEEDA;color:#633806;}
.b-mid{background:#E6F1FB;color:#0C447C;}
.b-entry{background:#EAF3DE;color:#27500A;}
.jm{color:#777;font-size:11px;margin:4px 0;}
.sk{display:inline-block;background:#EEF4FB;color:#1A5FA5;border:1px solid #C5D9F0;border-radius:4px;padding:1px 7px;font-size:10px;margin:3px 3px 0 0;}
.btn{display:inline-block;margin-top:7px;padding:5px 16px;background:#0C447C;color:#fff;text-decoration:none;border-radius:6px;font-size:12px;font-weight:600;}
.ftr{text-align:center;color:#bbb;font-size:11px;padding:14px 0;}
</style>
"""


def _badge(level: str) -> str:
    l = level.lower()
    if "staff" in l or "lead" in l:
        return f'<span class="badge b-lead">Staff / Lead</span>'
    if "senior" in l:
        return f'<span class="badge b-senior">Senior</span>'
    if "entry" in l:
        return f'<span class="badge b-entry">Entry Level</span>'
    return f'<span class="badge b-mid">Mid-Level</span>'


def build_job_row(job: dict) -> str:
    url    = job.get("url", "")
    level  = job.get("level", "")
    posted = job.get("posted", "")
    salary = job.get("salary", "")
    skills = job.get("skills", [])[:5]
    apply  = f'<a class="btn" href="{url}">Apply Now →</a>' if url else ""
    skill_pills = "".join(f'<span class="sk">{s}</span>' for s in skills)
    meta = (f'🏢 {job["company"]} &nbsp;·&nbsp; '
            f'📍 {job.get("location","Canada")} &nbsp;·&nbsp; '
            f'🏢 Full-time'
            f'{(" &nbsp;·&nbsp; 📅 " + posted) if posted else ""}')
    return (f'<div class="jr">'
            f'<b class="jt">{job["title"]}</b>{_badge(level)}'
            f'{"<span class=\\"sal\\">💰 " + salary + "</span>" if salary else ""}<br>'
            f'<div class="jm">{meta}</div>'
            f'{"<div>" + skill_pills + "</div>" if skill_pills else ""}'
            f'{apply}'
            f'</div>')


def build_email_html(jobs: list, run_time: str) -> str:
    if not jobs:
        return f"""{CSS}
<div class="wrap">
  <div class="hdr">
    <h1>✅ Job Alert Bot — Running Fine</h1>
    <p>{run_time} &nbsp;·&nbsp; {len(COMPANIES)} companies monitored</p>
  </div>
  <div class="jobs" style="text-align:center;padding:30px;">
    <p style="font-size:32px;margin:0 0 10px;">😴</p>
    <h2 style="color:#0C447C;font-size:18px;margin:0 0 8px;">No New Jobs Today</h2>
    <p class="jm">All {len(COMPANIES)} companies were checked. No new Canada data engineering roles since last run.</p>
  </div>
  <div class="ftr">🤖 Job Alert Bot &nbsp;·&nbsp; 9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {len(COMPANIES)} companies</div>
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
        sections += f'<div class="ch">{icon} {cat} <span class="cn">({len(cat_jobs)} jobs)</span></div>{rows}'

    return f"""{CSS}
<div class="wrap">
  <div class="hdr">
    <h1>🔔 Daily Job Alert — Data Engineering Canada</h1>
    <p>{run_time} &nbsp;·&nbsp; {total} new openings &nbsp;·&nbsp; {len(COMPANIES)} companies monitored</p>
  </div>
  <table class="stats"><tr>
    <td class="stat s-total"><div class="sn">{total}</div><div class="sl">Total Jobs</div></td>
    <td width="8"></td>
    <td class="stat s-senior"><div class="sn">{senior}</div><div class="sl">Senior</div></td>
    <td width="8"></td>
    <td class="stat s-mid"><div class="sn">{mid}</div><div class="sl">Mid-Level</div></td>
    <td width="8"></td>
    <td class="stat s-entry"><div class="sn">{entry}</div><div class="sl">Entry Level</div></td>
  </tr></table>
  <div class="jobs">{sections}</div>
  <div class="ftr">🤖 Job Alert Bot &nbsp;·&nbsp; Selenium + GitHub Actions &nbsp;·&nbsp; 9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {len(COMPANIES)} companies</div>
</div>"""


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
