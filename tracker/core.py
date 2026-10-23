import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def canonical(url):
    p = urlsplit(html.unescape(clean(url)))
    if p.scheme not in ("http", "https") or not p.hostname:
        return ""
    keep = [(k, v) for k, v in parse_qsl(p.query) if k.lower() in
            {"jk", "gh_jid", "jobid", "job_id", "j", "id", "reqid", "language"}]
    path = p.path.rstrip("/")
    if "ashbyhq.com" in p.netloc or "lever.co" in p.netloc:
        path = re.sub(r"/application$", "", path)
    return urlunsplit(("https", p.netloc.lower(), path, urlencode(sorted(keep)), ""))


def identity(url):
    u = canonical(url)
    p = urlsplit(u)
    # Stable IDs remove language / display-title / application-path differences.
    for host, pattern in [("lever.co", r"/([^/]+)/([a-f0-9-]{36})"),
                          ("ashbyhq.com", r"/([^/]+)/([a-f0-9-]{36})"),
                          ("myworkdayjobs.com", r"_([A-Za-z0-9-]+)$")]:
        m = re.search(pattern, p.path)
        if host in p.netloc and m:
            return p.netloc + ":" + ":".join(m.groups())
    return u


def date_string(value):
    if not value:
        return None
    try:
        if isinstance(value, (float, int)):
            return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def category(title, config):
    t = title.lower()
    if re.search(r"pharma|pharmacy|pharmacist", t):
        return None
    # A support role reporting to a director/chief is not that senior role.
    primary_title = re.split(r"\s+to\s+(?:the\s+)?", t, maxsplit=1)[0]
    if any(re.search(p, primary_title) for p in config["exclude_title_patterns"]):
        return None
    if "legal assistant" in t or "legal receptionist" in t or "law clerk" in t:
        return "Legal support"
    for name, terms in config["categories"].items():
        if any(term in t for term in terms):
            return name
    return None


def assess(raw, config):
    title = clean(raw.get("title"))
    cat = category(title, config)
    if not cat:
        return None
    text = clean(raw.get("description"))
    lower = (title + " " + text).lower()
    loc = clean(raw.get("location"))
    known_cities = config["preferred_cities"] + config["commute_review_cities"]
    local = any(re.search(r"\b" + re.escape(city) + r"\b", loc.lower()) for city in known_cities)
    canadian = local or bool(re.search(r"\b(canada|ontario)\b", loc.lower()))
    remote_claim = raw.get("is_remote") is True or "remote" in title.lower()
    if re.search(r"\b(united states|usa|u\.s\.)\b", loc, re.I):
        return None
    if not canadian or (not local and not remote_claim):
        return None
    if re.search(r"\b(internal applicants only|current employees only)\b", title + " " + lower, re.I):
        return None
    flags = ["Check required experience and software skills against your résumé"]
    if remote_claim:
        flags.append("Remote claimed by source: confirm Ontario eligibility and office visits")
    if local and not any(city in loc.lower() for city in config["preferred_cities"]):
        flags.append("Commute review: transit from Brampton not verified")
    if re.search(r"driver.?s licen[cs]e|personal vehicle|own vehicle", lower):
        flags.append("Driving mentioned: check whether required or preferred")
    if re.search(r"bilingual|fluency in french|fluent in french", lower):
        flags.append("Language requirement: check whether French is mandatory")
    experience_warning = bool(re.search(r"\b(?:[3-9]|1[0-9])\+?\s*(?:years|year)[’'s]*\s*(?:of )?(?:relevant )?experience", lower))
    if experience_warning:
        flags.append("Experience requirement: review the stated years carefully")
    if re.search(r"commission.only|100% commission|commission.based", lower):
        flags.append("Commission-based compensation: verify guaranteed base pay")
    employment = clean(raw.get("job_type")) or "Unspecified"
    # Description wins over misleading aggregate full-time labels.
    fallback = re.search(r"\b(casual|temporary|fixed.term|part.time|contract (?:role|position|ending)|\d+.month contract)\b", title + " " + lower, re.I)
    if fallback or re.search(r"contract|temporary|parttime|casual", employment, re.I):
        tier = "Fallback"
        employment = "Temporary / contract / casual / part-time — check details"
        flags.append("Fallback employment: renewal or conversion not assumed")
    elif re.search(r"permanent|full.time|fulltime|budget - continuing", lower + " " + employment):
        tier = "Priority"
    else:
        tier = "Review"
        flags.append("Employment type not established")
    if (experience_warning or remote_claim or re.search(r"\bbilingual\b", lower)) and tier == "Priority":
        tier = "Review"
    if "law clerk" in title.lower():
        flags.append("Check law-clerk credential requirements")
    salary = raw.get("salary") or "Not disclosed / not extracted"
    if raw.get("min_amount") is not None:
        low, high = raw["min_amount"], raw.get("max_amount")
        interval = raw.get("interval") or "period unknown"
        if interval == "yearly" and low < 10000:
            flags.append("Salary unit inconsistent: verify in posting")
        else:
            salary = f"{raw.get('currency') or 'CAD'} {low:,.2f}" + (f"–{high:,.2f}" if high and high != low else "") + f" / {interval}"
    # Preserve short evidence snippets instead of mirroring entire descriptions.
    sentences = re.split(r"\n+|(?<=[.!?])\s+", text)
    evidence = [s.strip(" *#\t") for s in sentences if re.search(r"qualif|experience|permanent|contract|salary|\$|remote|full.time", s, re.I)]
    evidence = " ".join(evidence[:5]).split()[:90]
    return {"category": cat, "tier": tier, "employment": employment, "flags": flags,
            "salary": salary, "evidence": " ".join(evidence),
            "match_reason": f"Title aligns with the {cat.lower()} search; requirements need individual review"}


def merge(existing, incoming, config, now):
    records = {j["id"]: dict(j) for j in existing}
    aliases = {identity(u): j["id"] for j in existing for u in j.get("urls", []) if identity(u)}
    for raw in incoming:
        assessment = assess(raw, config)
        if not assessment:
            continue
        urls = [canonical(raw.get(k, "")) for k in ("job_url_direct", "job_url")]
        urls = [u for u in urls if u]
        if not urls:
            continue
        found = {aliases[identity(u)] for u in urls if identity(u) in aliases}
        jid = sorted(found)[0] if found else hashlib.sha256(identity(urls[0]).encode()).hexdigest()[:16]
        old = records.get(jid, {})
        # If a newly discovered direct URL bridges two older records, unite them.
        for other in found - {jid}:
            duplicate = records.pop(other)
            old["urls"] = sorted(set(old.get("urls", []) + duplicate.get("urls", [])))
            old["first_seen"] = min(old.get("first_seen", now), duplicate.get("first_seen", now))
            old["sources"] = sorted(set(old.get("sources", []) + duplicate.get("sources", [])))
        urls = sorted(set(urls + old.get("urls", [])))
        previous_url = old.get("url")
        job = {**old, **assessment, "id": jid, "title": clean(raw.get("title")),
               "company": clean(raw.get("company")), "location": clean(raw.get("location")),
               "url": canonical(raw.get("job_url_direct")) or old.get("url") or canonical(raw["job_url"]),
               "urls": urls, "posted_date": date_string(raw.get("date_posted")) or old.get("posted_date"),
               "posted_date_basis": raw.get("date_basis", "Source-reported; may be board-added date"),
               "first_seen": old.get("first_seen", now), "last_seen": now,
               "sources": sorted(set(old.get("sources", []) + [clean(raw.get("site")) or "manual"])),
               "status": old.get("status", "Unverified")}
        if previous_url and job["url"] != previous_url:
            job["status"] = "Unverified"
            for field in ("last_checked", "last_verified", "deadline", "missing_since"):
                job.pop(field, None)
            job["verification_note"] = "Application URL changed; new destination needs checking"
        records[jid] = job
        for u in urls:
            aliases[identity(u)] = jid
    for job in records.values():
        if job.get("status") != "Closed" and datetime.fromisoformat(job["last_seen"]) < datetime.fromisoformat(now) - timedelta(days=config["stale_after_days"]):
            job["status"] = "Stale — recheck"
    return list(records.values())


def atomic_json(path, obj):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


PUBLIC_JOB_FIELDS = frozenset({
    "category", "company", "deadline", "employment", "evidence", "first_seen",
    "flags", "id", "last_checked", "last_seen", "last_verified", "location",
    "match_reason", "posted_date", "posted_date_basis", "salary", "sources",
    "status", "tier", "title", "url", "urls", "verification_note",
    "missing_since", "employer_posted_date", "exclusion_reason", "status_before_exclusion",
})


def public_jobs(jobs):
    """Export only listing metadata; never carry private tracking fields forward."""
    return [{key: value for key, value in job.items() if key in PUBLIC_JOB_FIELDS}
            for job in jobs]


def apply_scope(jobs, config, now):
    """Reapply title exclusions to stored listings without deleting their history."""
    for job in jobs:
        if category(job["title"], config) is None:
            if job["status"] != "Excluded":
                job["status_before_exclusion"] = job["status"]
            job["status"] = "Excluded"
            job["exclusion_reason"] = "Outside configured job families or excluded senior, student, clinical or pharmacy role"
            continue
        if job["status"] == "Excluded":
            job["status"] = job.pop("status_before_exclusion", "Unverified")
            job.pop("exclusion_reason", None)
        deadline = date_string(job.get("deadline"))
        if deadline and deadline < now[:10]:
            job["status"] = "Closed"
            job["verification_note"] = "Previously observed employer deadline has passed"
        elif job["status"] != "Closed" and datetime.fromisoformat(job["last_seen"]) < datetime.fromisoformat(now) - timedelta(days=config["stale_after_days"]):
            job["status"] = "Stale — recheck"
    return jobs
