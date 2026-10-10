from __future__ import annotations

import json
import sys

import atheris

with atheris.instrument_imports():
    from repo_launch_doctor.schema import validate_report_payload


def TestOneInput(data: bytes) -> None:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return
    try:
        validate_report_payload(payload)
    except (TypeError, ValueError, KeyError, RecursionError):
        # Invalid untrusted report shapes are expected; crashes outside these
        # validation failures should still be surfaced by Atheris.
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
