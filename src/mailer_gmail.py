import csv
import ssl
import random
import time
import os
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv("GMAIL_USER")
PASS = os.getenv("GMAIL_APP_PASS")
CSV  = os.getenv("CSV_PATH")
TPL  = os.getenv("TEMPLATE")

def load_prospects():
    with open(CSV, newline="") as f:
        return list(csv.DictReader(f))

def send_mail(recipient, subject, body, cced=False):
    msg = EmailMessage()
    msg["From"]    = USER
    msg["To"]      = recipient
    msg["Subject"] = subject

    if cced:
        msg["Cc"] = "el52@rice.edu"

    
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with __import__("smtplib").SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(USER, PASS)
        s.send_message(msg)

if __name__ == "__main__":
    template = open(TPL).read()
    for p in load_prospects():
        to_addr = f"{p['first_name'].lower()}.{p['last_name'].lower()}@{p['company_domain']}"
        subj    = f"Chat about {p['company']} {p['role']} role?"     # Modify it later 
        body    = template.format(**p)

        cc_flag = p.get("cced", "").strip().lower() == "yes"

        print(f"Would send to {to_addr}{' (CC: Edwin)' if cc_flag else ''}")

        send_mail(to_addr, subj, body, cced=cc_flag)  # uncomment to actually send

        # Add delay to avoid hitting rate limits
        delay = random.uniform(1, 3)
        print(f"Sleeping for {delay:.2f} seconds...\n")
        time.sleep(delay)
