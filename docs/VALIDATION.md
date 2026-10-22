# Validation record — October 22, 2026

## Completed

- Installed and imported `python-jobspy==1.4.0` under Python 3.12.
- Four live searches against Indeed and LinkedIn returned 80 results (10 per board per search), with descriptions and posting dates. 35 included direct employer links. 36 supplied salary fields. These counts are discovery results, not verified vacancies.
- The oldest source-reported posting date was September 10, 2026, supporting the six-week initial import.
- Imported that snapshot into persistent JSON, filtered it to 65 leads, categorized and rendered the results.
- Final initial breakdown: 41 priority-employment leads, 10 needing additional review, 14 fallback-employment leads. These categories do not certify eligibility.
- Directly checked three posting pages: Stelumar Office Administrative Assistant, OPS Records File Clerk (249646), City of Toronto Revenue Clerk 4 (63641). All other initial records remain explicitly unverified.
- Automated Python tests passed, covering duplicate URLs and bridges, distinct requisitions, stale history, total-source-outage preservation, public-field privacy filtering, role/location exclusions, misleading employment labels, unavailable pages, expired deadlines, and HTML/script escaping.
- Python compilation passed. Workflow YAML parsed; schedule, manual dispatch and write permission checked.
- Searchable HTML viewer logic passed a Node DOM harness: initial list, verified-only filter, fallback filter, text search and no-results state.
- Individual source retrieval tests succeeded for City of Mississauga HTML and William Osler's SmartRecruiters endpoint. These were source retrieval tests, not complete reviews of every listing.

## Not completed / limits

- Expanded 10-query backfill was interrupted after outbound network/proxy blocks. No claim of expanded coverage is made; the successful 80-result snapshot is the source of the initial 65-lead list.
- Full GitHub-hosted workflow execution has **not** been tested. See Actions for upload and execution status.
- Browser rendering/screenshot test was unavailable because Chromium download failed. The viewer was checked for functionality with a DOM harness, not visually in a real browser.
- LinkedIn warned that the remote parameter was unsupported and ignored. Remote claims must be independently reviewed for Ontario eligibility.
- Automated matching is conservative keyword screening with uncertainty flags, not an AI assessment of every requirement.
- JobSpy direct/employer dates and salaries can be inaccurate or missing; displayed provenance and verification labels must be retained.

## Next verification after upload

1. Run the GitHub Actions workflow manually with backfill enabled.
2. Inspect the logs, committed `data/health.json` and `docs/SOURCES.md`.
3. Confirm generated listings are committed with listing metadata only.
4. Review a sample of new priority, review, fallback and remote leads.
5. Confirm the next scheduled run executes. Do not equate a configured cron with proven daily execution.
