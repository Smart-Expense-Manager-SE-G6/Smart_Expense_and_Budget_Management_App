import os
from pathlib import Path
from uuid import uuid4

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5174").rstrip("/")
ARTIFACTS = Path(__file__).parent / "artifacts"


@pytest.fixture
def driver(tmp_path):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_experimental_option("prefs", {"download.default_directory": str(tmp_path)})
    instance = webdriver.Chrome(options=options)
    instance.set_window_size(1280, 900)
    yield instance
    instance.quit()


@pytest.fixture
def unique_user():
    return {"first": "E2E", "last": "Tester", "email": f"e2e.{uuid4().hex[:8]}@example.com", "password": "E2eStrongPassword!42"}


def wait_for_text(driver, text, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))


def field(driver, label):
    label_node = driver.find_element(By.XPATH, f"//label[normalize-space()='{label}']")
    return driver.find_element(By.ID, label_node.get_attribute("for"))


def click_button(driver, text):
    return WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f"//button[normalize-space()='{text}']"))).click()


def register(driver, user):
    driver.get(f"{BASE_URL}/register")
    for label, value in (("First name", user["first"]), ("Last name", user["last"]), ("Email", user["email"]), ("Password", user["password"])):
        field(driver, label).send_keys(value)
    click_button(driver, "Create account")
    WebDriverWait(driver, 10).until(lambda current: "/register" not in current.current_url)


def login(driver, user):
    driver.get(f"{BASE_URL}/login")
    field(driver, "Email").send_keys(user["email"])
    field(driver, "Password").send_keys(user["password"])
    click_button(driver, "Sign in")
    WebDriverWait(driver, 10).until(lambda current: "/login" not in current.current_url)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    yield
    if getattr(request.node, "rep_call", None) and request.node.rep_call.failed and hasattr(request.node, "_driver"):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        request.node._driver.save_screenshot(str(ARTIFACTS / f"{request.node.name}.png"))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, "rep_" + report.when, report)

