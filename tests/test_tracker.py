import json
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from tracker.core import atomic_json, assess, canonical, identity, merge, public_jobs
from tracker.sources import classify_page
from tracker.render import render

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text())
NOW = "2026-10-22T12:00:00-04:00"


def raw(**kwargs):
    return {"title": "Administrative Assistant", "company": "Test Employer", "location": "Mississauga, ON, Canada", "job_url": "https://example.org/jobs/123", "description": "Full-time permanent. Records and customer service.", "site": "test", **kwargs}


class MatchingTests(unittest.TestCase):
    def test_pharmacy_excluded(self):
        self.assertIsNone(assess(raw(title="Pharmacy Administrative Assistant"), CONFIG))

    def test_internship_excluded(self):
        self.assertIsNone(assess(raw(title="Communications Intern"), CONFIG))

    def test_noncanadian_remote_excluded(self):
        self.assertIsNone(assess(raw(location="United States", is_remote=True), CONFIG))

    def test_remote_eligibility_never_assumed(self):
        result = assess(raw(location="Ontario, Canada", is_remote=True), CONFIG)
        self.assertTrue(any("Ontario eligibility" in f for f in result["flags"]))

    def test_casual_overrides_fulltime_label(self):
        self.assertEqual(assess(raw(job_type="fulltime", description="Casual with an opportunity to transition to full-time"), CONFIG)["tier"], "Fallback")

    def test_unknown_pay_retained(self):
        self.assertIn("Not disclosed", assess(raw(), CONFIG)["salary"])

    def test_commute_not_assumed(self):
        self.assertTrue(any("Commute review" in f for f in assess(raw(location="Milton, ON"), CONFIG)["flags"]))

    def test_internal_only_excluded(self):
        self.assertIsNone(assess(raw(description="Internal applicants only"), CONFIG))


class HistoryTests(unittest.TestCase):
    def test_tracking_url_and_apply_path_dedupe(self):
        base = "https://jobs.lever.co/acme/64a5cbe2-cd46-47d1-a92f-fa6376bf5809"
        self.assertEqual(identity(base), identity(base + "/?utm_source=indeed"))
        self.assertEqual(identity(base), identity(base + "/application"))

    def test_distinct_requisitions_preserved(self):
        self.assertEqual(len(merge([], [raw(job_url="https://example.org/1"), raw(job_url="https://example.org/2")], CONFIG, NOW)), 2)

    def test_bridge_duplicate_urls(self):
        jobs = merge([], [raw(job_url="https://example.org/1"), raw(job_url="https://indeed.com/viewjob?jk=2")], CONFIG, NOW)
        merged = merge(jobs, [raw(job_url="https://indeed.com/viewjob?jk=2", job_url_direct="https://example.org/1")], CONFIG, NOW)
        self.assertEqual(len(merged), 1)

    def test_source_outage_preserves_records(self):
        initial = merge([], [raw()], CONFIG, NOW)
        self.assertEqual(merge(initial, [], CONFIG, NOW), initial)

    def test_stale_is_not_closed(self):
        initial = merge([], [raw()], CONFIG, "2026-10-01T12:00:00-04:00")
        self.assertEqual(merge(initial, [], CONFIG, NOW)[0]["status"], "Stale — recheck")

    def test_first_seen_preserved(self):
        initial = merge([], [raw()], CONFIG, NOW)
        later = merge(initial, [raw()], CONFIG, "2026-10-23T12:00:00-04:00")
        self.assertEqual(later[0]["first_seen"], NOW)


class VerificationTests(unittest.TestCase):
    def test_http200_unavailable_is_not_verified(self):
        self.assertEqual(classify_page(200, "<h1>Site Unavailable</h1>", "Administrative Assistant", NOW)[0], "Unverified")

    def test_homepage_redirect_not_verified(self):
        self.assertEqual(classify_page(200, "<h1>Careers</h1><a href='/'>Apply</a>", "Administrative Assistant", NOW)[0], "Unverified")

    def test_explicit_closure(self):
        self.assertEqual(classify_page(200, "This job is no longer available", "Role", NOW)[0], "Closed")

    def test_expired_structured_posting(self):
        content = '<script type="application/ld+json">' + json.dumps({"@type": "JobPosting", "title": "Role", "validThrough": "2026-10-01"}) + '</script>'
        self.assertEqual(classify_page(200, content, "Role", NOW)[0], "Closed")

    def test_matching_posting_with_apply(self):
        content = "<h1>Administrative Assistant</h1><p>" + "Full-time office duties. " * 70 + "</p><a href='/apply'>Apply</a>"
        self.assertEqual(classify_page(200, content, "Administrative Assistant", NOW)[0], "Posting verified")

    def test_unsafe_url_rejected(self):
        self.assertEqual(canonical("javascript:alert(1)"), "")


class IntegrationTests(unittest.TestCase):
    def test_render_escapes_remote_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker").mkdir()
            (root / "tracker/viewer.html").write_text('<script type="application/json">__JOBS__</script>')
            rows = merge([], [raw(company='</script><script>alert(1)</script>')], CONFIG, NOW)
            render(root, rows, [], NOW)
            self.assertNotIn('<script>alert(1)', (root / "index.html").read_text())
            self.assertIn('\\u003c', (root / "index.html").read_text())

    def test_total_outage_preserves_job_file(self):
        from tracker import update
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "tracker").mkdir()
            (root / "tracker/viewer.html").write_text('__JOBS__')
            (root / "config.json").write_text(json.dumps(CONFIG))
            records = merge([], [raw()], CONFIG, NOW)
            atomic_json(root / "data/jobs.json", records)
            before = (root / "data/jobs.json").read_bytes()
            with patch.object(update, 'ROOT', root), patch.object(update, 'discover', return_value=([], [{'source':'test','status':'failed','count':0}])), patch('sys.argv', ['update']):
                self.assertEqual(update.main(), 1)
            self.assertEqual(before, (root / "data/jobs.json").read_bytes())

    def test_private_fields_discarded_from_render_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker").mkdir()
            (root / "tracker/viewer.html").write_text('__JOBS__')
            records = merge([], [raw()], CONFIG, NOW)
            records[0].update(notes="PRIVATE_NOTE_SENTINEL", application_status="PRIVATE_STATUS_SENTINEL", candidate_name="PRIVATE_NAME_SENTINEL")
            render(root, records, [], NOW)
            exported = json.dumps(public_jobs(records))
            self.assertNotIn("PRIVATE_", exported)
            self.assertNotIn("PRIVATE_", (root / "index.html").read_text())
            self.assertIn("Administrative Assistant", exported)

    def test_render_only_scrubs_private_fields_from_disk(self):
        from tracker import update
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "tracker").mkdir()
            (root / "tracker/viewer.html").write_text('__JOBS__')
            (root / "config.json").write_text(json.dumps(CONFIG))
            records = merge([], [raw()], CONFIG, NOW)
            records[0]['notes'] = "PRIVATE_NOTE_SENTINEL"
            (root / "data/jobs.json").write_text(json.dumps(records))
            with patch.object(update, 'ROOT', root), patch('sys.argv', ['update','--render-only']):
                self.assertEqual(update.main(), 0)
            self.assertNotIn("PRIVATE_", (root / "data/jobs.json").read_text())


if __name__ == "__main__":
    unittest.main()
