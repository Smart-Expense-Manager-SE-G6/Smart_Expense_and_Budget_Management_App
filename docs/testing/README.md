# Testing documents (STP deliverables)

- [`test-summary.md`](test-summary.md): Test Summary Report, STP section 14 metrics
- [`test-cases.md`](test-cases.md): STP section 8 test-case catalogue with results
- [`defect-log.md`](defect-log.md): defects found, severity and aging
- [`execution-evidence.md`](execution-evidence.md): commands, workflows and CI run links
- [`security-report.md`](security-report.md): STP 5.1 security checks
- [`accessibility-audit.md`](accessibility-audit.md): accessibility and responsive audit
- [`uat-record.md`](uat-record.md): product-owner acceptance record

Every result is tied to a commit SHA and a GitHub Actions run URL, so it can be traced to the exact code that was tested.
The test code itself lives outside `docs/`: backend tests in each `backend/<app>/test*.py`, browser journeys in
[`tests/e2e/`](../../tests/e2e/README.md), the API collection in `tests/postman_collection.json`, and the
accessibility audit script in `tests/accessibility/`.
