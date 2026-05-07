"""
Deduplicator
ਪਹਿਲਾਂ ਭੇਜੇ jobs track ਕਰਦਾ ਹੈ — ਹਰ email ਵਿੱਚ ਸਿਰਫ਼ fresh jobs
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import SEEN_JOBS_FILE

logger = logging.getLogger(__name__)
EXPIRY_DAYS = 14


def _fingerprint(job: dict) -> str:
    key = f"{job.get('company','').lower()}__{job.get('title','').lower()}__{job.get('location','').lower()}"
    return hashlib.md5(key.encode()).hexdigest()


def _load() -> dict:
    path = Path(SEEN_JOBS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(seen: dict):
    try:
        with open(SEEN_JOBS_FILE, "w") as f:
            json.dump(seen, f, indent=2)
    except Exception as e:
        logger.error(f"Cache save failed: {e}")


def filter_new_jobs(jobs: list) -> list:
    seen   = _load()
    now    = datetime.now().isoformat()
    cutoff = (datetime.now() - timedelta(days=EXPIRY_DAYS)).isoformat()

    # ਪੁਰਾਣੇ entries ਹਟਾਓ
    seen = {fp: ts for fp, ts in seen.items() if ts > cutoff}

    new_jobs = []
    for job in jobs:
        fp = _fingerprint(job)
        if fp not in seen:
            new_jobs.append(job)
            seen[fp] = now

    _save(seen)
    logger.info(f"Dedup: {len(jobs)} scraped → {len(new_jobs)} new jobs")
    return new_jobs


def clear_cache():
    _save({})
    logger.info("Cache cleared")