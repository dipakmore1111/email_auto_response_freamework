from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class GmailMessage:
    message_id: str
    thread_id: str
    from_email: str
    from_header: str
    to_header: str
    subject: str
    body: str
    references: str
    in_reply_to: str
    auto_submitted: str
    date_header: str


@dataclass(slots=True)
class PreparedReply:
    subject: str
    body: str
    rule_name: str
    generator: Literal["ai", "rules"]
    attachments: list[Path]


@dataclass(slots=True)
class MessageOutcome:
    message_id: str
    from_email: str
    subject: str
    action: str
    rule_name: str
    generator: str
    preview: str


@dataclass(slots=True)
class RunResult:
    scanned: int
    replied: int
    skipped: int
    failed: int
    mode: str
    events: list[MessageOutcome]
