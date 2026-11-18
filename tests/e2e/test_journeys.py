"""
Selenium end-to-end journeys (S3-12, issue #74). Each test is named after its test case ID in
docs/requirements/rtm.md and drives the real app in Chrome, from sign-in to the result a user would see.
"""

import time
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from conftest import (BASE_URL, DIALOG, add_expense, button, by_label, choose, create_budget, field, login,
                      open_dialog, register, set_value, type_into, visible, wait, wait_dialog_closed,
                      wait_for_text, wait_for_text_gone)


# ---------------------------------------------------------------- FR1, FR2: accounts

def test_TC_Auth_01_register_lands_on_dashboard(driver, user):
    register(driver, user)
    heading = visible(driver, By.TAG_NAME, "h1").text
    assert user["first"] in heading


def test_TC_Auth_02_login_logout_and_protected_redirect(driver, user):
    register(driver, user)
    by_label(driver, "Sign out").click()
    wait(driver).until(lambda d: d.current_url.endswith("/login"))
    driver.get(f"{BASE_URL}/expenses")                       # signed out: protected page redirects
    wait(driver).until(lambda d: d.current_url.endswith("/login"))
    login(driver, user)
    assert driver.current_url.rstrip("/") == BASE_URL


def test_TC_Auth_03_profile_edit_persists(driver, user):
    register(driver, user)
    driver.get(f"{BASE_URL}/profile")
    type_into(driver, "Last name", "Updated")
    button(driver, "Save changes").click()
    wait_for_text(driver, "Profile saved")
    driver.refresh()
    wait(driver).until(lambda d: field(d, "Last name").get_attribute("value") == "Updated")


# ---------------------------------------------------------------- FR4, FR5, FR6, FR21: expenses

def test_TC_Exp_01_add_edit_delete_expense(driver, user):
    register(driver, user)
    add_expense(driver, "E2E lunch", "120", merchant="Corner Cafe", notes="Team lunch")
    assert "Corner Cafe" in driver.find_element(By.TAG_NAME, "body").text

    by_label(driver, "Edit E2E lunch").click()
    open_dialog(driver)
    type_into(driver, "Amount", "180", DIALOG)
    button(driver, "Save changes", DIALOG).click()
    wait_dialog_closed(driver)
    wait_for_text(driver, "180")

    by_label(driver, "Delete E2E lunch").click()
    open_dialog(driver)
    driver.find_elements(By.XPATH, "//dialog[@open]//button")[-1].click()   # the confirm button
    wait_for_text_gone(driver, "E2E lunch")


def test_TC_Exp_03_receipt_upload_and_link(driver, user, tmp_path):
    register(driver, user)
    receipt = tmp_path / "receipt.pdf"
    receipt.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    add_expense(driver, "Receipt expense", "45", receipt=receipt)
    wait(driver).until(lambda d: d.find_elements(By.CSS_SELECTOR, "[title='View receipt'], a.receipt-link"))


def test_TC_Exp_04_recurring_rule_pause_resume(driver, user):
    register(driver, user)
    driver.get(f"{BASE_URL}/recurring")
    type_into(driver, "Amount", "15000")
    Select(field(driver, "Frequency")).select_by_value("monthly")
    set_value(driver, field(driver, "Start date"), date.today().isoformat())
    type_into(driver, "Merchant", "Landlord")
    button(driver, "Create rule").click()
    wait_for_text(driver, "Landlord")
    row = lambda d: d.find_element(By.XPATH, "//tr[contains(., 'Landlord')]")
    wait(driver).until(lambda d: "Active" in row(d).text)
    row(driver).find_element(By.XPATH, ".//button[normalize-space()='Pause']").click()
    wait(driver).until(lambda d: "Paused" in row(d).text)
    row(driver).find_element(By.XPATH, ".//button[normalize-space()='Resume']").click()
    wait(driver).until(lambda d: "Active" in row(d).text)


def test_TC_Audit_01_expense_history(driver, user):
    register(driver, user)
    add_expense(driver, "History lunch", "120")
    by_label(driver, "Edit History lunch").click()
    open_dialog(driver)
    type_into(driver, "Amount", "180", DIALOG)
    button(driver, "Save changes", DIALOG).click()
    wait_dialog_closed(driver)
    by_label(driver, "History of History lunch").click()
    dialog = open_dialog(driver)
    wait(driver).until(lambda d: "Changed" in dialog.text)
    assert "120.00" in dialog.text and "180.00" in dialog.text


# ---------------------------------------------------------------- FR7: CSV import

def test_TC_Import_01_csv_preview_and_import(driver, user, tmp_path):
    register(driver, user)
    csv = tmp_path / "expenses.csv"
    csv.write_text("date,amount,category,payment_mode,merchant,notes\n"
                   f"{date.today().isoformat()},250.00,Food,upi,Imported Grocer,good row\n"
                   f"{date.today().isoformat()},-5,Food,upi,Bad Row,negative amount\n", encoding="utf-8")
    driver.get(f"{BASE_URL}/expenses/import")
    upload = wait(driver).until(lambda d: d.find_element(By.CSS_SELECTOR, "input[type='file']"))
    driver.execute_script("arguments[0].style.display = 'block';", upload)   # the drop zone hides the native input
    upload.send_keys(str(csv))
    button(driver, "Preview import").click()
    wait_for_text(driver, "1 valid row; 1 rejected.")
    error_row = visible(driver, By.XPATH, "//tr[td[1][normalize-space()='3']]")   # the bad row is line 3 of the file
    assert "amount" in error_row.text and "-5" in error_row.text
    button(driver, "Import valid rows").click()
    wait_for_text(driver, "Import complete")
    driver.get(f"{BASE_URL}/expenses")
    wait_for_text(driver, "Imported Grocer")
    assert "Bad Row" not in driver.find_element(By.TAG_NAME, "body").text


# ---------------------------------------------------------------- FR8, FR9: categories

def test_TC_Cat_01_custom_subcategory(driver, user):
    register(driver, user)
    driver.get(f"{BASE_URL}/categories")
    type_into(driver, "Category name", "Gym")
    button(driver, "Create category").click()
    wait_for_text(driver, "Gym")
    type_into(driver, "Category name", "Yoga")
    choose(driver, "Parent category", "Gym")
    button(driver, "Create category").click()
    wait(driver).until(lambda d: d.find_elements(
        By.XPATH, "//*[contains(@class,'category-item')][contains(., 'Gym')]//*[contains(@class,'category-item')][contains(., 'Yoga')]"))


def test_TC_Cat_02_category_suggestion_accept(driver, user):
    register(driver, user)
    driver.get(f"{BASE_URL}/expenses")
    button(driver, "Add expense").click()
    open_dialog(driver)
    type_into(driver, "Description", "Uber ride to the airport", DIALOG)
    suggestions = visible(driver, By.XPATH, "//*[@aria-label='Category suggestions']")
    suggestions.find_element(By.XPATH, ".//button[contains(normalize-space(), 'Travel')]").click()
    wait(driver).until(lambda d: Select(field(d, "Category", DIALOG)).first_selected_option.text == "Travel")


# ---------------------------------------------------------------- FR10, FR16: budgets and alerts

def test_TC_Bud_01_create_budget(driver, user):
    register(driver, user)
    create_budget(driver, "Groceries", "1000")
    card = driver.find_element(By.XPATH, "//*[contains(@class,'budget-card')][contains(., 'Groceries')]")
    assert "1,000" in card.text


def test_TC_Alert_01_80_percent_alert(driver, user):
    register(driver, user)
    create_budget(driver, "Food this month", "1000")
    add_expense(driver, "Big shop", "850")
    driver.get(f"{BASE_URL}/alerts")
    wait_for_text(driver, "Budget reached 80%")
    wait(driver).until(lambda d: d.find_elements(By.XPATH, "//*[@aria-label='Alerts, 1 unread']"))


# ---------------------------------------------------------------- FR3: shared budgets (two people)

def test_TC_Shared_01_share_budget_with_member(browsers, user):
    owner_browser, member_browser = browsers(), browsers()
    member = {**user, "first": "Ben", "email": user["email"].replace("e2e.", "e2e.member.")}
    register(member_browser, member)
    register(owner_browser, user)
    create_budget(owner_browser, "Household", "2000")
    by_label(owner_browser, "Members of Household").click()
    open_dialog(owner_browser)
    type_into(owner_browser, "Email", member["email"], DIALOG)
    Select(field(owner_browser, "Role", DIALOG)).select_by_value("member")
    button(owner_browser, "Add to budget", DIALOG).click()
    wait(owner_browser).until(lambda d: member["email"] in d.find_element(By.CSS_SELECTOR, "dialog[open]").text)

    member_browser.get(f"{BASE_URL}/budgets")
    wait_for_text(member_browser, "Household")
    card = member_browser.find_element(By.XPATH, "//*[contains(@class,'budget-card')][contains(., 'Household')]")
    assert "Shared by" in card.text
    assert not card.find_elements(By.XPATH, ".//*[@aria-label='Delete Household']")   # members cannot delete


# ---------------------------------------------------------------- FR19, FR20: reports

def _downloaded(folder, suffix, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:  # polling the download folder; there is no DOM event to wait on
        done = [p for p in folder.iterdir() if p.suffix == suffix]
        if done:
            return done[0]
        time.sleep(0.25)
    raise AssertionError(f"no {suffix} file downloaded into {folder}")


def test_TC_Report_01_export_pdf_and_excel(driver, user):
    register(driver, user)
    add_expense(driver, "Report lunch", "300")
    driver.get(f"{BASE_URL}/reports")
    wait_for_text(driver, "Total spend")
    button(driver, "Export PDF").click()
    pdf = _downloaded(driver.download_dir, ".pdf")
    button(driver, "Export Excel").click()
    xlsx = _downloaded(driver.download_dir, ".xlsx")
    assert pdf.read_bytes()[:5] == b"%PDF-"
    assert xlsx.read_bytes()[:2] == b"PK"
