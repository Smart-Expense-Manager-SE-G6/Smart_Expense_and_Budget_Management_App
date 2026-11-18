# Code and Branch Coverage Report

## Objective and scope
Measure backend statement and branch coverage with coverage.py and identify frontend coverage availability.

## Execution status

Coverage measurement was NOT RUN. Python is unavailable (`py -3 -m coverage --version` returned “No installed Python found”), so no numeric coverage percentage, module result, covered line list, or missed branch list is claimed. Frontend coverage is unmeasured because `frontend/package.json` has no coverage script/tool.

## Expected reproduction commands

```powershell
Set-Location backend
py -3 -m coverage run --branch manage.py test
py -3 -m coverage report
py -3 -m coverage json -o ..\docs\testing\reports\coverage\coverage.json
py -3 -m coverage html -d ..\docs\testing\reports\coverage\html
```

## Artifacts

`docs/testing/reports/coverage/coverage.json` and `docs/testing/reports/coverage/index.html` state that measurement was not run; they are status artifacts, not fabricated coverage output. No HTML coverage tree could be produced without coverage.py.

## Limitations

No branch, statement, function, condition, or module percentages are available from this environment. Frontend coverage remains unmeasured.
