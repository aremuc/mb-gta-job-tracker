# Setup and maintenance

## First setup

The public repository is `aremuc/mb-gta-job-tracker`. Anyone can browse the Markdown listings without an account. Download `index.html` to use the searchable viewer locally.

The workflow collects jobs daily at 13:37 UTC. Ordinary code pushes test and regenerate existing listings quickly; they do not search for new jobs. Add `[refresh-jobs]` to a code-change commit message to explicitly request collection on that push. To run a six-week search manually, open **Actions → Refresh job tracker → Run workflow** and select backfill. Inspect the run and `docs/SOURCES.md`; a green run with degraded sources is not full coverage.

## Public data and privacy

This repository is a public vacancy list. Do not commit résumés, names of job seekers, contact details, application activity, personal notes, or credentials. Git history can retain deleted information.

Application tracking belongs in a separate private spreadsheet or document. The publisher exports an explicit set of job-listing fields and discards extra fields such as notes and application status. That protects against accidental carryover; it cannot detect personal details typed into a listing's title or other allowed field. Review edits before committing.

## Run locally (Python 3.12)

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python -m tracker.update --backfill
```

Normal daily equivalent: `python -m tracker.update`.
Regenerate views without requests: `python -m tracker.update --render-only`.

## Preferences

Edit `config.json`. Search queries are discovery hints, not eligibility decisions.
The initial backfill uses 42 days; daily searches overlap seven days. Results are capped per board per query.
Expand job families and locations through the configuration; keep a manageable query budget.
No age filter or contact details are required. The original résumé is deliberately not included.
Compensation is preferred above minimum wage, but no hard threshold is guessed. Unspecified salaries remain in the list.

## Verification and history

- `Posting verified`: matching employer/job-board posting structure or matching title plus substantive description and Apply control.
- `Unverified`: new lead, blocked page, unsupported rendering, or incomplete evidence.
- `Stale — recheck`: not rediscovered for 14 days. It is not automatically declared closed.
- `Closed`: explicit closure, a recognized expired deadline, or repeated 404/410 on separate days without an intervening successful page response.
- `Excluded`: outside the configured title rules. Preserved in `docs/EXCLUDED.md`, omitted from active views and network verification. Rules are reapplied to existing data too.
- Verification is capped at 60 pages per run; oldest checks go first and repeat after seven days.
- Check dates are visible. A verified page does not guarantee a current vacancy, complete eligibility or employer responsiveness.
- Missing from a paginated/search-limited feed is never proof of closure.
- Future source failures retain previous jobs. Total collection failure exits nonzero and publishes health details.
- Duplicates merge by cleaned URL, employer IDs on supported hosts, and direct/source URL bridges. Different IDs remain separate to avoid deleting genuine vacancies; some cross-board duplicates can remain.

## Troubleshooting

**No new jobs:** read `docs/SOURCES.md`; distinguish a failed source from an empty query. Run a backfill after an outage longer than seven days.

**LinkedIn ignores remote:** expected warning in the tested JobSpy version. The tracker marks remote claims for review; never infer Ontario eligibility from a remote flag.

**Salary looks wrong:** source units can be incorrect. The tracker flags implausible annual values; consult the actual description.

**Push denied:** confirm Actions can write repository contents and that branch protection permits the bot. Do not remove protections blindly; use a PR-based publishing workflow if needed.

**Page layout changed:** that source is marked failed rather than returning an empty successful result. Update its adapter and run tests.

**Dependency updates:** top-level dependencies are in `requirements.txt`; `requirements-lock.txt` pins the versions used in the tested environment. Update deliberately in a virtual environment and repeat tests plus a small live query.

## Reading timestamps

The view-generation timestamp is separate from discovery and posting-check timestamps. A render-only run does not update source-check timestamps. “Priority” is an employment preference, not a promise of qualification. Remote and bilingual postings are flagged for individual review.

## Sources and attribution

Discovery uses [SpeedyApply JobSpy](https://github.com/speedyapply/JobSpy) and configured employer career pages.
The new code separates source health, history, matching and rendering. No proprietary résumé or personal identifiers are published.
Short evidence excerpts are retained for review; employer links remain authoritative.
