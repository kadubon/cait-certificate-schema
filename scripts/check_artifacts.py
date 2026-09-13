"""Inspect sdist/wheel paths, required resources, secrets, and checksums."""

from __future__ import annotations

import hashlib
import tarfile
import zipfile
from pathlib import Path

from check_source import scan


def main() -> None:
    artifacts = sorted([*Path("dist").glob("*.whl"), *Path("dist").glob("*.tar.gz")])
    assert len(artifacts) == 2
    for path in artifacts:
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                data = {name: archive.read(name) for name in archive.namelist()}
            assert "cait_schema/schemas/accounting/report.schema.json" in data
            assert "cait_schema/accounting/fixtures/positive.json" in data
            assert "cait_schema/legacy_examples/arrival_record.json" in data
        else:
            with tarfile.open(path) as archive:
                data = {}
                for item in archive:
                    assert not item.issym() and not item.islnk()
                    if item.isfile():
                        source = archive.extractfile(item)
                        assert source is not None
                        data[item.name] = source.read()
            assert any(name.endswith("/schemas/accounting/report.schema.json") for name in data)
        for name, content in data.items():
            assert not name.startswith(("/", "\\")) and ".." not in Path(name).parts
            assert not any(part in {".env", ".git", ".venv", "__pycache__"} for part in Path(name).parts)
            assert not name.endswith((".pyc", ".key", ".pem"))
            scan(content.decode("utf-8", errors="replace"), name)
    manifest = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in artifacts)
    Path("dist/SHA256SUMS").write_text(manifest, encoding="utf-8")
    print(manifest)


if __name__ == "__main__":
    main()
