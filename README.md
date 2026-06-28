# Gmail Automated Reply Framework

A Python framework for automatically replying to Gmail messages with local, rule-based templates, a dashboard, and Windows scheduling support.

## What It Does

- Reads matching Gmail messages with the Gmail API
- Generates replies from local rules with no AI or API key required
- Personalizes templates with sender and subject placeholders
- Creates draft replies or sends them directly
- Labels processed messages to avoid duplicate responses
- Stores run history in SQLite for the dashboard
- Includes a local web dashboard
- Includes Windows Task Scheduler setup scripts

## Setup

1. Create a Google Cloud project and enable the Gmail API.
2. Create OAuth desktop app credentials and download the file as `credentials.json`.
3. Copy `.env.example` to `.env`.
4. Copy `responder_rules.example.json` to `responder_rules.json`.
5. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## First Run

Run in dry mode first:

```bash
python -m gmail_autoresponder --dry-run
```

Create Gmail drafts:

```bash
python -m gmail_autoresponder
```

Send replies automatically:

```bash
python -m gmail_autoresponder --send
```

Start the dashboard:

```bash
python -m gmail_autoresponder.dashboard
```

Open `http://127.0.0.1:8787`

## Environment Variables

- `GMAIL_CREDENTIALS_FILE`: OAuth client credentials JSON
- `GMAIL_TOKEN_FILE`: OAuth token cache JSON
- `GMAIL_RULES_FILE`: Rule file path
- `GMAIL_PROCESSED_LABEL`: Label added after processing
- `GMAIL_DRAFT_ONLY`: `true` or `false`
- `GMAIL_QUERY`: Gmail search query for target messages
- `GMAIL_MAX_RESULTS`: Max messages per run
- `GMAIL_ALLOWED_SENDERS`: Optional comma-separated allowlist
- `AUTO_REPLY_SIGNATURE`: Signature appended to templates
- `APP_DB_FILE`: SQLite database for run history
- `DASHBOARD_HOST`: Local dashboard host
- `DASHBOARD_PORT`: Local dashboard port
- `SCHEDULE_TASK_NAME`: Windows scheduled task name
- `SCHEDULE_INTERVAL_MINUTES`: Task interval

## Rule File

Rules live in `responder_rules.json`. Each rule can match:

- `keywords`: checked against subject, body, sender name, and sender email
- `subject_contains`: checked only against subject
- `sender_contains`: checked against sender name and sender email
- `body_contains`: checked only against the email body
- `reply_subject`: optional custom subject template
- `body_template`: reply template

The first matching rule wins. If nothing matches, the framework uses `fallback_template`.

Available template placeholders:

- `{signature}`
- `{sender_name}`
- `{sender_email}`
- `{original_subject}`
- `{snippet}`

## Automation

- Use `scripts\run_responder.ps1 -Send` for live automatic replies
- Use `scripts\register_auto_run.ps1` to run it every few minutes with Windows Task Scheduler
- The scheduled task runs the local framework automatically after Gmail OAuth has been connected once

## Notes

- No OpenAI key or other AI key is needed.
- Gmail still requires Google OAuth credentials because sending email is done through Gmail itself.
- The framework skips messages sent by the authenticated account.
- It ignores obvious auto-generated emails when the headers expose that.
- Labeling is used to prevent duplicate replies.
- Start with draft mode until you trust the rules.
