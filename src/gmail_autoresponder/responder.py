from __future__ import annotations

from .config import AppConfig, RuleSet
from .gmail_client import GmailClient
from .models import GmailMessage, MessageOutcome, RunResult
from .rules import pick_reply
from .storage import RunStore


class AutoResponder:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.rule_set = RuleSet.load(config.rules_file)
        self.store = RunStore(config.db_file)
        self.gmail = GmailClient(config.credentials_file, config.token_file)
        self.processed_label_id = self.gmail.ensure_label(config.processed_label)

    def run(self, dry_run: bool = False, send_now: bool = False) -> RunResult:
        mode = "dry-run" if dry_run else "send" if send_now else "draft"
        run_id = self.store.start_run(mode=mode, query_text=self.config.query)
        messages = self.gmail.list_messages(self.config.query, self.config.max_results)
        scanned = len(messages)
        replied = 0
        skipped = 0
        failed = 0
        events: list[MessageOutcome] = []

        try:
            for message in messages:
                if not self._should_reply(message):
                    skipped += 1
                    event = MessageOutcome(
                        message_id=message.message_id,
                        from_email=message.from_email,
                        subject=message.subject,
                        action="skipped",
                        rule_name="n/a",
                        generator="n/a",
                        preview="Message skipped by safety filters.",
                    )
                    events.append(event)
                    self.store.add_event(run_id, event)
                    continue

                try:
                    reply = self._prepare_reply(message)
                    if dry_run:
                        print(f"[DRY RUN] {message.from_email} -> {reply.rule_name} :: {reply.subject}")
                        action = "previewed"
                    else:
                        response_id = self.gmail.create_reply(
                            original=message,
                            reply=reply,
                            send_now=send_now,
                        )
                        self.gmail.mark_processed(message.message_id, self.processed_label_id)
                        action = "sent" if send_now else "drafted"
                        print(f"[{action.upper()}] {message.from_email} -> {reply.rule_name} :: {response_id}")

                    replied += 1
                    event = MessageOutcome(
                        message_id=message.message_id,
                        from_email=message.from_email,
                        subject=message.subject,
                        action=action,
                        rule_name=reply.rule_name,
                        generator=reply.generator,
                        preview=_preview_text(reply.body),
                    )
                except Exception as exc:
                    failed += 1
                    event = MessageOutcome(
                        message_id=message.message_id,
                        from_email=message.from_email,
                        subject=message.subject,
                        action="failed",
                        rule_name="error",
                        generator="error",
                        preview=str(exc)[:280],
                    )
                events.append(event)
                self.store.add_event(run_id, event)
        except Exception as exc:
            result = RunResult(
                scanned=scanned,
                replied=replied,
                skipped=skipped,
                failed=failed + 1,
                mode=mode,
                events=events,
            )
            self.store.finish_run(run_id, result, status="failed", error_text=str(exc)[:500])
            raise

        result = RunResult(
            scanned=scanned,
            replied=replied,
            skipped=skipped,
            failed=failed,
            mode=mode,
            events=events,
        )
        self.store.finish_run(run_id, result, status="completed")
        return result

    def _should_reply(self, message: GmailMessage) -> bool:
        if message.from_email == self.gmail.account_email:
            return False
        if not message.from_email or "no-reply" in message.from_email or "noreply" in message.from_email:
            return False
        if message.auto_submitted and message.auto_submitted.lower() != "no":
            return False
        if self.config.allowed_senders and message.from_email not in self.config.allowed_senders:
            return False
        return True

    def _prepare_reply(self, message: GmailMessage):
        return pick_reply(message, self.rule_set, self.config.signature)


def _preview_text(value: str, limit: int = 280) -> str:
    compact = " ".join(value.split())
    return compact[: limit - 3] + "..." if len(compact) > limit else compact
