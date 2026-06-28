from __future__ import annotations

import base64
import mimetypes
import re
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .models import GmailMessage, PreparedReply

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
EMAIL_PATTERN = re.compile(r"<([^>]+)>")


class GmailClient:
    def __init__(self, credentials_file: Path, token_file: Path) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = build("gmail", "v1", credentials=self._load_credentials())
        profile = self.service.users().getProfile(userId="me").execute()
        self.account_email = profile["emailAddress"].lower()

    def _load_credentials(self) -> Credentials:
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def ensure_label(self, label_name: str) -> str:
        labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
        for label in labels:
            if label["name"].lower() == label_name.lower():
                return label["id"]
        created = self.service.users().labels().create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        return created["id"]

    def list_messages(self, query: str, max_results: int) -> list[GmailMessage]:
        response = self.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()
        messages = response.get("messages", [])
        return [self.get_message(item["id"]) for item in messages]

    def get_message(self, message_id: str) -> GmailMessage:
        payload = self.service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()
        headers = {item["name"].lower(): item["value"] for item in payload["payload"].get("headers", [])}
        body = _extract_body(payload["payload"])
        from_header = headers.get("from", "")
        return GmailMessage(
            message_id=payload["id"],
            thread_id=payload["threadId"],
            from_email=_extract_email(from_header),
            from_header=from_header,
            to_header=headers.get("to", ""),
            subject=headers.get("subject", "(no subject)"),
            body=body,
            references=headers.get("references", ""),
            in_reply_to=headers.get("message-id", ""),
            auto_submitted=headers.get("auto-submitted", ""),
            date_header=headers.get("date", ""),
        )

    def create_reply(self, original: GmailMessage, reply: PreparedReply, send_now: bool) -> str:
        message = EmailMessage()
        message["To"] = original.from_header
        message["Subject"] = reply.subject
        if original.in_reply_to:
            message["In-Reply-To"] = original.in_reply_to
            message["References"] = " ".join(
                part for part in [original.references, original.in_reply_to] if part
            ).strip()
        message.set_content(reply.body)
        for attachment_path in reply.attachments:
            self._attach_file(message, attachment_path)

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        body = {"raw": encoded, "threadId": original.thread_id}
        if send_now:
            result = self.service.users().messages().send(userId="me", body=body).execute()
            return result["id"]
        result = self.service.users().drafts().create(
            userId="me",
            body={"message": body},
        ).execute()
        return result["id"]

    def _attach_file(self, message: EmailMessage, attachment_path: Path) -> None:
        mime_type, _ = mimetypes.guess_type(attachment_path.name)
        main_type, sub_type = (mime_type or "application/octet-stream").split("/", 1)
        with attachment_path.open("rb") as file_handle:
            message.add_attachment(
                file_handle.read(),
                maintype=main_type,
                subtype=sub_type,
                filename=attachment_path.name,
            )

    def mark_processed(self, message_id: str, label_id: str) -> None:
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]},
        ).execute()


def _extract_email(header_value: str) -> str:
    match = EMAIL_PATTERN.search(header_value)
    if match:
        return match.group(1).lower()
    return header_value.strip().lower()


def _extract_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and part.get("body", {}).get("data"):
                return _decode_body(part["body"]["data"])
        for part in payload["parts"]:
            nested = _extract_body(part)
            if nested:
                return nested
        return ""
    data = payload.get("body", {}).get("data")
    return _decode_body(data) if data else ""


def _decode_body(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="ignore")
