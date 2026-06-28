from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    credentials_file: Path
    token_file: Path
    rules_file: Path
    db_file: Path
    attachments_dir: Path
    processed_label: str
    draft_only: bool
    query: str
    max_results: int
    allowed_senders: set[str]
    signature: str
    dashboard_host: str
    dashboard_port: int
    schedule_task_name: str
    schedule_interval_minutes: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        base_dir = Path.cwd()
        allowed = {
            item.strip().lower()
            for item in os.getenv("GMAIL_ALLOWED_SENDERS", "").split(",")
            if item.strip()
        }
        return cls(
            credentials_file=base_dir / os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
            token_file=base_dir / os.getenv("GMAIL_TOKEN_FILE", "token.json"),
            rules_file=base_dir / os.getenv("GMAIL_RULES_FILE", "responder_rules.json"),
            db_file=base_dir / os.getenv("APP_DB_FILE", "autoresponder.db"),
            attachments_dir=base_dir / os.getenv("GMAIL_ATTACHMENTS_DIR", "attachments"),
            processed_label=os.getenv("GMAIL_PROCESSED_LABEL", "auto_replied"),
            draft_only=_to_bool(os.getenv("GMAIL_DRAFT_ONLY"), True),
            query=os.getenv(
                "GMAIL_QUERY",
                "is:unread in:inbox -category:promotions -label:auto_replied",
            ),
            max_results=int(os.getenv("GMAIL_MAX_RESULTS", "10")),
            allowed_senders=allowed,
            signature=os.getenv("AUTO_REPLY_SIGNATURE", "Best regards,\nYour Name"),
            dashboard_host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
            dashboard_port=int(os.getenv("DASHBOARD_PORT", "8787")),
            schedule_task_name=os.getenv("SCHEDULE_TASK_NAME", "Gmail Auto Responder"),
            schedule_interval_minutes=int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "15")),
        )


@dataclass(slots=True)
class ReplyRule:
    name: str
    keywords: list[str]
    subject_contains: list[str]
    sender_contains: list[str]
    body_contains: list[str]
    reply_subject: str | None
    body_template: str
    attachments: list[Path]


@dataclass(slots=True)
class RuleSet:
    fallback_subject_prefix: str
    fallback_template: str
    rules: list[ReplyRule]

    @classmethod
    def load(cls, path: Path) -> "RuleSet":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rules_dir = path.parent
        rules = [
            ReplyRule(
                name=item["name"],
                keywords=item.get("keywords", []),
                subject_contains=item.get("subject_contains", []),
                sender_contains=item.get("sender_contains", []),
                body_contains=item.get("body_contains", []),
                reply_subject=item.get("reply_subject"),
                body_template=item["body_template"],
                attachments=[
                    (rules_dir / relative_path).resolve()
                    for relative_path in item.get("attachments", [])
                ],
            )
            for item in payload.get("rules", [])
        ]
        return cls(
            fallback_subject_prefix=payload.get("fallback_subject_prefix", "Re:"),
            fallback_template=payload["fallback_template"],
            rules=rules,
        )
