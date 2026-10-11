"""Content-addressed immutable raw store: cache/raw/ab/abcdef...<sha256>.<ext>."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_EXT = {
    "application/pdf": "pdf",
    "text/html": "html",
    "text/plain": "txt",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/json": "json",
    "text/csv": "csv",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BlobStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, sha: str, mime: str = "") -> Path:
        ext = _EXT.get(mime.split(";")[0].strip().lower(), "bin")
        return self.root / sha[:2] / f"{sha}.{ext}"

    def find(self, sha: str) -> Path | None:
        d = self.root / sha[:2]
        if d.is_dir():
            for p in d.iterdir():
                if p.name.startswith(sha + "."):
                    return p
        return None

    def put(self, data: bytes, mime: str) -> str:
        sha = sha256_bytes(data)
        if self.find(sha):
            return sha
        p = self.path_for(sha, mime)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".tmp{os.getpid()}")
        tmp.write_bytes(data)
        tmp.replace(p)
        return sha

    def read(self, sha: str) -> bytes:
        p = self.find(sha)
        if p is None:
            raise KeyError(sha)
        data = p.read_bytes()
        if sha256_bytes(data) != sha:
            raise OSError(f"blob {sha} is corrupt")
        return data
