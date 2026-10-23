import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker.core import apply_scope, assess, merge
from tracker.render import render, age_text
from tracker.sources import verify
from test_tracker import CONFIG, NOW, raw


class ScopeTests(unittest.TestCase):
    def test_irrelevant_roles_excluded(self):
        for title in ['Analyst, Enterprise Data and Records co-op', 'Chief Administrative Officer',
                      'Senior Administrative Assistant', 'Modality Supervisor - MRI Diagnostic Imaging',
                      'Registered Technologist - Mammography Screening, Diagnostic Imaging',
                      'Manager, AMS/SAP Platform Administration and Support']:
            with self.subTest(title=title):
                self.assertIsNone(assess(raw(title=title), CONFIG))

    def test_document_and_hospital_clerical_roles_retained(self):
        for title in ['Document Imaging Specialist', 'Nursing Clerk', 'Administrative Assistant', 'Executive Assistant to Chief of Staff']:
            with self.subTest(title=title):
                self.assertIsNotNone(assess(raw(title=title), CONFIG))

    def test_title_exclusions_apply_to_old_data_without_deletion(self):
        jobs = merge([], [raw()], CONFIG, NOW)
        jobs[0]['title'] = 'Senior Administrative Assistant'
        filtered = apply_scope(jobs, CONFIG, NOW)
        self.assertEqual(filtered[0]['status'], 'Excluded')
        self.assertEqual(len(filtered), 1)
        filtered[0]['title'] = 'Administrative Assistant'
        self.assertEqual(apply_scope(filtered, CONFIG, NOW)[0]['status'], 'Unverified')

    def test_remote_and_bilingual_do_not_get_priority_automatically(self):
        for record in [raw(location='Ontario, Canada', is_remote=True), raw(title='Bilingual Administrative Assistant')]:
            self.assertEqual(assess(record, CONFIG)['tier'], 'Review')

    def test_deadline_closes_without_waiting_for_network_check(self):
        jobs = merge([], [raw()], CONFIG, NOW)
        jobs[0].update(deadline='2026-10-21', status='Posting verified')
        self.assertEqual(apply_scope(jobs, CONFIG, NOW)[0]['status'], 'Closed')

    def test_us_location_with_same_city_name_rejected(self):
        self.assertIsNone(assess(raw(location='Concord, CA, United States'), CONFIG))


class VerificationHistoryTests(unittest.TestCase):
    def test_changed_url_requires_new_verification(self):
        jobs = merge([], [raw()], CONFIG, NOW)
        jobs[0].update(status='Posting verified', last_checked=NOW, last_verified=NOW)
        jobs = merge(jobs, [raw(job_url_direct='https://employer.example/new-posting')], CONFIG, NOW)
        self.assertEqual(jobs[0]['status'], 'Unverified')
        self.assertNotIn('last_checked', jobs[0])

    def test_missing_then_recovered_then_missing_does_not_close(self):
        jobs = merge([], [raw()], CONFIG, NOW)
        jobs[0]['missing_since'] = '2026-10-01'
        with patch('tracker.sources.session') as session:
            session.return_value.get.return_value.status_code = 200
            session.return_value.get.return_value.text = '<h1>Careers</h1>'
            verify(jobs, CONFIG, NOW)
            self.assertNotIn('missing_since', jobs[0])
            session.return_value.get.return_value.status_code = 404
            verify(jobs, CONFIG, '2026-10-30T12:00:00-04:00')
        self.assertEqual(jobs[0]['status'], 'Unverified')

    def test_excluded_jobs_do_not_consume_verification_budget(self):
        jobs = merge([], [raw()], CONFIG, NOW)
        jobs[0]['status'] = 'Excluded'
        with patch('tracker.sources.session') as session:
            self.assertEqual(verify(jobs, CONFIG, NOW), 0)
            session.return_value.get.assert_not_called()


class DisplayTests(unittest.TestCase):
    def test_render_preserves_chronological_order_and_real_collection_time(self):
        jobs = merge([], [raw(job_url='https://example.org/old', date_posted='2026-10-01'),
                          raw(job_url='https://example.org/new', date_posted='2026-10-20')], CONFIG, NOW)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tracker').mkdir()
            (root / 'tracker/viewer.html').write_text('__JOBS__')
            render(root, jobs, [{'source':'Test', 'status':'ok','checked_at':NOW}], '2026-10-23T12:00:00-04:00')
            displayed = json.loads((root / 'index.html').read_text())
            self.assertEqual(displayed[0]['posted_date'], '2026-10-20')
            source = (root / 'docs/SOURCES.md').read_text()
            self.assertIn('Last collection attempt: ' + NOW, source)
            self.assertIn('Apply-blue', (root / 'docs/ALL_JOBS.md').read_text())

    def test_age_calculation(self):
        self.assertEqual(age_text('2026-10-22', date(2026,10,23)), '1d')
        self.assertEqual(age_text(None, date(2026,10,23)), '—')
