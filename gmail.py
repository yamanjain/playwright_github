from __future__ import print_function

import datetime
import os.path
import time
from dateutil import parser
from bs4 import BeautifulSoup
import base64
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def gmail_otp(time_otp_sent, user_id, local_clock_wrong_in_seconds = 0):
    # def gmail_otp(gmail_query_string, otp_tagger_string, otp_length, time_otp_sent):
    time_otp_sent = time_otp_sent - datetime.timedelta(seconds=local_clock_wrong_in_seconds)
    gmail_query_string = "from:Honda@honda.hmsi.in subject:OTP For HI-RISE Login"
    otp_tagger_string = f"Your OTP Code for User Id({user_id}) to login to HI-RISE is "
    otp_length = 42
    if local_clock_wrong_in_seconds < 60:
        time.sleep(5)

    gmail_query_string = gmail_query_string + " in:inbox newer_than:1d"
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    cwd = os.getcwd()
    try:
        if os.path.exists(cwd + os.path.sep + 'token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(cwd + os.path.sep + 'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(cwd + os.path.sep + 'token.json', 'w') as token:
                token.write(creds.to_json())

    except Exception as error:
        print(f'An error occurred during authentication: {error}')
        exit(0)

    try:
        latest_email_body = ""
        latest_email_date = datetime.datetime(1990, 1, 1, 0, 0, 0).astimezone()
        service = build('gmail', 'v1', credentials=creds, static_discovery=False)

        retry = 0
        otp_array = []
        max_retry = 12
        if local_clock_wrong_in_seconds > 600:
            max_retry = 2
        while retry < max_retry and len(otp_array) <= 1:
            retry += 1
            all_emails = fetch_emails(service, gmail_query_string)
            output_list = []
            for result in all_emails:
                # Fetch Email object with raw email body and attachment ids
                msg = service.users().messages().get(userId="me", id=result['id'], format="full").execute()
                payload = msg['payload']
                parts = payload.get('parts')
                if parts is None:
                    # Simpler method without recursion
                    email_body = parse_msg_body(msg)
                else:
                    # Get body using recursion
                    [body_message, body_html] = processParts(parts)
                    email_body_text = str(body_message, 'utf-8')
                    email_html = str(body_html, 'utf-8')
                    email_html_text = clean_html(email_html)
                    email_body = email_body_text + email_html_text
                # Special for hirise OTP
                if otp_tagger_string not in email_body:
                    continue
                email_headers = get_headers(msg)
                gmail_date = parser.parse(email_headers["Date"])
                if gmail_date > time_otp_sent:
                    latest_email_date = max(latest_email_date, gmail_date)
                    if gmail_date == latest_email_date:
                        latest_email_body = email_body
                        latest_email_headers = email_headers

            otp_array = latest_email_body.split(otp_tagger_string)
            if len(otp_array) <= 1:
                if (retry<3):
                    time.sleep(5)
                else:
                    time.sleep(10)
            # keep retrying above till valid otp email received

        if len(otp_array) > 1:
            otp = otp_array[1][:otp_length]
        else:
            otp = ""
        # print(otp)
        return otp
        ## Create a python data structure with all the info and convert it to json and write to a file
        # output_list.append({'email_headers': latest_email_headers, 'email_body': latest_email_body})
        # with open("payload.json", "w") as outfile:
        #     json.dump(output_list, outfile)

    except HttpError as error:
        print(f'An error occurred: {error}')


def get_headers(msg):
    headers_needed = ['From', 'To', 'Date', 'Subject']
    res_dict = {}
    headers_list = msg.get("payload").get('headers')
    for header in headers_list:
        if header['name'] in headers_needed:
            res_dict[header['name']] = header['value']

    return res_dict


def fetch_emails(service, gmail_query_string):
    """
    Get all emails based on a filter passed in args
    """
    try:
        # Filter q sssed from caller.
        args = sys.argv[1:]
        # Call the Gmail API
        results = service.users().messages().list(userId='me', q=gmail_query_string).execute()
        # results = service.users().messages().list(userId='me', q='from:support@icicilombard.com subject:fund transfer for motor claim newer_than:8d').execute()
        # results = service.users().messages().list(userId='me', q="from:noreply@godigit.com subject:Claim Payment Advice newer_than:10d").execute()
        # results = service.users().messages().list(userId='me', q="label:autoproc newer_than:23d").execute()
        # results = service.users().messages().list(userId='me', q=args[0]).execute()
        if 'messages' in results:
            return results['messages'] or []
        else:
            return []
    except HttpError as error:
        print(f'An error occurred: {error}')


def parse_msg_body(msg):
    """
    Find the email body from the respective email object
    Navigate to payload > body > data, if not present it should be available as a part object
    Navigate to the part[0] to get the available parts and retrieve the email body
    Navigate to the part[0] -> part[0] to get the available parts and retrieve the email body
    If the email body is not available, from above three then return the snippet.
    """
    try:
        if msg.get("payload").get("body").get("data"):
            return base64.urlsafe_b64decode(msg.get("payload").get("body").get("data").encode("ASCII")).decode("utf-8")
        elif msg.get("payload").get("parts")[0].get("body").get("data"):
            return base64.urlsafe_b64decode(
                msg.get("payload").get("parts")[0].get("body").get("data").encode("ASCII")).decode("utf-8")
        elif msg.get("payload").get("parts")[0].get("parts")[0].get("body").get("data"):
            return base64.urlsafe_b64decode(
                msg.get("payload").get("parts")[0].get("parts")[0].get("body").get("data")).decode("utf-8")
        return msg.get("snippet")
    except Exception as e:
        err_msg = f"Error occurred while fetching email body: {e}"
        print(err_msg)
        return err_msg


def processParts(parts):
    if not 'body_message' in locals():
        body_message = bytearray()
    if not 'body_html' in locals():
        body_html = bytearray()
    for part in parts:
        body = part.get("body")
        data = body.get("data")
        mimeType = part.get("mimeType")
        if mimeType == 'multipart/alternative':
            subparts = part.get('parts')
            [body_message, body_html] = processParts(subparts)
        elif mimeType == 'text/plain' and not isinstance(data, type(None)):
            body_message = base64.urlsafe_b64decode(data)
        elif mimeType == 'text/html' and not isinstance(data, type(None)):
            body_html = base64.urlsafe_b64decode(data)
    return [body_message, body_html]


def clean_html(email_html):
    soup = BeautifulSoup(email_html, features="html.parser")
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text


if __name__ == '__main__':
    # if os.path.exists("payload.json"):
    #     os.remove("payload.json")
    gmail_otp()
