# Validation record

## October 23, 2026 maintenance

- Started from commit `22964e7b697d09bf8fcf3f09ae5d3f7de74b335c`, preserving the combined newest-first list, posting ages, Apply buttons, and fast render-only code updates.
- 35 local Python tests pass, including public-data filtering, stored-title exclusions, document versus medical imaging, remote/bilingual uncertainty, deadline expiry, URL-change verification invalidation, missing-page recovery, sorting and source timestamps.
- Reviewed GitHub run `39847436362`: collection succeeded; publishing failed because main had changed. The subsequent rebase fix and successful render-only run `39848226337` were confirmed.
- The stored dataset already contained 242 records after live GitHub collection. Counts and current source status are shown in the generated pages.
- Public content was checked for identifying details and personal tracking data before publication. No résumé is included.

## Scope of evidence

Local tests use controlled fixtures. Live source availability and automated posting verification are separately reported in Actions, source health, and each listing's check dates. A successful run is not complete market coverage or a personal qualification assessment.

No real-browser visual test has been completed. The initial viewer passed a DOM harness; later presentation improvements are preserved. LinkedIn may ignore remote filtering. Source dates and salaries may be wrong; check the application page.

The first dataset began with a six-week, 80-result discovery sample. Later GitHub runs expanded it. Daily searches overlap seven days; manual backfill searches six weeks. The first scheduled run after these changes still needs to occur before daily scheduling can be called proven.
