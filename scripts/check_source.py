"""Legacy identity, generated drift, pinned companion identity and bounded secret scans."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    r"-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"gh[pousr]_" + r"[A-Za-z0-9]{30,}",
    r"pypi-" + r"[A-Za-z0-9_-]{40,}",
    r"AKIA" + r"[A-Z0-9]{16}",
    r"[A-Z]:[\\/]Users[\\/][^\s]+",
    r"/ho" + r"me/[^\s/]+/",
]


def scan(text: str, name: str) -> None:
    assert not any(re.search(pattern, text) for pattern in PATTERNS), "Secret/local path detected in " + name


def main() -> None:
    manifest = json.loads((ROOT / "security" / "legacy-manifest.json").read_text())
    for filename, sha in manifest["files"].items():
        text = (ROOT / filename).read_text(encoding="utf-8").replace("\r\n", "\n")
        assert hashlib.sha256(text.encode()).hexdigest() == sha, "Legacy identity drift: " + filename
    pinned = ROOT / "src" / "cait_schema" / "accounting" / "fixtures" / "companions"
    for project in json.loads((pinned / "manifest.json").read_text()).values():
        for filename, item in project["files"].items():
            assert hashlib.sha256((pinned / filename).read_bytes()).hexdigest() == item["sha256"], filename
    outputs = [
        *(ROOT / "schemas" / "accounting").glob("*.json"),
        *(pinned.parent).glob("*.json"),
        ROOT / "docs" / "generated_reference.md",
    ]
    before = {path: path.read_bytes() for path in outputs}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate.py")], cwd=ROOT, check=True)
    assert all(path.read_bytes() == value for path, value in before.items()), "Generated file drift"
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    for name in names:
        path = ROOT / name
        if path.is_file():
            scan(path.read_text(encoding="utf-8", errors="replace"), name)
    print("Legacy identities, generated drift, companion pins and source scans passed")


if __name__ == "__main__":
    main()
