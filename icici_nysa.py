from playwright.sync_api import sync_playwright, Playwright, Page, Browser, BrowserContext, TimeoutError
from playwright.sync_api import expect

from db_connection import make_db_connection
from get_playwright_page import get_playwright_page
import time
import os
from datetime import date, timedelta
import pandas as pd


def icici_nysa_authentication(p):
    login_what = "nysa"
    login_user_id = os.getenv("NYSA_USER_ID")
    login_password = os.getenv("NYSA_PASSWORD")
    # # prepare Playwright
    # with sync_playwright() as p:

    # ---------------------
    matchers = ['https://nysa-lite.icicilombard.com/#/quote','https://nysa-lite.icicilombard.com/#/login' ]
    [browser, page, context, running_status] = get_playwright_page(p, matchers, slow_mo=50)
    if running_status:
        print(f"{login_what} is running")
        # Check if logged in to the website
        logged_in_as = page.get_by_role("button", name="Change Password")
        logged_user = page.locator("div.imname")
        # logged_user = page.locator("div.imname").inner_text()
        if logged_in_as.is_visible() and logged_user.is_visible():
            print("Already logged in")
            return [browser, page, context]

    baseurl = "https://nysa-lite.icicilombard.com/#/login"
    retry = 0
    max_no_of_retry = 3
    while retry < max_no_of_retry:
        try:
            page.goto(baseurl, wait_until="domcontentloaded", timeout=5000)
            page.get_by_placeholder("Username").wait_for(timeout=5000)
            break
        except TimeoutError:
            print (f"{login_what}  homepage timed out. Retrying..")
            time.sleep(3)
            retry += 1
    if retry == max_no_of_retry:
        print (f"{login_what}  homepage timed out. Exiting..")
        exit(1)
    # Authentication begins
    # captchaCode

    page.get_by_placeholder("Username").fill(login_user_id)
    page.get_by_placeholder("Password").fill(login_password)
    page.get_by_role("button", name="LOG IN").click()
    return [browser, page, context]




def get_nysa_issuance_report(page):
    page.get_by_role("link", name="Issuance Report").click()
    # Get yesterday's date in a variable
    yesterday = date.today() - timedelta(days=4)
    # get the mm/dd part
    yesterday_mmdd = yesterday.strftime('%d/%m/')
    page.get_by_role("textbox", name="From Date*").click()
    # page.get_by_role("textbox", name="To Date*").click()
    page.get_by_label(yesterday_mmdd).click()

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Submit").click()
    download = download_info.value
    file_path = "policy_details.xlsx"
    download.save_as(file_path)
    return file_path

def update_aiven_database(download_file_path):
    # Get the actual file path of the downloaded Excel
    excel_file = download_file_path

    # Load Excel Data
    df = pd.read_excel(excel_file)

    # Normalize all column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Filter only "new business" rows (case-insensitive match)
    updates_df = df[df["transaction_type"].str.strip().str.lower() == "new business"].copy()

    # Prepare insurance fields
    updates_df["insurance_name"] = "ICICI Lombard GIC Limited"
    updates_df["insurance_type"] = "Third Party"
    updates_df["insurance_start_date"] = pd.to_datetime(updates_df["transaction_date"])
    updates_df["insurance_end_date"] = updates_df["insurance_start_date"] + pd.DateOffset(years=5)+ pd.DateOffset(days=-1)
    updates_df["cover_note_no"] = updates_df["policy_number"]

    updates_df = updates_df[[
        "chassis_number",
        "insurance_name",
        "insurance_start_date",
        "insurance_type",
        "insurance_end_date",
        "cover_note_no"
    ]]

    # --------------------------
    # Connect to Database
    conn, cur = make_db_connection()

    # --------------------------
    # 5. Update Query
    # --------------------------
    update_query = """
    UPDATE vahan_extract
    SET
        insurance_name = %s,
        insurance_start_date = %s,
        insurance_type = %s,
        insurance_end_date = %s,
        cover_note_no = %s
    WHERE frame_no = %s
    """

    # --------------------------
    # 6. Execute Updates
    # --------------------------
    updated_records = []

    for _, row in updates_df.iterrows():
        cur.execute(update_query, (
            row["insurance_name"],
            row["insurance_start_date"],
            row["insurance_type"],
            row["insurance_end_date"],
            row["cover_note_no"],
            row["chassis_number"]   # match with frame_no
        ))
        updated_records.append(row.to_dict())

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Insurance details updated for {len(updated_records)} 'New Business' records.")

def run_icici_nysa():
    start_time = time.time()

    with sync_playwright() as p:
        page: Page
        browser: Browser
        context: BrowserContext
        [browser, page, context] = icici_nysa_authentication(p)
        page_url = page.url
        excel_download = get_nysa_issuance_report(page)
        update_aiven_database(excel_download)
        exit(0)


if __name__ == '__main__':
    run_icici_nysa()