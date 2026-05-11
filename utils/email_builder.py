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


def build_job_row(job: dict) -> str:
    skills = ", ".join(job.get("skills", [])[:4])
    salary = f' · 💰 {job["salary"]}' if job.get("salary") else ""
    url    = job.get("url", "")
    apply  = f' <a href="{url}">[Apply]</a>' if url else ""
    level  = job.get("level", "")
    return (f'<tr><td style="padding:5px 0;border-bottom:1px solid #eee;">'
            f'<b>{job["title"]}</b> <i>[{level}]</i>{salary}{apply}<br>'
            f'<small>{job["company"]} · {job.get("location","Canada")} · {job.get("posted","Recent")}'
            f'{(" · " + skills) if skills else ""}</small>'
            f'</td></tr>')


def build_email_html(jobs: list, run_time: str) -> str:
    if not jobs:
        return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:20px 10px;">
  <div style="background:linear-gradient(135deg,#0C447C,#185FA5);
              border-radius:12px;padding:22px 26px;margin-bottom:18px;">
    <h1 style="color:#fff;font-size:20px;margin:0 0 5px;">✅ Job Alert Bot — Running Fine</h1>
    <p style="color:#B5D4F4;font-size:12px;margin:0;">{run_time} &nbsp;·&nbsp; {len(COMPANIES)} companies monitored</p>
  </div>
  <div style="background:#fff;border-radius:12px;padding:30px;text-align:center;">
    <p style="font-size:32px;margin:0 0 10px;">😴</p>
    <h2 style="color:#0C447C;font-size:18px;margin:0 0 8px;">No New Jobs Today</h2>
    <p style="color:#666;font-size:14px;margin:0;">All {len(COMPANIES)} companies were checked. No new Canada data engineering roles since last run.</p>
  </div>
  <div style="text-align:center;color:#bbb;font-size:11px;padding:14px 0;">
    🤖 Job Alert Bot &nbsp;·&nbsp; 9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {len(COMPANIES)} companies
  </div>
</div>
</body>
</html>"""

    total   = len(jobs)
    senior  = sum(1 for j in jobs if "Senior" in j.get("level", ""))
    mid     = sum(1 for j in jobs if "Mid" in j.get("level", ""))
    entry   = sum(1 for j in jobs if "Entry" in j.get("level", ""))

    # Group by category
    by_cat = {}
    for job in jobs:
        cat = job.get("category", "Other")
        by_cat.setdefault(cat, []).append(job)

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
        sections += f"""
        <tr><td style="padding:16px 0 4px;">
          <h2 style="font-size:13px;font-weight:700;color:#333;margin:0;
              border-left:3px solid #185FA5;padding-left:8px;">
            {icon} {cat}
            <span style="font-weight:400;color:#aaa;font-size:11px;">
              ({len(cat_jobs)} jobs)
            </span>
          </h2>
        </td></tr>
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:20px 10px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0C447C,#185FA5);
              border-radius:12px;padding:22px 26px;margin-bottom:18px;">
    <h1 style="color:#fff;font-size:20px;margin:0 0 5px;">
      🔔 Daily Job Alert — Data Engineering Canada
    </h1>
    <p style="color:#B5D4F4;font-size:12px;margin:0;">
      {run_time} &nbsp;·&nbsp; {total} new openings &nbsp;·&nbsp; {len(COMPANIES)} companies monitored
    </p>
  </div>

  <!-- Stats -->
  <table width="100%" cellpadding="6" style="margin-bottom:18px;">
    <tr>
      <td align="center" style="background:#fff;border-radius:8px;border:1px solid #eee;">
        <div style="font-size:22px;font-weight:700;color:#0C447C;">{total}</div>
        <div style="font-size:11px;color:#888;">Total Jobs</div>
      </td>
      <td width="8"></td>
      <td align="center" style="background:#FAEEDA;border-radius:8px;border:1px solid #FAC775;">
        <div style="font-size:22px;font-weight:700;color:#633806;">{senior}</div>
        <div style="font-size:11px;color:#854F0B;">Senior</div>
      </td>
      <td width="8"></td>
      <td align="center" style="background:#E6F1FB;border-radius:8px;border:1px solid #85B7EB;">
        <div style="font-size:22px;font-weight:700;color:#0C447C;">{mid}</div>
        <div style="font-size:11px;color:#185FA5;">Mid-Level</div>
      </td>
      <td width="8"></td>
      <td align="center" style="background:#EAF3DE;border-radius:8px;border:1px solid #C0DD97;">
        <div style="font-size:22px;font-weight:700;color:#27500A;">{entry}</div>
        <div style="font-size:11px;color:#3B6D11;">Entry Level</div>
      </td>
    </tr>
  </table>

  <!-- Jobs -->
  <div style="background:#fff;border-radius:12px;padding:18px 22px;border:1px solid #eee;">
    <table width="100%" cellpadding="0" cellspacing="0">
      {sections}
    </table>
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#bbb;font-size:11px;padding:14px 0;">
    🤖 Job Alert Bot &nbsp;·&nbsp; Selenium + GitHub Actions &nbsp;·&nbsp;
    9:00 AM &amp; 6:00 PM daily &nbsp;·&nbsp; {len(COMPANIES)} companies
  </div>

</div>
</body>
</html>"""


def send_email(jobs: list, run_label: str = "Daily") -> bool:
    cfg     = EMAIL_CONFIG
    now     = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    if not jobs:
        subject = (f"✅ Job Alert [{run_label}]: No New Jobs — "
                   f"{datetime.now().strftime('%b %d, %Y')}")
    else:
        subject = (f"🔔 Job Alert [{run_label}]: "
                   f"{len(jobs)} Data Engineering Jobs — "
                   f"{datetime.now().strftime('%b %d, %Y')}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["sender_email"]
    msg["To"]      = cfg["recipient_email"]
    msg.attach(MIMEText(build_email_html(jobs, now), "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=30, context=ctx) as server:
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(
                cfg["sender_email"],
                cfg["recipient_email"],
                msg.as_string()
            )
        logger.info(f"✅ Email sent: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail auth failed — check App Password in .env file")
        return False
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False