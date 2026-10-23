"""Fetchers return records and health separately; an outage is never an empty feed."""
import json
import re
import time
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .core import category


def session():
    s = requests.Session()
    s.headers["User-Agent"] = "GTAJobTracker/1.0 (public job discovery; daily)"
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    return s


def discover(config, days):
    from jobspy import scrape_jobs
    rows, health = [], []
    for query in config["queries"]:
        started = time.monotonic()
        try:
            df = scrape_jobs(site_name=["indeed", "linkedin"], search_term=query["term"],
                             location=query["location"], distance=20,
                             is_remote=query.get("remote", False), results_wanted=config["results_per_board"],
                             hours_old=days * 24, country_indeed="Canada", fetch_description=True, verbose=1)
            items = json.loads(df.to_json(orient="records", date_format="iso"))
            rows.extend(items)
            errors, warnings = df.attrs.get("errors", {}), df.attrs.get("warnings", {})
            health.append({"source": "JobSpy: " + query["term"] + " / " + query["location"],
                           "status": "degraded" if errors else ("ok" if items else "empty — review"),
                           "count": len(items), "errors": errors, "warnings": warnings,
                           "seconds": round(time.monotonic() - started, 1)})
            print(f"Collected {len(items)} leads: {query['term']} / {query['location']}", flush=True)
        except Exception as exc:
            health.append({"source": "JobSpy: " + query["term"], "status": "failed", "error": str(exc)[:300], "count": 0})
        time.sleep(1)
    s = session()
    for company in config["smartrecruiters"]:
        try:
            collected, offset = [], 0
            while True:
                r = s.get(f"https://api.smartrecruiters.com/v1/companies/{company}/postings", params={"limit": 100, "offset": offset}, timeout=25)
                r.raise_for_status()
                payload = r.json()
                if "content" not in payload or "totalFound" not in payload:
                    raise ValueError("Posting API schema changed")
                for job in payload["content"]:
                    if not category(job["name"], config):
                        continue
                    detail = s.get(job["ref"], timeout=25)
                    detail.raise_for_status()
                    d = detail.json()
                    sections = d.get("jobAd", {}).get("sections", {})
                    text = "\n".join(BeautifulSoup(v.get("text", ""), "html.parser").get_text(" ", strip=True) for v in sections.values())
                    collected.append({"title": d["name"], "company": d.get("company", {}).get("name", company),
                                      "location": d["location"].get("fullLocation", d["location"].get("city", "")),
                                      "job_url": d.get("postingUrl") or "https://jobs.smartrecruiters.com/" + company + "/" + d["id"],
                                      "description": text, "job_type": d.get("typeOfEmployment", {}).get("label", ""),
                                      "is_remote": d["location"].get("remote", False),
                                      "date_posted": d.get("releasedDate"), "date_basis": "Employer release date", "site": "SmartRecruiters: " + company})
                offset += len(payload["content"])
                if offset >= payload["totalFound"] or not payload["content"]:
                    break
            rows.extend(collected)
            health.append({"source": "SmartRecruiters: " + company, "status": "ok", "count": len(collected)})
        except Exception as exc:
            health.append({"source": "SmartRecruiters: " + company, "status": "failed", "count": 0, "error": str(exc)[:300]})
    for board in config["html_boards"]:
        try:
            urls, collected = set(), []
            # SuccessFactors pages contain duplicate desktop/mobile links. Parse both pages.
            for page in range(0, 150, 50):
                base = board["url"]
                url = base if page == 0 else (base.rstrip("/") + f"/{page}/" if "?" not in base else base + f"&startrow={page}")
                r = s.get(url, timeout=25)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                links = soup.select("a.jobTitle-link")
                if not links and page == 0:
                    raise ValueError("No expected job markup; unavailable/changed page, not an empty feed")
                new = {urljoin(url, a["href"]): a.get_text(" ", strip=True) for a in links if a.get("href")}
                new = {u: t for u, t in new.items() if u not in urls}
                if not new:
                    break
                urls.update(new)
                for u, title in new.items():
                    if not category(title, config):
                        continue
                    d = s.get(u, timeout=25)
                    d.raise_for_status()
                    doc = BeautifulSoup(d.text, "html.parser")
                    body = doc.select_one(".jobdescription") or doc.select_one(".job") or doc
                    description = body.get_text(" ", strip=True)
                    location = board["location"]
                    structured = job_schema(doc)
                    if structured:
                        loc = structured[0].get("jobLocation", {})
                        loc = loc[0] if isinstance(loc, list) and loc else loc
                        address = loc.get("address", {}) if isinstance(loc, dict) else {}
                        if isinstance(address, dict) and address.get("addressLocality"):
                            location = ", ".join(str(address.get(k, "")) for k in ("addressLocality", "addressRegion", "addressCountry"))
                    elif "University of Toronto Mississauga (UTM)" in description:
                        location = "Mississauga, ON, Canada"
                    elif "University of Toronto Scarborough (UTSC)" in description:
                        location = "Scarborough, ON, Canada"
                    collected.append({"title": title, "company": board["name"], "location": location,
                                      "description": description, "job_url": u, "site": board["name"]})
            rows.extend(collected)
            health.append({"source": board["name"], "status": "ok", "count": len(collected)})
        except Exception as exc:
            health.append({"source": board["name"], "status": "failed", "count": 0, "error": str(exc)[:300]})
    return rows, health


def job_schema(soup):
    def visit(item):
        if isinstance(item, list):
            for child in item:
                yield from visit(child)
        elif isinstance(item, dict):
            if item.get("@type") == "JobPosting" or "JobPosting" in (item.get("@type") or []):
                yield item
            if "@graph" in item:
                yield from visit(item["@graph"])
    found = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            found.extend(visit(json.loads(tag.string or tag.get_text())))
        except (ValueError, TypeError):
            continue
    return found


def classify_page(status_code, content, title, now):
    """An HTTP success is insufficient. Only a matching posting plus Apply is verified."""
    if status_code in (404, 410):
        return "Missing", "Posting URL returned " + str(status_code), {}
    if status_code != 200:
        return "Unverified", "HTTP " + str(status_code), {}
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(" ", strip=True)
    if re.search(r"site unavailable|access denied|verify you are human|captcha|temporarily unavailable", text, re.I):
        return "Unverified", "Unavailable or blocked page", {}
    if re.search(r"this (?:job|position|posting) (?:is no longer available|has been closed|has expired)|no longer accepting applications", text, re.I):
        return "Closed", "Explicit closure message on posting page", {}
    def normalized(value):
        return re.sub(r"[^a-z0-9]", "", value.lower())
    title_key = normalized(title)
    for item in job_schema(soup):
        if normalized(item.get("title", "")) != title_key:
            continue
        deadline = str(item.get("validThrough", ""))[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline) and deadline < now[:10]:
            return "Closed", "Employer structured deadline passed", {"deadline": deadline}
        return "Posting verified", "Matching JobPosting structured data; availability still subject to employer changes", {"deadline": deadline or None, "employer_posted_date": str(item.get("datePosted", ""))[:10] or None}
    headings = [x.get_text(" ", strip=True) for x in soup.select("h1,h2,title")]
    matching = title_key and any(title_key in normalized(h) for h in headings)
    apply = any(re.search(r"\bapply\b", a.get_text(" ", strip=True), re.I) for a in soup.select("a[href],button"))
    if matching and apply and len(text) > 1000:
        # Restrict expiry extraction to explicit posting closing labels.
        match = re.search(r"Closing Date:\s*(\d{2}/\d{2}/\d{4})", text, re.I)
        if match:
            from datetime import datetime
            deadline = datetime.strptime(match[1], "%m/%d/%Y").date().isoformat()
            if deadline < now[:10]:
                return "Closed", "Employer closing date passed", {"deadline": deadline}
        return "Posting verified", "Matching title, substantive description and Apply control", {}
    return "Unverified", "Could not confirm a matching live posting and application route", {}


def verify(jobs, config, now):
    from datetime import datetime, timedelta
    s = session()
    due = [j for j in jobs if j.get("status") != "Excluded" and (not j.get("last_checked") or datetime.fromisoformat(j["last_checked"]) <= datetime.fromisoformat(now) - timedelta(days=config["verification_max_age_days"]))]
    due.sort(key=lambda j: (j.get("last_checked", ""), j["tier"] != "Priority", j["first_seen"]))
    for j in due[:config["verification_budget"]]:
        try:
            r = s.get(j["url"], timeout=20)
            status, note, fields = classify_page(r.status_code, r.text, j["title"], now)
            if status == "Missing":
                # Two missing responses on separate days required; outages never close jobs.
                previous = j.get("missing_since")
                j["missing_since"] = previous or now[:10]
                status = "Closed" if previous and previous < now[:10] else "Unverified"
            else:
                # A later real page response breaks a sequence of missing pages.
                if r.status_code == 200 and "blocked" not in note.lower():
                    j.pop("missing_since", None)
                if status == "Posting verified":
                    j["last_verified"] = now
            j.update(fields)
            # An inaccessible page doesn't undo confirmed closure.
            if j.get("status") != "Closed" or status == "Posting verified":
                j["status"] = status
            j["verification_note"] = note
        except requests.RequestException as exc:
            if j.get("status") != "Closed":
                j["status"] = "Unverified"
            j["verification_note"] = "Request failed: " + str(exc)[:140]
        j["last_checked"] = now
        print(f"Checked {j['id']}: {j['status']}", flush=True)
    return len(due[:config["verification_budget"]])
