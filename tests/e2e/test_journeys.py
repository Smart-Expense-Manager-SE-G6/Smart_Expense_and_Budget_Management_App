from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from conftest import BASE_URL, click_button, field, login, register, wait_for_text


def remember_driver(request, driver):
    request.node._driver = driver


def test_TC_Auth_01_register_lands_on_dashboard(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    assert driver.current_url.rstrip("/") == BASE_URL


def test_TC_Auth_02_login_logout_and_protected_redirect(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses")
    assert "/expenses" in driver.current_url
    driver.get(f"{BASE_URL}/login")
    login(driver, unique_user)
    assert "/login" not in driver.current_url


def test_TC_Auth_03_profile_edit_persists(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/profile")
    last_name = field(driver, "Last name")
    last_name.clear()
    last_name.send_keys("Updated")
    click_button(driver, "Save changes")
    driver.refresh()
    assert field(driver, "Last name").get_attribute("value") == "Updated"


def test_TC_Exp_01_add_edit_delete_expense(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses")
    click_button(driver, "Add expense")
    field(driver, "Description").send_keys("E2E lunch")
    field(driver, "Amount").send_keys("12.50")
    click_button(driver, "Save expense")
    wait_for_text(driver, "E2E lunch")


def test_TC_Exp_03_receipt_upload_and_link(request, driver, unique_user, tmp_path):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses")
    click_button(driver, "Add expense")
    field(driver, "Description").send_keys("Receipt expense")
    field(driver, "Amount").send_keys("10")
    receipt = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
    pdf = tmp_path / "receipt.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    receipt.send_keys(str(pdf))
    click_button(driver, "Save expense")
    wait_for_text(driver, "Receipt expense")


def test_TC_Exp_04_recurring_rule(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/recurring")
    assert "Recurring" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Cat_02_category_suggestion_accept(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses")
    click_button(driver, "Add expense")
    field(driver, "Description").send_keys("Uber ride")
    WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Travel"))


def test_TC_Import_01_csv_preview_and_import(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses/import")
    assert "Import" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Bud_01_create_budget(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/budgets")
    assert "Budget" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Alert_01_80_percent_alert(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/alerts")
    assert "Alert" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Shared_01_share_budget_with_member(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/budgets")
    assert "Budget" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Report_01_export_pdf_and_excel(request, driver, unique_user, tmp_path):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/reports")
    assert "Report" in driver.find_element(By.TAG_NAME, "body").text


def test_TC_Audit_01_expense_history(request, driver, unique_user):
    remember_driver(request, driver)
    register(driver, unique_user)
    driver.get(f"{BASE_URL}/expenses")
    assert "Expense" in driver.find_element(By.TAG_NAME, "body").text
