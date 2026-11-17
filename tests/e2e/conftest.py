"""
Shared setup for the Selenium end-to-end suite (S3-12, issue #74).

Every lookup waits (React renders after the page loads, and Vite compiles the app on
the first visit), every test registers its own user, and a screenshot is saved for any
failing test before its browser is closed.
"""

import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5174").rstrip("/")
TIMEOUT = int(os.getenv("E2E_TIMEOUT", "20"))
ARTIFACTS = Path(__file__).parent / "artifacts"
PASSWORD = "E2eStrongPassword!42"


# ---------------------------------------------------------------- pytest plumbing

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Keep each phase's TestReport on the test item, so fixtures can see if the test failed."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, "rep_" + report.when, report)


def _new_browser(download_dir):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
    })
    browser = webdriver.Chrome(options=options)
    browser.execute_cdp_cmd("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(download_dir)})
    return browser


@pytest.fixture
def browsers(request, tmp_path):
    """A factory for browsers: browsers() opens one; a test may open several (e.g. owner and member)."""
    opened = []

    def open_browser():
        download_dir = tmp_path / f"downloads{len(opened)}"
        download_dir.mkdir()
        browser = _new_browser(download_dir)
        browser.download_dir = download_dir
        opened.append(browser)
        return browser

    yield open_browser

    report = getattr(request.node, "rep_call", None)
    for index, browser in enumerate(opened):
        try:
            if report is not None and report.failed:  # screenshot BEFORE the browser is closed
                ARTIFACTS.mkdir(parents=True, exist_ok=True)
                browser.save_screenshot(str(ARTIFACTS / f"{request.node.name}-{index}.png"))
        finally:
            browser.quit()


@pytest.fixture
def driver(browsers):
    return browsers()


@pytest.fixture
def user():
    return {"first": "Eve", "last": "Tester", "email": f"e2e.{uuid4().hex[:10]}@example.com", "password": PASSWORD}


# ---------------------------------------------------------------- page helpers

def wait(driver, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout)


def visible(driver, by, selector):
    return wait(driver).until(EC.visibility_of_element_located((by, selector)))


def wait_for_text(driver, text):
    wait(driver).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))


def wait_for_text_gone(driver, text):
    wait(driver).until(lambda d: text not in d.find_element(By.TAG_NAME, "body").text)


def field(driver, label, scope="//"):
    """The input/select/textarea whose <label> has exactly this text (our FormField always pairs them)."""
    lab = wait(driver).until(EC.presence_of_element_located((By.XPATH, f"{scope}label[normalize-space()='{label}']")))
    return visible(driver, By.ID, lab.get_attribute("for"))


def set_value(driver, element, value):
    """Set a value the way a user would, so React sees it (also works for <input type=date>)."""
    driver.execute_script(
        "const [el, v] = arguments;"
        "const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value').set;"
        "setter.call(el, v);"
        "el.dispatchEvent(new Event('input', {bubbles: true}));"
        "el.dispatchEvent(new Event('change', {bubbles: true}));",
        element, value,
    )


def type_into(driver, label, value, scope="//"):
    element = field(driver, label, scope)
    element.clear()
    element.send_keys(value)
    return element


def choose(driver, label, visible_text, scope="//"):
    Select(field(driver, label, scope)).select_by_visible_text(visible_text)


def button(driver, text, scope="//"):
    return wait(driver).until(EC.element_to_be_clickable((By.XPATH, f"{scope}button[normalize-space()='{text}']")))


def by_label(driver, aria_label):
    return wait(driver).until(EC.element_to_be_clickable((By.XPATH, f"//*[@aria-label='{aria_label}']")))


DIALOG = "//dialog[@open]//"


def open_dialog(driver):
    return visible(driver, By.CSS_SELECTOR, "dialog[open]")


def wait_dialog_closed(driver):
    wait(driver).until(lambda d: not d.find_elements(By.CSS_SELECTOR, "dialog[open]"))


# ---------------------------------------------------------------- journeys used by many tests

def register(driver, user):
    driver.get(f"{BASE_URL}/register")
    type_into(driver, "First name", user["first"])
    type_into(driver, "Last name", user["last"])
    type_into(driver, "Email", user["email"])
    type_into(driver, "Password", user["password"])
    button(driver, "Create account").click()
    wait(driver).until(lambda d: d.current_url.rstrip("/") == BASE_URL)


def login(driver, user):
    driver.get(f"{BASE_URL}/login")
    type_into(driver, "Email", user["email"])
    type_into(driver, "Password", user["password"])
    button(driver, "Sign in").click()
    wait(driver).until(lambda d: d.current_url.rstrip("/") == BASE_URL)


def add_expense(driver, description, amount, category="Food", merchant="", notes="", receipt=None):
    driver.get(f"{BASE_URL}/expenses")
    button(driver, "Add expense").click()
    open_dialog(driver)
    type_into(driver, "Amount", amount, DIALOG)
    choose(driver, "Category", category, DIALOG)
    set_value(driver, field(driver, "Date", DIALOG), date.today().isoformat())
    type_into(driver, "Description", description, DIALOG)
    if merchant:
        type_into(driver, "Merchant", merchant, DIALOG)
    if notes:
        type_into(driver, "Notes", notes, DIALOG)
    if receipt:
        field(driver, "Receipt (optional)", DIALOG).send_keys(str(receipt))
    button(driver, "Add expense", DIALOG).click()
    wait_dialog_closed(driver)
    wait_for_text(driver, description)


def create_budget(driver, name, limit, category="Food"):
    driver.get(f"{BASE_URL}/budgets")
    button(driver, "New budget").click()
    open_dialog(driver)
    type_into(driver, "Budget name", name, DIALOG)
    choose(driver, "Applies to", category, DIALOG)
    type_into(driver, "Limit", limit, DIALOG)
    button(driver, "Create budget", DIALOG).click()
    wait_dialog_closed(driver)
    wait_for_text(driver, name)
