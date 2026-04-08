import smtplib
import ssl
import sys
import re
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from getpass import getpass

# ── Anti-spam timing ─────────────────────────────────────────────────────────
BASE_DELAY_SECONDS = 2       
# Minimum delay between emails
JITTER_SECONDS     = 1.5     
# Random extra delay


def load_recipients(filepath: str) -> list[tuple[str, str]]:
# Lines starting with '#' and blank lines are ignored
    recipients = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    print(f"  [!] Line {line_num} skipped (invalid format): '{line}'")
                    continue
                name, _, email = line.partition(":")
                name = name.strip()
                email = email.strip()
                if name and email:
                    recipients.append((name, email))
                else:
                    print(f"  [!] Line {line_num} skipped (empty name or email): '{line}'")
    except FileNotFoundError:
        print(f"\n[ERROR] File not found: '{filepath}'")
        sys.exit(1)
    return recipients


def personalize(text: str, name: str) -> str:
    return text.replace("[user]", name)


def html_to_plaintext(html: str) -> str:
    """Strip HTML tags to produce a plain-text fallback."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_message(
    sender_email: str,
    sender_name: str,
    recipient_email: str,
    subject: str,
    body: str,
    is_html: bool,
) -> MIMEMultipart:
# Build a MIME message with anti-spam headers.
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{sender_name} <{sender_email}>"
    msg["To"]      = recipient_email

    # ── Anti-spam headers ─────────────────────────────────────────────────────
    # Signals this is a one-to-one transactional email, not a bulk blast
    msg["Precedence"]                  = "bulk"
    msg["X-Mailer"]                    = "Python/smtplib"
    # List-Unsubscribe helps deliverability with major providers
    msg["List-Unsubscribe"]            = f"<mailto:{sender_email}?subject=Unsubscribe>"
    msg["List-Unsubscribe-Post"]       = "List-Unsubscribe=One-Click"

    if is_html:
        plain_body = html_to_plaintext(body)
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

    return msg


def send_emails(
    sender_email: str,
    sender_name: str,
    sender_password: str,
    smtp_host: str,
    smtp_port: int,
    subject_template: str,
    body_template: str,
    is_html: bool,
    recipients: list[tuple[str, str]],
):
    context = ssl.create_default_context()
    sent   = 0
    failed = 0
    total  = len(recipients)

    print(f"\nConnecting to {smtp_host}:{smtp_port} ...")
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(sender_email, sender_password)
            print("Login successful.\n")

            for idx, (name, email) in enumerate(recipients, 1):
                subject = personalize(subject_template, name)
                body    = personalize(body_template, name)

                msg = build_message(
                    sender_email=sender_email,
                    sender_name=sender_name,
                    recipient_email=email,
                    subject=subject,
                    body=body,
                    is_html=is_html,
                )

                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    print(f"  [✓] ({idx}/{total}) Sent  → {name} <{email}>")
                    sent += 1
                except Exception as e:
                    print(f"  [✗] ({idx}/{total}) Failed → {name} <{email}>  ({e})")
                    failed += 1

                # ── Delay before next email (skip after last one) ─────────────
                if idx < total:
                    delay = BASE_DELAY_SECONDS + random.uniform(0, JITTER_SECONDS)
                    print(f"      ⏳ Waiting {delay:.1f}s before next send...")
                    time.sleep(delay)

    except smtplib.SMTPAuthenticationError:
        print("[ERROR] Authentication failed. Check your email/password (or app password).")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")
        sys.exit(1)

    print(f"\nDone. Sent: {sent}  |  Failed: {failed}")


def multiline_input(prompt: str) -> str:
    """Collect multi-line input; user signals end with a blank line."""
    print(prompt)
    lines = []
    while True:
        line = input()
        if line == "":
            if lines:
                break
            else:
                continue
        lines.append(line)
    return "\n".join(lines)


def main():
    print("=" * 50)
    print("        Mass Email Sender")
    print("=" * 50)

    # ── SMTP configuration ──────────────────────────────
    print("\n[SMTP Configuration]")
    smtp_host     = input("SMTP host (e.g. smtp.gmail.com): ").strip() or "smtp.gmail.com"
    smtp_port_str = input("SMTP port (default 465): ").strip()
    smtp_port     = int(smtp_port_str) if smtp_port_str.isdigit() else 465

    # ── Sender credentials ──────────────────────────────
    print("\n[Sender Credentials]")
    sender_email = input("Your email address   : ").strip()
    sender_name  = input("Your display name    : ").strip() or sender_email
    sender_password = getpass("Your password (hidden): ")

    # ── Email content ───────────────────────────────────
    print("\n[Email Content]")
    print("Tip: use [user] anywhere to insert the recipient's name.\n")

    subject = input("Title>> ").strip()
    body    = multiline_input("Mail>> (enter your message; leave a blank line when done)")

    # ── Recipient list ───────────────────────────────────
    print("\n[Recipient List]")
    txt_path   = input("User:mail txt file>> ").strip()
    recipients = load_recipients(txt_path)

    if not recipients:
        print("\n[ERROR] No valid recipients found in the file.")
        sys.exit(1)

    print(f"\n{len(recipients)} recipient(s) loaded:")
    for name, email in recipients:
        print(f"  • {name} <{email}>")

    # ── Confirmation ─────────────────────────────────────
    confirm = input(f"\nSend {len(recipients)} email(s)? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    # ── Send ─────────────────────────────────────────────
    send_emails(
        sender_email=sender_email,
        sender_name=sender_name,
        sender_password=sender_password,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        subject_template=subject,
        body_template=body,
        recipients=recipients,
        is_html=True,
    )


if __name__ == "__main__":
    main()
