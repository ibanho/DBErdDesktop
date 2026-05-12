from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .models import ConnectionSettings, SessionRecord, SshSettings


APP_DIR_NAME = "DBErdDesktop"
KEY_FILE_NAME = "session.key"
SESSIONS_FILE_NAME = "sessions.enc"


class SessionStore:
    def __init__(self, app_dir: Path | None = None) -> None:
        self.app_dir = app_dir or self._default_app_dir()
        self.key_path = self.app_dir / KEY_FILE_NAME
        self.sessions_path = self.app_dir / SESSIONS_FILE_NAME
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())

    @property
    def display_path(self) -> Path:
        return self.sessions_path

    def load(self) -> list[SessionRecord]:
        if not self.sessions_path.exists():
            return []
        try:
            encrypted = self.sessions_path.read_bytes()
            payload = self._fernet.decrypt(encrypted)
            data = json.loads(payload.decode("utf-8"))
        except InvalidToken as exc:
            raise RuntimeError("세션 파일을 복호화할 수 없습니다. 키 파일이 변경되었을 수 있습니다.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("세션 파일 형식이 올바르지 않습니다.") from exc

        sessions = []
        for item in data.get("sessions", []):
            sessions.append(
                SessionRecord(
                    name=item["name"],
                    db=ConnectionSettings(**item["db"]),
                    ssh=SshSettings(**item["ssh"]),
                    description=item.get("description", ""),
                )
            )
        return sessions

    def save_all(self, sessions: list[SessionRecord]) -> None:
        payload = {
            "version": 1,
            "sessions": [
                {
                    "name": session.name,
                    "description": session.description,
                    "db": asdict(session.db),
                    "ssh": asdict(session.ssh),
                }
                for session in sorted(sessions, key=lambda value: value.name.lower())
            ],
        }
        encrypted = self._fernet.encrypt(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        self.sessions_path.write_bytes(encrypted)

    def upsert(self, session: SessionRecord) -> None:
        sessions = [existing for existing in self.load() if existing.name != session.name]
        sessions.append(session)
        self.save_all(sessions)

    def delete(self, name: str) -> None:
        sessions = [existing for existing in self.load() if existing.name != name]
        self.save_all(sessions)

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def _default_app_dir(self) -> Path:
        root = os.environ.get("APPDATA")
        if root:
            return Path(root) / APP_DIR_NAME
        return Path.home() / f".{APP_DIR_NAME.lower()}"
