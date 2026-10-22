# Source health

[Home](../README.md) · Last attempt: 2026-10-22T16:04:21-04:00

| Source | Result | Rows before filtering | Details |
|---|---|---:|---|
| Initial four JobSpy queries: Indeed and LinkedIn | ok | 80 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {&quot;linkedin&quot;: &#91;&quot;Remote-only parameter ignored; description review required&quot;&#93;}} |
| Expanded six-week backfill | interrupted | 0 | Execution was interrupted after outbound network/proxy blocks. Initial 80-row snapshot retained; expanded coverage not claimed. |
| City of Mississauga (prior live test) | HTML retrieval tested | 20 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| William Osler SmartRecruiters (prior live test) | API retrieval tested | 74 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| University of Toronto Python fetch (prior live test) | failed | 0 | HTTP 200 with Site Unavailable body; browser/search retrieval worked separately. |

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
