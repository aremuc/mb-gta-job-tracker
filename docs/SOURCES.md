# Source health

[Home](../README.md) · Last collection attempt: 2026-10-26T15:31:52-04:00

Views generated: 2026-10-26T15:31:52-04:00. Rendering alone does not refresh source checks.

| Source | Result | Rows before filtering | Details |
|---|---|---:|---|
| JobSpy: administrative assistant / Brampton, ON | ok | 40 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| JobSpy: office coordinator / Mississauga, ON | degraded | 20 | {&quot;errors&quot;: {&quot;linkedin&quot;: &quot;response status code 429 (blocked: use a proxy)&quot;}, &quot;warnings&quot;: {}} |
| JobSpy: records clerk / Mississauga, ON | ok | 40 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| JobSpy: document management / Toronto, ON | degraded | 30 | {&quot;errors&quot;: {&quot;linkedin&quot;: &quot;response status code 429 (blocked: use a proxy)&quot;}, &quot;warnings&quot;: {}} |
| JobSpy: communications assistant / Toronto, ON | degraded | 4 | {&quot;errors&quot;: {&quot;linkedin&quot;: &quot;response status code 429 (blocked: use a proxy)&quot;}, &quot;warnings&quot;: {}} |
| JobSpy: legal assistant / Brampton, ON | ok | 40 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| JobSpy: program assistant / Toronto, ON | ok | 40 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| JobSpy: customer service representative / Mississauga, ON | ok | 40 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| JobSpy: client services representative / Ontario, Canada | ok | 29 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {&quot;linkedin&quot;: &#91;&quot;is_remote isn&#x27;t supported, ignoring it&quot;&#93;}} |
| JobSpy: administrative assistant / Ontario, Canada | degraded | 13 | {&quot;errors&quot;: {&quot;linkedin&quot;: &quot;response status code 429 (blocked: use a proxy)&quot;}, &quot;warnings&quot;: {&quot;linkedin&quot;: &#91;&quot;is_remote isn&#x27;t supported, ignoring it&quot;&#93;}} |
| SmartRecruiters: WilliamOslerHealthSystem1 | ok | 0 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| SmartRecruiters: HaltonHealthcare1 | ok | 4 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| City of Mississauga | ok | 0 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |
| University of Toronto | ok | 10 | {&quot;errors&quot;: {}, &quot;warnings&quot;: {}} |

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
