from __future__ import annotations

import re

from .config import RuleSet
from .models import GmailMessage, PreparedReply


def pick_reply(message: GmailMessage, rule_set: RuleSet, signature: str) -> PreparedReply:
    subject = message.subject.strip()
    subject_text = subject.lower()
    body_text = message.body.lower()
    sender_text = f"{message.from_header}\n{message.from_email}".lower()
    haystack = f"{subject_text}\n{body_text}\n{sender_text}"
    template_context = _build_template_context(message, signature)

    for rule in rule_set.rules:
        keyword_match = _matches_any(rule.keywords, haystack)
        subject_match = _matches_any(rule.subject_contains, subject_text)
        sender_match = _matches_any(rule.sender_contains, sender_text)
        body_match = _matches_any(rule.body_contains, body_text)
        attachment_match = _attachments_mentioned(rule.attachments, haystack)
        if keyword_match or subject_match or sender_match or body_match or attachment_match:
            return PreparedReply(
                subject=_resolve_reply_subject(rule.reply_subject, subject, rule_set.fallback_subject_prefix, template_context),
                body=rule.body_template.format(**template_context),
                rule_name=rule.name,
                generator="rules",
                attachments=_existing_attachments(rule.attachments),
            )

    return PreparedReply(
        subject=_ensure_reply_prefix(subject, rule_set.fallback_subject_prefix),
        body=rule_set.fallback_template.format(**template_context),
        rule_name="fallback",
        generator="rules",
        attachments=[],
    )


def _ensure_reply_prefix(subject: str, prefix: str) -> str:
    normalized = subject.lower().strip()
    if normalized.startswith("re:"):
        return subject
    return f"{prefix} {subject}".strip()


def _matches_any(terms: list[str], haystack: str) -> bool:
    return any(term.lower() in haystack for term in terms)


def _resolve_reply_subject(
    reply_subject: str | None,
    original_subject: str,
    prefix: str,
    template_context: dict[str, str],
) -> str:
    if not reply_subject:
        return _ensure_reply_prefix(original_subject, prefix)
    return reply_subject.format(**template_context).strip()


def _build_template_context(message: GmailMessage, signature: str) -> dict[str, str]:
    sender_name = _extract_sender_name(message.from_header, message.from_email)
    return {
        "signature": signature,
        "sender_name": sender_name,
        "sender_email": message.from_email,
        "original_subject": message.subject.strip(),
        "snippet": _compact_text(message.body, 220),
    }


def _extract_sender_name(from_header: str, from_email: str) -> str:
    if "<" in from_header:
        name = from_header.split("<", 1)[0].strip().strip('"').strip()
        if name:
            return name
    local_part = from_email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return local_part.title() if local_part else "there"


def _compact_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    return compact[: limit - 3] + "..." if len(compact) > limit else compact


def _existing_attachments(paths):
    return [path for path in paths if path.exists() and path.is_file()]


def _attachments_mentioned(paths, haystack: str) -> bool:
    normalized_haystack = _normalize_text(haystack)
    for path in paths:
        stem = _normalize_text(path.stem)
        filename = _normalize_text(path.name)
        if stem and stem in normalized_haystack:
            return True
        if filename and filename in normalized_haystack:
            return True
    return False


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
