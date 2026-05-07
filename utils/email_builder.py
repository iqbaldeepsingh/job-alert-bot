"""
Email Builder + Sender
ਸੁੰਦਰ HTML email ਬਣਾਉਂਦਾ ਹੈ ਅਤੇ Gmail ਤੇ ਭੇਜਦਾ ਹੈ
"""

import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import EMAIL_CONFIG, MAX_JOBS_PER_EMAIL

logger = logging.getLogger(__name__)


def build_level_badge(level: str) -> str:
    styles = {
        "Senior":       "background:#FAEEDA;color:#633806;",
        "Staff / Lead": "background:#EEEDFE;color:#3C3489;",
        "Mid-Level":    "background:#E6F1FB;color:#0C447C;",
        "Entry Level":  "background:#EAF3DE;color:#27500A;",
        "Principal":    "background:#F5E6FF;color:#7A1A9A;",
    }
    style = styles.get(level, "background:#F1EFE8;color:#444;")
    return (f'<span style="{style}padding:2px 8px;border-radius:12px;'
            f'font-size:11px;font-weight:600;">{level}</span>')


def build_job_row(job: dict) -> str:
    skills_html = "".join(
        f'<span style="background:#E6F1FB;color:#0C447C;padding:2px 7px;'
        f'border-radius:8px;font-size:11px;margin-right:4px;">{s}</span>'
        for s in job.get("skills", [])[:5]
    )
    apply_btn = ""
    if job.get("url"):
        apply_btn = (
            f'<a href="{job["url"]}" style="display:inline-block;margin-top:6px;'
            f'padding:4px 12px;background:#185FA5;color:#fff;text-decoration:none;'
            f'border-radius:6px;font-size:12px;">Apply Now →</a>'
        )
    salary = f'<span style="color:#3B6D11;font-size:12px;"> 💰 {job["salary"]}</span>' \
             if job.get("salary") else ""

    return f"""
    <tr>
      <td style="padding:14px 0;border-bottom:1px solid #eee;">
        <strong style="font-size:14px;color:#0C447C;">{job['title']}</strong>
        &nbsp;{build_level_badge(job.get('level',''))}
        {salary}<br>
        <span style="font-size:12px;color:#555;">
          🏢 {job['company']} &nbsp;·&nbsp;
          📍 {job.get('location','Canada')} &nbsp;·&nbsp;
          💼 {job.get('type','Full-time')} &nbsp;·&nbsp;
          🕐 {job.get('posted','Recent')}
        </span><br>
        <div style="margin-top:5px;">{skills_html}</div>
        {apply_btn}
      </td>
    </tr>"""


def build_email_html(jobs: list, run_time: str) -> str:
    total   = len(jobs)
    senior  = sum(1 for j in jobs if "Senior" in j.get("level", ""))
    mid     = sum(1 for j in jobs if "Mid" in j.get("level", ""))
    entry   = sum(1 for j in jobs if "Entry" in j.get("level", ""))

    # Group by category
    by_cat = {}
    for job in jobs[:MAX_JOBS_PER_EMAIL]:
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
      {run_time} &nbsp;·&nbsp; {total} new openings &nbsp;·&nbsp; 250 companies monitored
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
    9:00 AM &amp; 7:00 PM daily &nbsp;·&nbsp; 250 companies
  </div>

</div>
</body>
</html>"""


def send_email(jobs: list, run_label: str = "Daily") -> bool:
    cfg     = EMAIL_CONFIG
    now     = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    subject = (f"🔔 Job Alert [{run_label}]: "
               f"{len(jobs)} Data Engineering Jobs — "
               f"{datetime.now().strftime('%b %d, %Y')}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["sender_email"]
    msg["To"]      = cfg["recipient_email"]
    msg.attach(MIMEText(build_email_html(jobs, now), "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
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