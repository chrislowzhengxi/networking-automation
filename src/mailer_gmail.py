import csv
import ssl
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

def send_mail(recipient, subject, body):
    msg = EmailMessage()
    msg["From"]    = USER
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with __import__("smtplib").SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(USER, PASS)
        s.send_message(msg)

if __name__ == "__main__":
    template = open(TPL).read()
    for p in load_prospects():
        to_addr = f"{p['first_name'].lower()}.{p['last_name'].lower()}@{p['company_domain']}"
        subj    = f"Chat about {p['company']} {p['role']} role?"
        body    = template.format(**p)
        print("Would send to", to_addr)    # dry run
        send_mail(to_addr, subj, body)  # uncomment to actually send
