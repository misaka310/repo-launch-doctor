from __future__ import annotations

import tempfile
from pathlib import Path

from repo_launch_doctor.config import load_config


def fuzz_one_input(data: bytes) -> None:
    with tempfile.TemporaryDirectory() as temp:
        config_path = Path(temp) / ".repo-launch-doctor.json"
        config_path.write_bytes(data)
        try:
            load_config(Path(temp))
        except ValueError:
            # Invalid user configuration is an expected parser outcome.
            return


def main() -> None:
    import atheris
    import sys

    atheris.Setup(sys.argv, fuzz_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
