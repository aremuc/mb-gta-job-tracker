import html
import json
import re

from .core import public_jobs


def cell(s):
    return html.escape(str(s or "Unknown")).replace("|", "&#124;").replace("\n", " ").replace("[", "&#91;").replace("]", "&#93;")


def table(jobs):
    lines = ["| Role / employer | Location | Pay | Posted | Status | Apply |", "|---|---|---|---|---|---|"]
    for j in jobs:
        lines.append("| " + " | ".join([cell(j["title"]) + " — " + cell(j["company"]), cell(j["location"]), cell(j["salary"]), cell(j.get("posted_date")), cell(j["status"]), '<a href="' + html.escape(j["url"], quote=True) + '">View posting</a>']) + " |")
    return "\n".join(lines)


def render(root, jobs, health, now):
    jobs = public_jobs(jobs)
    active = [j for j in jobs if j["status"] != "Closed"]
    active.sort(key=lambda j: (j.get("posted_date") or "", j.get("first_seen") or ""), reverse=True)
    verified = [j for j in active if j["status"] == "Posting verified"]
    content = f"""# GTA Entry-Level Job Tracker

Paid opportunities in administration, records, legal support, communications, client services and community programs.
**Brampton · Mississauga · Toronto · GTA commute review · Ontario-eligible remote**

Permanent/full-time roles come first. Contracts, casual and part-time roles are separated as fallbacks. No pharmacy roles or internships.

**{len(active)} leads · {len(verified)} posting pages verified · updated {now}**

This is a research shortlist, not a guarantee of eligibility or an employer's hiring activity.
“Posting verified” means a matching posting page was successfully checked; read its requirements before applying.
Unverified and stale leads remain visible with explicit labels. Source-reported posting dates can differ from the employer's original date.

## Browse

- **[All jobs, newest first](docs/ALL_JOBS.md)** — one chronological list across all categories
- [Contract and other fallback roles](docs/FALLBACK.md)
- [Closed postings](docs/ARCHIVE.md)
- [Source health and coverage](docs/SOURCES.md)
- [Setup and maintenance](docs/MAINTENANCE.md)
- **Searchable viewer:** download `index.html` and open it in your browser. Search/filter locally; no hosting or account required. GitHub displays its source rather than running it.

## Verified priority leads

These have a checked posting page and a full-time/permanent signal. Requirements and commute still need review.

{table([j for j in verified if j['tier'] == 'Priority'][:15])}

## How this works

JobSpy searches Indeed and LinkedIn; selected employer feeds supplement discovery. The first import searches six weeks back.
Daily runs search the last seven days (overlap avoids gaps), retain history, and rotate through posting checks.
No applications are submitted. No résumé, phone number, email address or credentials are stored here.

Configure search terms and cities in `config.json`. Keep application activity and personal notes in a separate private document; never commit them here.
The schedule is configured for 13:37 UTC daily (9:37 a.m. Toronto during daylight saving, 8:37 a.m. in winter).
Actual execution can be delayed by GitHub. Check Actions and the source-health report; a schedule file alone is not proof a run succeeded.
"""
    (root / "README.md").write_text(content, encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    for label, subset in [("ALL_JOBS", active), ("FALLBACK", [j for j in active if j["tier"] == "Fallback"]), ("ARCHIVE", [j for j in jobs if j["status"] == "Closed"])]:
        intro = f"# {label.replace('_', ' ').title()}\n\n[Home](../README.md) · Updated {now}\n\n"
        if label == "ALL_JOBS":
            intro += "All active jobs in one list, newest posting date first. Posting dates are source-reported and may be inaccurate; undated jobs appear last.\n\n" + table(subset) + "\n"
        else:
            intro += table(subset) + "\n"
        (docs / f"{label}.md").write_text(intro, encoding="utf-8")
    source = f"# Source health\n\n[Home](../README.md) · Last attempt: {now}\n\n"
    source += "| Source | Result | Rows before filtering | Details |\n|---|---|---:|---|\n"
    for h in health:
        source += f"| {cell(h['source'])} | {cell(h['status'])} | {h.get('count', 0)} | {cell(h.get('error') or json.dumps({'errors': h.get('errors', {}), 'warnings': h.get('warnings', {})}))} |\n"
    source += """
## Coverage limits

- Automated: configured JobSpy searches (Indeed and LinkedIn), SmartRecruiters employers, and selected SuccessFactors portals.
- JobSpy is not a complete search index. Each query is capped; broaden terms or increase results when needed.
- LinkedIn may ignore remote filtering. Every remote lead requires checking Ontario eligibility in the description.
- No automatic claim of transit accessibility, sponsorship eligibility, French proficiency or salary above minimum wage.
- Planned/manual only: Job Bank, CharityVillage, Peel, Sheridan, Brampton, Trillium, Randstad. These are **not** advertised as daily automated coverage in this version.
- University of Toronto may block the Python client; the health table reports actual results.
- No paid API/proxy or LLM subscription is required. Check GitHub Actions usage and source health regularly.
- Feed failures preserve the previous data. Missing from search results does not prove a vacancy closed.
- Rechecks rotate within a bounded budget. See each listing's last checked/verified dates in the viewer.
"""
    (docs / "SOURCES.md").write_text(source, encoding="utf-8")
    # Escape script terminators; remote strings are inserted using DOM textContent only.
    payload = json.dumps(active, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = (root / "tracker" / "viewer.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(template.replace("__JOBS__", payload).replace("__UPDATED__", html.escape(now)), encoding="utf-8")

