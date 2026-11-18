# White-Box Test Report

## Objective and scope
Analyze statement, branch, condition, function, decision-path, exception, and uncovered-code evidence from actual instrumentation.

## Measurement result

No white-box measurement was possible. coverage.py could not be invoked because Python is not installed. Therefore numeric statement/branch/function/condition coverage and missing-line/missing-branch lists are unavailable. Manual source inspection was not converted into coverage claims.

## Executed evidence

The only executed code tests were two frontend Node tests. They provide pass/fail assertions but no configured statement, branch, condition, or function instrumentation.

## Exact commands

```powershell
npm.cmd test --prefix frontend
py -3 -m coverage run --branch backend/manage.py test
py -3 -m coverage report
```

The first command passed 2/2; the coverage commands were NOT RUN because the interpreter was unavailable. Exception paths and decision paths are consequently unmeasured.
