import datetime
import os
import time

from playwright.sync_api import sync_playwright, Playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect
import gmail
from get_playwright_page import get_playwright_page
import re
import pickle

from hirisevahanextract import load_and_insert_csv


def check_otp_valid(email_text):
    # 1. Extract the expiry date and time using a regular expression
    expiry_match = re.search(r'(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2})', email_text)

    if not expiry_match:
        print("Expiry date not found in the text.")
        return False

    expiry_str = expiry_match.group(1)

    # 2. Parse the expiry string into a datetime object
    # The format %m/%d/%Y %H:%M:%S matches MM/DD/YYYY HH:MM:SS
    expiry_datetime = datetime.datetime.strptime(expiry_str, "%m/%d/%Y %H:%M:%S")

    # 3. Get the current datetime
    current_datetime = datetime.datetime.now()

    # 4. Compare the current time with the expiry time
    is_valid = current_datetime <= expiry_datetime

    return is_valid


def hirise_authentication(p):
    global captcha_retry
    # # prepare Playwright
    # with sync_playwright() as p:

    # ---------------------
    matchers = ['https://hirise.honda2wheelersindia.com/']
    [browser, page, context, running_status] = get_playwright_page(p, matchers, slow_mo=50)
    if running_status:
        print("Hirise is running")
        # Check if logged in to Hirise
        logged_in_as = page.get_by_role("menuitem", name="Settings")
        logged_user = page.get_by_text("Active Position: HMSI-Sal-E-BR-BR010001")
        # logged_user = page.get_by_text("BINODJAIN@GMAIL.COM")
        if logged_in_as.is_visible() and logged_user.is_visible():
            print("Already logged in")
            return [browser, page, context]

    baseurl = "https://hirise.honda2wheelersindia.com/"
    retry = 0
    max_no_of_retry = 3
    while retry < max_no_of_retry:
        try:
            page.goto(baseurl, timeout=5000)
            break
        except:
            print ("Hirise homepage timed out. Retrying..")
            retry += 1
    if retry == max_no_of_retry:
        print ("Hirise homepage timed out. Exiting..")
        exit(1)
    # Authentication begins
    # captchaCode
    incorrect_password_filename = "incorrect_hirise_password.pkl"
    if os.path.exists(incorrect_password_filename):
        # Retrieve from file
        with open(incorrect_password_filename, "rb") as f:
            loaded_incorrect_password = pickle.load(f)

    hirise_user_id = os.getenv('hirise_user_id')
    hirise_password = os.getenv('hirise_password')
    if loaded_incorrect_password == hirise_password:
        print("Hirise password has expired or is invalid. Saved incorrect password found. Please check and update the .env file. Exiting..")
        exit(0)
    print ("Using Hirise User ID:", hirise_user_id)
    page.get_by_label("HI-RISE User ID").fill(hirise_user_id)
    page.get_by_label("Password").fill(hirise_password)
    page.get_by_role("link", name="Login")
    # get text of element with id captchaCode
    captcha_text = page.locator("#captchaCode").text_content()
    # remove all spaces and newlines from captcha_text
    captcha_text = captcha_text.replace(" ", "").replace("\n", "")
    page.get_by_role("textbox", name="Captcha").fill(captcha_text)
    time_otp_sent = datetime.datetime.now().astimezone()
    # time difference between gmail and local clock is about ten seconds
    # But here we are fetching all email from past 4 hours since OTP is valid for 4 hours
    local_clock_wrong_in_seconds = 60 * 60 * 4 + 10
    # Using temp file to store OTP
    otp_filename = "temp_hirise_otp.pkl"
    otp_source = "Unknown"
    my_otp = ''
    loaded_userid = ''
    if os.path.exists(otp_filename):
        # Retrieve from file
        with open(otp_filename, "rb") as f:
            (loaded_userid, my_otp) = pickle.load(f)
    if loaded_userid == hirise_user_id and check_otp_valid(my_otp):
        otp_source = "temp file"
    else:
        print ("Fetching OTP from Gmail")
        my_otp = gmail.gmail_otp(time_otp_sent, hirise_user_id, local_clock_wrong_in_seconds)
        if not check_otp_valid(my_otp):
            print("No valid OTP in Gmail. Sending new OTP.")
            time_otp_sent = datetime.datetime.now().astimezone()
            page.get_by_role("button", name="Send OTP").click()
            page.once("dialog", lambda dialog: dialog.dismiss())
            local_clock_wrong_in_seconds = 10
            my_otp = gmail.gmail_otp(time_otp_sent, local_clock_wrong_in_seconds)
        if check_otp_valid(my_otp):
            otp_source = "Gmail"
    if check_otp_valid(my_otp):
        print(f"Valid OTP found in {otp_source}.")
        page.get_by_role("textbox", name="OTP").fill(my_otp[0:4])
        # Store in file
        otp_data = (hirise_user_id, my_otp)
        with open(otp_filename, "wb") as f:
            pickle.dump(otp_data, f)
    else:
        print ("Enter OTP manually")
        page.pause()
    page.get_by_role("link", name="Login").click()
    time.sleep(1)
    incorrect_password = page.get_by_text("The user ID or password that you entered is incorrect")
    if incorrect_password.is_visible():
        with open(incorrect_password_filename, "wb") as f:
            pickle.dump(hirise_password, f)
        print("Incorrect User ID or Password. Exiting..")
        exit(0)
    # Check if logged in to Hirise

    return [browser, page, context]

def get_vahan_csv_from_hirise(page, file_path):
    page.get_by_label("Site Map").locator("span").first.click()
    page.locator("#sitemapFilterInput").click()
    # 1. Locate the site map table by its class name
    # table_locator = page.locator('#sitemapSection2')
    page.locator("span.siebui-screen-name-2").get_by_role("link", name="Invoices").click()

    # 2. Within that table, find a link by its text and click it

    # table_locator.get_by_role("link", name="Invoices").click()
    # page.locator("#s_smc_1602").click()
    page.locator("select[name=\"s_pdq\"]").select_option("All Invoices Today -1")
    time.sleep(3)
    page.locator("a.ui-tabs-anchor", has_text="RTO Extract").nth(1).click()
    time.sleep(2)
    page.get_by_label("RTO Extract List: Menu").click()
    time.sleep(0.5)
    page.get_by_role("menuitem", name="Export...").click()
    page.get_by_label("Comma Separated Text File").check()
    with page.expect_download() as download_info:
        page.get_by_label("Export Form:Next").click()
    download = download_info.value
    # Save with a custom name and path
    download.save_as(file_path)
    page.get_by_label("Export Form:Close").click()


def hirise_vahan():
    with sync_playwright() as p:
        [browser,page,context]=hirise_authentication(p)
        file_path = 'RTO_Extract.CSV'
        get_vahan_csv_from_hirise(page, file_path)
        load_and_insert_csv(file_path)

if __name__ == "__main__":
    hirise_vahan()
    print("Vahan CSV extraction completed.")
