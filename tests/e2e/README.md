# Selenium end-to-end tests

The suite uses Selenium 4 with Chrome headless and Selenium Manager. Every test creates an isolated user and uses explicit waits; it does not use `time.sleep()`.

```powershell
docker compose up -d --build
python -m pip install -r tests/e2e/requirements.txt
pytest tests/e2e --html=tests/e2e/artifacts/report.html --self-contained-html
```

Set `E2E_BASE_URL` when the frontend is not at `http://localhost:5174`. Failed tests save screenshots in `tests/e2e/artifacts/`.
