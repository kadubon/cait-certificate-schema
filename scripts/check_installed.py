"""Install built wheel externally with no cache; execute offline checks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    (wheel,) = Path("dist").glob("*.whl")
    uv = shutil.which("uv")
    assert uv
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("UV_", "PIP_")) and k not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }
    env["PIP_CONFIG_FILE"] = os.devnull
    with tempfile.TemporaryDirectory(prefix="cait-installed-") as directory:
        root = Path(directory)
        subprocess.run([uv, "venv", "--python", "3.13", "--seed", str(root / "env")], env=env, check=True)
        python = root / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--no-cache-dir",
                "--index-url",
                "https://pypi.org/simple",
                str(wheel.resolve()),
            ],
            cwd=root,
            env=env,
            check=True,
        )
        subprocess.run([str(python), "-m", "pip", "check"], cwd=root, env=env, check=True)
        output = subprocess.check_output(
            [str(python), "-I", "-m", "cait_schema.accounting.installed_check"], cwd=root, env=env, text=True
        )
        assert json.loads(output)["offline"]
        print(output)


if __name__ == "__main__":
    main()
