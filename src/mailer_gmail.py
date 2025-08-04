import argparse
import csv
import ssl
import random
import time
import os

from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument("--preview", action="store_true", help="Preview emails before sending")
args = parser.parse_args()

load_dotenv()
USER = os.getenv("GMAIL_USER")
PASS = os.getenv("GMAIL_APP_PASS")
CSV  = os.getenv("CSV_PATH")
TPL  = os.getenv("TEMPLATE")
NAME = os.getenv("GMAIL_NAME")

LOG  = os.path.join(os.path.dirname(__file__), "../sent_log.csv")
def load_sent_log():
    if not os.path.exists(LOG):
        return set()
    with open(LOG, newline="") as f:
        return {row["key"] for row in csv.DictReader(f)}

def append_to_log(key, cced):
    write_header = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["key", "cced", "timestamp"])
        writer.writerow([key, cced, datetime.utcnow().isoformat()])


def load_prospects():
    with open(CSV, newline="") as f:
        return list(csv.DictReader(f))

def send_mail(recipient, subject, body, cced=False):
    msg = EmailMessage()
    msg["From"] = f"{NAME} <{USER}>"
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

    sent_keys = load_sent_log()
    print(f"Loaded {len(sent_keys)} sent emails from log.")

    seen_keys = set()  
    for p in load_prospects():
        key = f"{p['first_name'].lower()}::{p['last_name'].lower()}::{p['company_domain'].lower()}"

        if key in sent_keys or key in seen_keys:
            print(f"Skipping {key} (already sent).")
            continue

        seen_keys.add(key)

        to_addr = f"{p['first_name'].lower()}.{p['last_name'].lower()}@{p['company_domain']}"
        subj    = f"Chat about {p['company']} {p['role']} role?"     # Modify it later 
        body    = template.format(**p)
        cc_flag = p.get("cced", "").strip().lower() == "yes"

        print(f"Would send to {to_addr}{' (CC: Edwin)' if cc_flag else ''}")

        print("\n--- Email Preview ---")
        print(f"To     : {to_addr}")
        print(f"Subject: {subj}")
        print(f"Body   :\n{body}")
        print("---------------------\n")

        if args.preview:
            confirm = input("Send this email? (y/n): ").strip().lower()
            if confirm != "y":
                print("Skipped.\n")
                continue

        send_mail(to_addr, subj, body, cced=cc_flag)  # uncomment to actually send
        append_to_log(key, cc_flag)

        # Add delay to avoid hitting rate limits
        delay = random.uniform(1, 3)
        print(f"Sleeping for {delay:.2f} seconds...\n")
        time.sleep(delay)
