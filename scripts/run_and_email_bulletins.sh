#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/fumc/github/church-automation"
EMAIL_ENV_FILE="${HOME}/.church-automation/bulletins-email.env"
LOG_PREFIX="[bulletins-email]"

cd "$REPO_ROOT"

if [[ "${BULLETINS_EMAIL_SKIP_GENERATION:-0}" != "1" ]]; then
  echo "$LOG_PREFIX Starting bulletin generation at $(date -Iseconds)"
  uv run make-bulletins
  echo "$LOG_PREFIX Bulletin generation finished"
else
  echo "$LOG_PREFIX Skipping bulletin generation (BULLETINS_EMAIL_SKIP_GENERATION=1)"
fi

if [[ -f "$EMAIL_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$EMAIL_ENV_FILE"
  echo "$LOG_PREFIX Loaded email config from $EMAIL_ENV_FILE"
else
  echo "$LOG_PREFIX Missing config file: $EMAIL_ENV_FILE"
  echo "$LOG_PREFIX Create it from scripts/bulletins-email.env.example"
  exit 2
fi

: "${BULLETIN_SMTP_HOST:?BULLETIN_SMTP_HOST is required}"
: "${BULLETIN_SMTP_PORT:?BULLETIN_SMTP_PORT is required}"
: "${BULLETIN_SMTP_USER:?BULLETIN_SMTP_USER is required}"
: "${BULLETIN_SMTP_PASS:?BULLETIN_SMTP_PASS is required}"
: "${BULLETIN_EMAIL_TO:?BULLETIN_EMAIL_TO is required}"

RECENT_MINUTES="${BULLETIN_EMAIL_LOOKBACK_MINUTES:-180}"
SUBJECT="${BULLETIN_EMAIL_SUBJECT:-New Church Bulletins}"
BODY="${BULLETIN_EMAIL_BODY:-Attached are the newly generated bulletin PDFs.}"

mapfile -t PDF_FILES < <(find packages/bulletins/output -type f -name "Bulletin-*.pdf" -mmin "-${RECENT_MINUTES}" | sort)

if [[ ${#PDF_FILES[@]} -eq 0 ]]; then
  echo "$LOG_PREFIX No bulletin PDFs found in last ${RECENT_MINUTES} minutes"
  exit 0
fi

echo "$LOG_PREFIX Found ${#PDF_FILES[@]} bulletin PDF(s) to send"

python3 - "$SUBJECT" "$BODY" "${PDF_FILES[@]}" <<'PY'
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

subject = sys.argv[1]
body = sys.argv[2]
files = [Path(p) for p in sys.argv[3:]]

smtp_host = os.environ["BULLETIN_SMTP_HOST"]
smtp_port = int(os.environ["BULLETIN_SMTP_PORT"])
smtp_user = os.environ["BULLETIN_SMTP_USER"]
smtp_pass = os.environ["BULLETIN_SMTP_PASS"]
to_list = [x.strip() for x in os.environ["BULLETIN_EMAIL_TO"].split(",") if x.strip()]

if not to_list:
    raise SystemExit("BULLETIN_EMAIL_TO is empty after parsing")

msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = smtp_user
msg["To"] = ", ".join(to_list)
msg.set_content(body)

for path in files:
    with path.open("rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )

context = ssl.create_default_context()
with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as smtp:
    smtp.ehlo()
    smtp.starttls(context=context)
    smtp.ehlo()
    smtp.login(smtp_user, smtp_pass)
    smtp.send_message(msg)

print(f"Sent bulletin email to {len(to_list)} recipient(s) with {len(files)} attachment(s)")
PY

echo "$LOG_PREFIX Email send complete"
