from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pattern:
    kind: str
    name: str
    regex: re.Pattern[str]


SECRET_PATTERNS = [
    Pattern("secret", "aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Pattern("secret", "github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    Pattern("secret", "openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    Pattern("secret", "google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    Pattern("secret", "slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    Pattern("secret", "huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    Pattern("secret", "stripe-live-key", re.compile(r"\bsk_live_[0-9A-Za-z]{16,}\b")),
    Pattern("secret", "sendgrid-key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b")),
    Pattern("secret", "private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    Pattern("secret", "discord-webhook", re.compile(r"https://discord(?:app)?\.com/api/webhooks/[0-9]{10,}/[A-Za-z0-9._-]{20,}")),
]

PRIVACY_PATTERNS = [
    Pattern("privacy", "windows-user-path", re.compile(r"\b[A-Za-z]:[\\/]Users[\\/][^\\/\s\"'<>]+", re.IGNORECASE)),
    Pattern("privacy", "local-dev-path", re.compile(r"\b[A-Za-z]:[\\/]00_dev[\\/]", re.IGNORECASE)),
    Pattern("privacy", "private-ip", re.compile(r"\b(?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)\d{1,3}(?:\.\d{1,3}){1,2}\b")),
    Pattern("privacy", "machine-hostname", re.compile(r"\bDESK2\b", re.IGNORECASE)),
    Pattern("privacy", "specific-gpu-model", re.compile(r"\b(?:RTX\s*3060|RTX\s*5060\s*Ti)\b", re.IGNORECASE)),
    Pattern("privacy", "portfolio-fund-name", re.compile(r"(?:ｅＭＡＸＩＳ|eMAXIS\s+Slim|ニッセイＳＯＸ|ＳＢＩ日本高配当)", re.IGNORECASE)),
]


def annotation(level: str, repo_name: str, pattern: Pattern, commit: str, path: str) -> None:
    safe_path = path.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    message = f"{repo_name}: historical {pattern.kind} marker '{pattern.name}' at commit {commit[:12]} (value redacted)"
    print(f"::{level} file={safe_path or 'unknown'}::{message}")


def scan(repo_dir: Path, repo_name: str) -> tuple[int, int]:
    proc = subprocess.Popen(
        ["git", "-C", str(repo_dir), "log", "--all", "-p", "--no-ext-diff", "--no-color", "--format=COMMIT:%H"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    current_commit = "unknown"
    current_path = "unknown"
    seen: set[tuple[str, str, str]] = set()
    secret_count = 0
    privacy_count = 0

    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        if line.startswith("COMMIT:"):
            current_commit = line[7:].strip() or "unknown"
            current_path = "unknown"
            continue
        if line.startswith("+++ b/"):
            current_path = line[6:].strip() or "unknown"
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        for pattern in (*SECRET_PATTERNS, *PRIVACY_PATTERNS):
            if not pattern.regex.search(added):
                continue
            key = (pattern.name, current_commit, current_path)
            if key in seen:
                continue
            seen.add(key)
            if pattern.kind == "secret":
                secret_count += 1
                annotation("error", repo_name, pattern, current_commit, current_path)
            else:
                privacy_count += 1
                annotation("warning", repo_name, pattern, current_commit, current_path)

    if proc.stderr is not None:
        proc.stderr.read()
    return_code = proc.wait()
    if return_code:
        raise RuntimeError(f"git log failed for {repo_name}: exit {return_code}")
    print(f"AUDIT_SUMMARY repo={repo_name} secret={secret_count} privacy={privacy_count}")
    return secret_count, privacy_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True, type=Path)
    parser.add_argument("--repo-name", required=True)
    args = parser.parse_args()
    secrets, _privacy = scan(args.repo_dir, args.repo_name)
    return 1 if secrets else 0


if __name__ == "__main__":
    raise SystemExit(main())
