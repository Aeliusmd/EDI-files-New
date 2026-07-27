from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Generator

import paramiko


@contextlib.contextmanager
def sftp_connection(
    host: str, port: int, username: str, password: str
) -> Generator[paramiko.SFTPClient, None, None]:
    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        yield sftp
    finally:
        if transport.is_active():
            transport.close()


def list_835_files(sftp: paramiko.SFTPClient, remote_path: str) -> list[str]:
    """Return only .835 filenames from remote_path. All other types ignored."""
    try:
        all_files = sftp.listdir(remote_path)
    except FileNotFoundError:
        return []
    return [f for f in all_files if f.lower().endswith(".835")]


def download_file(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    filename: str,
    local_dir: Path,
) -> Path:
    local_dir.mkdir(parents=True, exist_ok=True)
    remote_file = f"{remote_path.rstrip('/')}/{filename}"
    local_path = local_dir / filename
    sftp.get(remote_file, str(local_path))
    return local_path
