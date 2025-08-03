# 📬 Networking Email Automation

This project helps streamline the process of sending personalized networking emails during recruiting season. It allows you to:

- Load a list of contacts from a CSV file
- Customize and send templated emails
- Use Gmail’s secure App Password authentication
- Automate your outreach while keeping things personal

---

## ✅ Requirements

- Python 3.7+
- Gmail account with [App Passwords](https://myaccount.google.com/u/2/apppasswords) 

---




## ✏️ Setup

1. Clone the repo  
2. Set up a virtual environment:

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install python-dotenv
   ```
3.  Create a `.env` file in the root:

  ```
  GMAIL_USER=your.email@gmail.com
  GMAIL_APP_PASS=your_16_character_app_password
  CSV_PATH=prospects.csv
  TEMPLATE=templates/outreach.tpl.txt
  ```

4. Fill out `prospects.csv`:
  ```
  first_name,last_name,company,role,company_domain,personal_note
  Alice,Chen,Goldman Sachs,Analyst,gs.com,Met at UChicago info session
  ```

5. Write your template in `templates/outreach.tpl.txt`:
```
Hi {first_name},

I'm Chris, a senior at UChicago studying CS & Econ. I recently applied to {company}'s {role} program and noticed we {personal_note}. Would you be open to a 15-minute chat?

Best,
Chris
```

6. Run: `python src/mailer_gmail.py`


## 🛡️ Safety Tips
- Send in small batches (e.g., 10–20/hr)
- Keep a sent_log.csv if you want to track progress
- Don’t commit .env or personal data
- If Gmail flags your activity, wait and resume later

## 💡 Future Improvements
Add scheduling/follow-up reminders
Connect to LinkedIn scraping (safely)
Switch to Outlook or Gmail API for richer control

## 📫 Contact
Built by Chris Low for recruiting season survival.
Feel free to fork, modify, and use responsibly.

