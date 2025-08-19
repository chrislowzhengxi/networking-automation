from __future__ import annotations

import sys
import subprocess
from pathlib import Path
import typer
from typer.models import OptionInfo
from rich import print as rprint
from InquirerPy import inquirer
import yaml
from pydantic import BaseModel


def _norm_opt(v, default=None):
    # If Typer's OptionInfo leaked into a direct call, treat as unset
    return default if isinstance(v, OptionInfo) or v is None else v


app = typer.Typer(help="Email + cover letter automation, but friendly.")

# ----- config -----
class Paths(BaseModel):
    cover_template: str
    cover_outdir: str
    email_log: str
    email_template_dir: str
    contacts_csv: str

class Defaults(BaseModel):
    pdf: bool = True
    cc_myself: bool = False

class Config(BaseModel):
    sender_name: str
    sender_email: str
    paths: Paths
    defaults: Defaults

def load_config(cfg_path: str = "config.yaml") -> Config:
    with open(cfg_path, "r") as f:
        return Config(**yaml.safe_load(f))

CFG = load_config()



def _check(path: str | Path, kind: str = "file"):
    p = Path(path)
    if kind == "file" and not p.is_file():
        typer.secho(f"Missing {kind}: {p}", fg=typer.colors.RED)
        raise typer.Exit(1)
    if kind == "dir" and not p.is_dir():
        typer.secho(f"Missing {kind}: {p}", fg=typer.colors.RED)
        raise typer.Exit(1)
    return p

# ----- cover letters -----
cover = typer.Typer(help="Generate cover letters")
app.add_typer(cover, name="cover")

@cover.command("make")
def cover_make(
    company: str = typer.Option(None, help="Company name"),
    position: str = typer.Option(None, help="Position title"),
    template: str = typer.Option(None, help="Path to .docx template"),
    outdir: str = typer.Option(None, help="Output directory"),
    pdf: bool = typer.Option(None, help="Export PDF"),
    open_out: bool = typer.Option(True, help="Reveal output folder")
):
    template = _norm_opt(template, CFG.paths.cover_template)
    outdir = _norm_opt(outdir, CFG.paths.cover_outdir)
    pdf = CFG.defaults.pdf if pdf is None else pdf

    # basic validation for wizard typos
    company = (company or "").strip()
    position = (position or "").strip()
    if not company or company.startswith("source "):
        typer.secho("Please enter a valid company name.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if not position:
        typer.secho("Please enter a valid position.", fg=typer.colors.RED)
        raise typer.Exit(1)

    _check(template, "file")
    Path(outdir).mkdir(parents=True, exist_ok=True)

    # Call your existing script exactly like you did before:
    cmd = [
        sys.executable,  # was "python3"
        "cover_letter/make_letters.py",
        "--template", template,
        "--company", company,
        "--position", position,
        "--outdir", outdir,
    ]
    if pdf:
        cmd.append("--pdf")

    rprint(f"[bold]Running:[/bold] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    if open_out:
        # macOS: open Finder. On Linux use 'xdg-open', Windows 'start'.
        subprocess.run(["open", outdir])

@cover.command("wizard")
def cover_wizard():
    """Interactive cover letter generator (no auto-defaults)."""
    # Always start blank
    while True:
        company = inquirer.text(message="Company name:").execute().strip()
        if company and not company.startswith("source "):
            break
        typer.secho("Please enter a valid company name.", fg=typer.colors.RED)

    position = inquirer.text(
        message="Position title:",
        default="Software Engineer"
    ).execute().strip()

    as_pdf = inquirer.confirm(
        message="Export to PDF?",
        default=CFG.defaults.pdf
    ).execute()

    cover_make(company=company, position=position, pdf=as_pdf, open_out=True)


# ----- email -----
email = typer.Typer(help="Send or preview emails")
app.add_typer(email, name="email")

@email.command("send")
def email_send(
    template: str = typer.Option(None, help="Which template file to use"),
    contacts: str = typer.Option(None, help="CSV of contacts to send to"),
    cc_myself: bool = typer.Option(None, help="CC me on every email"),
    dry_run: bool = typer.Option(False, help="Preview without sending")
):
    template = _norm_opt(template, CFG.paths.email_template_dir)
    contacts = _norm_opt(contacts, CFG.paths.contacts_csv)
    cc = CFG.defaults.cc_myself if cc_myself is None else cc_myself

    # Pick a template file interactively if a directory was passed
    tpath = Path(template)
    if tpath.is_dir():
        choices = [p.name for p in tpath.glob("*.txt")] + [p.name for p in tpath.glob("*.md")]
        if not choices:
            typer.secho("No templates found in email_template_dir", fg=typer.colors.RED)
            raise typer.Exit(1)
        picked = inquirer.select(message="Choose an email template:", choices=choices).execute()
        template = str(tpath / picked)

    # Wrap your existing mailer script. Adjust args to match your file.
    cmd = [
        "python3", "src/mailer_gmail.py",
        "--template", template,
        "--contacts", contacts,
        "--cc", str(int(cc)),
        "--log", CFG.paths.email_log
    ]
    if dry_run:
        cmd.append("--dry-run")

    rprint(f"[bold]Running:[/bold] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

@email.command("wizard")
def email_wizard():
    """Pick template and recipients interactively, then send."""
    email_send(dry_run=False)

# ----- logs -----
@app.command("log")
def log_show():
    """Open the send log in your default CSV viewer."""
    _check(CFG.paths.email_log, "file")
    subprocess.run(["open", CFG.paths.email_log])

if __name__ == "__main__":
    app()
