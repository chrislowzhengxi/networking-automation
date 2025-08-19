import argparse
import csv
import ssl
import random
import time
import os
from datetime import datetime, timezone
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
TPL_DIR = os.getenv("TEMPLATE_DIR")  

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
        writer.writerow([key, cced, datetime.now(timezone.utc).isoformat()])

def load_prospects():
    with open(CSV, newline="") as f:
        return list(csv.DictReader(f))

# New logic 
def is_truthy(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in {"y", "yes", "true", "1"}

def load_template(template_name: str) -> str:
    if not template_name:
        raise ValueError("Missing 'template' in CSV row.")
    path = os.path.join(TPL_DIR, f"{template_name}.tpl.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
# Build subjects from template key, no need to put subject in CSV
SUBJECT_BUILDERS = {
    "bulls": lambda r: (
        f"Chicago Bulls Data Analyst and UChicago Student interested in your work at "
        f"{r.get('company','').strip() or 'your firm'} - {r.get('first_name','').strip()}"
    ),
    "uchicago": lambda r: (
        f"UChicago Student interested in {r.get('role','').strip() or 'opportunities'} at "
        f"{r.get('company','').strip() or 'your company'} - {r.get('first_name','').strip()}"
    ),
    "edwin": lambda r: (
        f"UChicago and Rice Twins Curious About Your Path at "
        f"{r.get('company','').strip() or 'your company'} - {r.get('first_name','').strip()}"
    ),
}

def sanitize_subject(s: str) -> str:
    # Keep it clean and simple
    s = s.replace("—", "-").replace("–", "-")
    return " ".join(s.split())

def build_subject(row: dict) -> str:
    key = (row.get("template") or "").strip()
    builder = SUBJECT_BUILDERS.get(key)
    if builder is None:
        # Fallback if template key has no subject rule
        company = row.get("company", "").strip() or "your company"
        return f"UChicago Student Interested in {company}"
    return sanitize_subject(builder(row))



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
    # template = open(TPL).read()

    sent_keys = load_sent_log()
    print(f"Loaded {len(sent_keys)} sent emails from log.")

    seen_keys = set()  
    for p in load_prospects():
        key = f"{p['first_name'].lower()}::{p['last_name'].lower()}::{p['company_domain'].lower()}"

        if key in sent_keys or key in seen_keys:
            print(f"Skipping {key} (already sent).")
            continue

        seen_keys.add(key)

        # Recipient 
        to_addr = f"{p['first_name'].lower()}.{p['last_name'].lower()}@{p['company_domain']}"
        # subj    = f"UChicago and Rice Twins Curious About Your Path at {p['company']} – {p['first_name']}"    
        # body    = template.format(**p)
        # cc_flag = p.get("cced", "").strip().lower() == "yes"
        cc_flag = is_truthy(p.get("cced"))

        # Template and subject
        template_name = (p.get("template") or "").strip()
        template_text = load_template(template_name)
        subj = build_subject(p)

        # Body
        try:
            body = template_text.format(**p)
        except KeyError as e:
            missing = str(e).strip("'")
            raise KeyError(
                f"Missing placeholder '{missing}' in CSV for template '{template_name}'. "
                f"Add column '{missing}' or remove it from the template."
            ) from e

        print(f"Would send to {to_addr}{' (CC: Edwin)' if cc_flag else ''}")

        print("\n--- Email Preview ---")
        print(f"To     : {to_addr}")
        if cc_flag:
            print("Cc     : el52@rice.edu")
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
        delay = random.uniform(1.0, 3.0)
        print(f"Sleeping for {delay:.2f} seconds...\n")
        time.sleep(delay)
