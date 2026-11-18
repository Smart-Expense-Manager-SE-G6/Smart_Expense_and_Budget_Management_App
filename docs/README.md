# Project documentation

Everything the team wrote about the system. The approved course documents (SRS, SASD, test plan and others)
are in [`../deliverables/`](../deliverables/README.md).

## Requirements and traceability
- [`requirements/rtm.md`](requirements/rtm.md): Requirements Traceability Matrix, every FR and NFR mapped to design, code and test cases
- [`requirements/rtm-release-audit.md`](requirements/rtm-release-audit.md): release check that every RTM reference points to a real file
- [`requirements/deviations.md`](requirements/deviations.md): every place the system differs from the course documents, and why

## Design
- [`design/data-dictionary.md`](design/data-dictionary.md): database models and fields
- [`design/adr/`](design/adr/): architecture decision records
  - [0001 Authentication with server-side sessions](design/adr/0001-authentication-sessions.md)
  - [0002 Report date-range cap](design/adr/0002-report-date-range-cap.md)
  - [0003 Statement and CSV import format](design/adr/0003-statement-and-csv-import-format.md)
  - [0004 Anomaly detection](design/adr/0004-anomaly-detection.md)

## Testing (STP deliverables)
- [`testing/unit-test-report.md`](testing/unit-test-report.md): Unit Test Report, 366 backend tests by module and file
- [`testing/system-validation-report.md`](testing/system-validation-report.md): System Validation Report, end-to-end, deployment and requirement validation
- [`testing/code-coverage-report.md`](testing/code-coverage-report.md): Code (line) Coverage Report, by module and file
- [`testing/branch-coverage-report.md`](testing/branch-coverage-report.md): Branch Coverage Report, with every branch not taken
- [`testing/test-summary.md`](testing/test-summary.md): Test Summary Report with the STP section 14 metrics
- [`testing/test-cases.md`](testing/test-cases.md): test-case catalogue with results
- [`testing/defect-log.md`](testing/defect-log.md): defects found, severity and aging
- [`testing/execution-evidence.md`](testing/execution-evidence.md): where each suite runs and its CI run links
- [`testing/security-report.md`](testing/security-report.md): STP 5.1 security checks and results
- [`testing/accessibility-audit.md`](testing/accessibility-audit.md): accessibility and responsive audit (NFR7, NFR8)
- [`testing/uat-record.md`](testing/uat-record.md): user acceptance testing record

## Operations
- [`operations/deployment.md`](operations/deployment.md): production stack, local demo and CI/CD delivery
- [`operations/recovery-runbook.md`](operations/recovery-runbook.md): backups, off-site copies and disaster recovery

## Users and release
- [`user/user-guide.md`](user/user-guide.md): how to use the app
- [`user/screenshots/`](user/screenshots/README.md): release screenshot checklist
- [`release/RELEASE_NOTES.md`](release/RELEASE_NOTES.md): release notes for version 1.0
