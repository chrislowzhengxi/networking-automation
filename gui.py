# gui.py
import os, sys, platform, subprocess, traceback
from pathlib import Path
from outreach import mailer_gmail as mailer
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
try:
    import yaml
except ImportError:
    yaml = None  # fallback defaults

# ---------- config ----------

DEFAULTS = {
    "paths": {
        "cover_template": "cover_letter/templates/cover_letter.docx",
        "cover_outdir": "cover_letter/outs",
        "email_template_dir": "outreach/email_templates",
        "contacts_csv": "outreach/prospects.csv",
        "email_log": "outreach/sent_log.csv",
    },
    "defaults": {
        "pdf": True,
        "cc_myself": False,
    },
}

def load_cfg():
    cfg_path = Path("config.yaml")
    if yaml and cfg_path.is_file():
        try:
            with open(cfg_path, "r") as f:
                raw = yaml.safe_load(f) or {}
            # shallow merge
            out = DEFAULTS.copy()
            out["paths"]   = {**DEFAULTS["paths"], **(raw.get("paths") or {})}
            out["defaults"] = {**DEFAULTS["defaults"], **(raw.get("defaults") or {})}
            out["sender_name"] = raw.get("sender_name")
            out["sender_email"] = raw.get("sender_email")
            return out
        except Exception:
            pass
    return DEFAULTS

CFG = load_cfg()

def open_in_finder(path: Path):
    path = Path(path)
    if platform.system() == "Darwin":
        subprocess.run(["open", str(path)])
    elif platform.system() == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)])


# Adding preview 
def preview_dialog(parent, msg: dict) -> str:
    """
    Show a modal preview. Returns 'send', 'skip', or 'cancel'.
    msg keys: to, cc, subject, body
    """
    win = tk.Toplevel(parent)
    win.title("Preview email")
    win.transient(parent)
    win.grab_set()

    # layout
    frm = ttk.Frame(win, padding=12)
    frm.grid(sticky="nsew")
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)

    # fields
    ttk.Label(frm, text=f"To: {msg['to']}").grid(sticky="w", pady=(0,4))
    if msg["cc"]:
        ttk.Label(frm, text=f"Cc: {msg['cc']}").grid(sticky="w", pady=(0,4))
    ttk.Label(frm, text=f"Subject: {msg['subject']}").grid(sticky="w", pady=(0,8))

    txt = ScrolledText(frm, width=90, height=22, wrap="word")
    txt.grid(sticky="nsew")
    frm.rowconfigure(3, weight=1)
    frm.columnconfigure(0, weight=1)
    txt.insert("1.0", msg["body"])
    txt.configure(state="disabled")

    # buttons
    btns = ttk.Frame(frm)
    btns.grid(sticky="e", pady=(10,0))
    result = {"val": "skip"}  # default if window closed

    def _set(v):
        result["val"] = v
        win.destroy()

    ttk.Button(btns, text="Skip", command=lambda: _set("skip")).grid(row=0, column=0, padx=4)
    ttk.Button(btns, text="Send", command=lambda: _set("send")).grid(row=0, column=1, padx=4)
    ttk.Button(btns, text="Cancel All", command=lambda: _set("cancel")).grid(row=0, column=2, padx=4)

    win.wait_window()
    return result["val"]


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Networking Automation")
        self.geometry("640x420")
        self.minsize(620, 380)

        nb = ttk.Notebook(self)
        self.cover_tab = ttk.Frame(nb)
        self.email_tab = ttk.Frame(nb)
        nb.add(self.cover_tab, text="Cover Letter")
        nb.add(self.email_tab, text="Email")
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_cover()
        self._build_email()

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=12, pady=(0,8))

    # ----- COVER LETTER TAB -----
    def _build_cover(self):
        frm = self.cover_tab

        # Template
        ttk.Label(frm, text="Template (.docx):").grid(row=0, column=0, sticky="w", pady=6)
        self.cover_tpl_var = tk.StringVar(value=CFG["paths"]["cover_template"])
        ttk.Entry(frm, textvariable=self.cover_tpl_var, width=52).grid(row=0, column=1, sticky="we")
        ttk.Button(frm, text="Browse", command=self._pick_cover_template).grid(row=0, column=2, padx=6)

        # Company / Position
        ttk.Label(frm, text="Company:").grid(row=1, column=0, sticky="w", pady=6)
        self.company_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.company_var, width=40).grid(row=1, column=1, sticky="we", columnspan=2)

        ttk.Label(frm, text="Position:").grid(row=2, column=0, sticky="w", pady=6)
        self.position_var = tk.StringVar(value="Software Engineer")
        ttk.Entry(frm, textvariable=self.position_var, width=40).grid(row=2, column=1, sticky="we", columnspan=2)

        # Outdir
        ttk.Label(frm, text="Output folder:").grid(row=3, column=0, sticky="w", pady=6)
        self.outdir_var = tk.StringVar(value=CFG["paths"]["cover_outdir"])
        ttk.Entry(frm, textvariable=self.outdir_var, width=52).grid(row=3, column=1, sticky="we")
        ttk.Button(frm, text="Browse", command=self._pick_outdir).grid(row=3, column=2, padx=6)

        # PDF
        self.pdf_var = tk.BooleanVar(value=bool(CFG["defaults"]["pdf"]))
        ttk.Checkbutton(frm, text="Export PDF (requires Word on macOS)", variable=self.pdf_var).grid(row=4, column=1, sticky="w", pady=4)

        # Actions
        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=3, sticky="e", pady=10)
        ttk.Button(btns, text="Generate", command=self._generate_cover).pack(side="left", padx=6)
        ttk.Button(btns, text="Open Output", command=lambda: open_in_finder(Path(self.outdir_var.get()))).pack(side="left", padx=6)

        # CSV batch (optional)
        sep = ttk.Separator(frm, orient="horizontal"); sep.grid(row=6, column=0, columnspan=3, sticky="we", pady=10)
        ttk.Label(frm, text="Batch (CSV with headers: company,position):").grid(row=7, column=0, sticky="w")
        self.batch_csv_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.batch_csv_var, width=52).grid(row=7, column=1, sticky="we")
        ttk.Button(frm, text="Pick CSV", command=self._pick_batch_csv).grid(row=7, column=2, padx=6)
        ttk.Button(frm, text="Run Batch", command=self._run_batch).grid(row=8, column=2, sticky="e", pady=8)

        for c in range(3):
            frm.grid_columnconfigure(c, weight=1)

    def _pick_cover_template(self):
        p = filedialog.askopenfilename(title="Choose .docx template", filetypes=[("Word docx", "*.docx")], initialdir=str(Path(self.cover_tpl_var.get()).parent))
        if p: self.cover_tpl_var.set(p)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="Choose output folder", initialdir=str(Path(self.outdir_var.get()).parent))
        if d: self.outdir_var.set(d)

    def _pick_batch_csv(self):
        p = filedialog.askopenfilename(title="Choose CSV", filetypes=[("CSV", "*.csv")])
        if p: self.batch_csv_var.set(p)

    def _generate_cover(self):
        tpl = Path(self.cover_tpl_var.get()).expanduser()
        outdir = Path(self.outdir_var.get()).expanduser()
        company = (self.company_var.get() or "").strip()
        position = (self.position_var.get() or "").strip()
        pdf = self.pdf_var.get()

        if not tpl.is_file():
            messagebox.showerror("Error", f"Template not found:\n{tpl}")
            return
        if not company:
            messagebox.showerror("Error", "Please enter a company.")
            return
        outdir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "cover_letter/make_letters.py",
            "--template", str(tpl),
            "--company", company,
            "--position", position,
            "--outdir", str(outdir),
        ]
        if pdf:
            cmd.append("--pdf")
        self._run_cmd(cmd, success_msg=f"Cover letter created for {company}")

    def _run_batch(self):
        tpl = Path(self.cover_tpl_var.get()).expanduser()
        outdir = Path(self.outdir_var.get()).expanduser()
        csv_path = Path(self.batch_csv_var.get()).expanduser()
        pdf = self.pdf_var.get()

        if not tpl.is_file():
            messagebox.showerror("Error", f"Template not found:\n{tpl}"); return
        if not csv_path.is_file():
            messagebox.showerror("Error", f"CSV not found:\n{csv_path}"); return
        outdir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "cover_letter/make_letters.py",
            "--template", str(tpl),
            "--csv", str(csv_path),
            "--outdir", str(outdir),
        ]
        if pdf:
            cmd.append("--pdf")
        self._run_cmd(cmd, success_msg=f"Batch generated from {csv_path.name}")

    # ----- EMAIL TAB -----
    def _build_email(self):
        frm = self.email_tab

        ttk.Label(frm, text="Email template file:").grid(row=0, column=0, sticky="w", pady=6)
        # self.email_tpl_var = tk.StringVar(value=CFG["paths"]["email_template_dir"])
        self.email_tpl_var = tk.StringVar(value="outreach/email_templates/bulls.tpl.txt")
        ttk.Entry(frm, textvariable=self.email_tpl_var, width=52).grid(row=0, column=1, sticky="we")
        ttk.Button(frm, text="Browse", command=self._pick_email_template).grid(row=0, column=2, padx=6)

        ttk.Label(frm, text="Contacts CSV:").grid(row=1, column=0, sticky="w", pady=6)
        self.contacts_var = tk.StringVar(value=CFG["paths"]["contacts_csv"])
        ttk.Entry(frm, textvariable=self.contacts_var, width=52).grid(row=1, column=1, sticky="we")
        ttk.Button(frm, text="Browse", command=self._pick_contacts_csv).grid(row=1, column=2, padx=6)

        self.cc_var = tk.BooleanVar(value=bool(CFG["defaults"]["cc_myself"]))
        ttk.Checkbutton(frm, text="CC myself", variable=self.cc_var).grid(row=2, column=1, sticky="w", pady=4)
        self.dry_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Dry run (preview only)", variable=self.dry_var).grid(row=3, column=1, sticky="w", pady=4)

        btns = ttk.Frame(frm); btns.grid(row=4, column=0, columnspan=3, sticky="e", pady=10)
        ttk.Button(btns, text="Send Emails", command=self._send_emails).pack(side="left", padx=6)
        ttk.Button(btns, text="Open Log", command=self._open_email_log).pack(side="left", padx=6)

        for c in range(3):
            frm.grid_columnconfigure(c, weight=1)

    def _pick_email_template(self):
        # Allow choosing either a single file or a directory of templates
        p = filedialog.askopenfilename(title="Choose template file", filetypes=[("Text/Markdown", "*.txt *.md"), ("All", "*.*")])
        if p:
            self.email_tpl_var.set(p)

    def _pick_contacts_csv(self):
        p = filedialog.askopenfilename(title="Choose contacts CSV", filetypes=[("CSV", "*.csv")])
        if p: self.contacts_var.set(p)

    def _open_email_log(self):
        log = Path(CFG["paths"]["email_log"])
        if not log.exists():
            messagebox.showinfo("Info", f"Log not found yet:\n{log}")
            return
        open_in_finder(log)

    # def _send_emails(self):
    #     tpl = self.email_tpl_var.get().strip()
    #     contacts = self.contacts_var.get().strip()
    #     if not tpl:
    #         messagebox.showerror("Error", "Please choose an email template file."); return
    #     if not Path(contacts).is_file():
    #         messagebox.showerror("Error", f"Contacts CSV not found:\n{contacts}"); return

    #     cmd = [
    #         sys.executable, "email/mailer_gmail.py",
    #         "--template", tpl,
    #         "--contacts", contacts,
    #         "--cc", "1" if self.cc_var.get() else "0",
    #         "--log", CFG["paths"]["email_log"],
    #     ]
    #     if self.dry_var.get():
    #         cmd.append("--dry-run")
    #     self._run_cmd(cmd, success_msg="Emails processed")


    def _send_emails(self):
        tpl_path = Path(self.email_tpl_var.get()).expanduser()
        contacts_csv = Path(self.contacts_var.get()).expanduser()
        cc_everyone = bool(self.cc_var.get())
        preview_mode = bool(self.dry_var.get())
        sent_log_path = Path(CFG["paths"]["email_log"]).expanduser()

        # Validate paths
        if tpl_path.is_dir():
            messagebox.showerror(
                "Template required",
                f"You selected a folder.\n\nPlease choose a template *file* (.txt/.md):\n{tpl_path}"
            )
            return
        if not tpl_path.is_file():
            messagebox.showerror("Not found", f"Template file not found:\n{tpl_path}")
            return
        if not contacts_csv.is_file():
            messagebox.showerror("Not found", f"Contacts CSV not found:\n{contacts_csv}")
            return

        # Load dedupe set once
        try:
            sent_keys = mailer.load_sent_log_from_path(sent_log_path)
        except Exception as e:
            messagebox.showerror("Log error", f"Could not read log:\n{sent_log_path}\n\n{e}")
            return

        seen = set()
        n_sent = n_already = n_preview_skipped = 0

        try:
            with contacts_csv.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    msg = mailer.compose_email_from_row(row, tpl_path, cc_everyone)

                    # dedupe
                    if msg["key"] in sent_keys or msg["key"] in seen:
                        n_already += 1
                        continue
                    seen.add(msg["key"])

                    # GUI preview loop
                    if preview_mode:
                        action = preview_dialog(self, msg)   # self is the Tk root
                        if action == "cancel":
                            break
                        if action == "skip":
                            n_preview_skipped += 1
                            continue  # skip this row; continue to next

                    # Send + log
                    mailer.send_mail(
                        recipient=msg["to"],
                        subject=msg["subject"],
                        body=msg["body"],
                        cced=msg["cc_flag"],
                    )
                    mailer.append_to_log_path(sent_log_path, msg["key"], msg["cc_flag"])
                    n_sent += 1

            self.status_var.set(
                f"Emails sent: {n_sent} | already logged: {n_already} | skipped in preview: {n_preview_skipped}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"{e}\n\n{traceback.format_exc()}")
            self.status_var.set("Error.")


    # ----- shared runner -----
    def _run_cmd(self, cmd, success_msg="Done"):
        try:
            self.status_var.set("Running…")
            self.update_idletasks()
            subprocess.run(cmd, check=True)
            self.status_var.set(success_msg)
        except subprocess.CalledProcessError as e:
            self.status_var.set("Error.")
            messagebox.showerror("Command failed", f"{' '.join(cmd)}\n\nExit code: {e.returncode}")
        except Exception as e:
            self.status_var.set("Error.")
            messagebox.showerror("Error", f"{e}\n\n{traceback.format_exc()}")



if __name__ == "__main__":
    App().mainloop()
