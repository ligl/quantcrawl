from __future__ import annotations

import json
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from urllib.request import Request, urlopen


class Notifier(Protocol):
    def send(self, title: str, body: str) -> None:
        ...


@dataclass(slots=True)
class EmailNotifier:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    sender: str
    to: str

    def send(self, title: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = title
        message["From"] = self.sender
        message["To"] = self.to
        message.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as client:
            client.starttls()
            if self.smtp_user:
                client.login(self.smtp_user, self.smtp_password)
            client.send_message(message)


@dataclass(slots=True)
class FeishuNotifier:
    webhook: str

    def send(self, title: str, body: str) -> None:
        payload = {
            "msg_type": "text",
            "content": {"text": f"{title}\n{body}"},
        }
        req = Request(
            self.webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10):
            return


@dataclass(slots=True)
class DingTalkNotifier:
    webhook: str

    def send(self, title: str, body: str) -> None:
        payload = {
            "msgtype": "text",
            "text": {"content": f"{title}\n{body}"},
        }
        req = Request(
            self.webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10):
            return
