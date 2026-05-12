from __future__ import annotations

from dataclasses import replace

from .models import ConnectionSettings, SshSettings


class SshTunnel:
    def __init__(self) -> None:
        self._forwarder = None

    @property
    def is_active(self) -> bool:
        return bool(self._forwarder and self._forwarder.is_active)

    @property
    def local_port(self) -> int | None:
        if not self._forwarder:
            return None
        return int(self._forwarder.local_bind_port)

    def open(self, ssh: SshSettings, db: ConnectionSettings) -> ConnectionSettings:
        if not ssh.enabled:
            return db
        if not ssh.host or not ssh.username:
            raise RuntimeError("SSH host와 계정을 입력하세요.")

        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError as exc:
            raise RuntimeError("SSH 터널 기능을 위해 sshtunnel 패키지가 필요합니다.") from exc

        self.close()

        ssh_kwargs = {
            "ssh_address_or_host": (ssh.host, ssh.port),
            "ssh_username": ssh.username,
            "remote_bind_address": (db.host or "127.0.0.1", db.port),
            "local_bind_address": ("127.0.0.1", 0),
        }
        if ssh.password:
            ssh_kwargs["ssh_password"] = ssh.password
        if ssh.key_file:
            ssh_kwargs["ssh_pkey"] = ssh.key_file
        if ssh.key_passphrase:
            ssh_kwargs["ssh_private_key_password"] = ssh.key_passphrase

        self._forwarder = SSHTunnelForwarder(**ssh_kwargs)
        self._forwarder.start()
        return replace(db, host="127.0.0.1", port=int(self._forwarder.local_bind_port))

    def close(self) -> None:
        if self._forwarder is not None:
            self._forwarder.stop()
            self._forwarder = None
