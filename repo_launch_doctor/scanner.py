from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .checks import run_checks
from .config import load_config
from .inventory import collect_inventory
from .models import ScanReport
from .reporters import write_reports


def scan_repository(
    root: Path | str,
    output_directory: Path | str | None = None,
) -> ScanReport:
    root_path = Path(root).expanduser().resolve()
    config = load_config(root_path)
    inventory = collect_inventory(root_path, config)
    findings, metadata = run_checks(inventory, config)
    report = ScanReport(
        root=str(root_path),
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        files_scanned=len(inventory.files),
        findings=findings,
        metadata=metadata,
    )
    if output_directory is not None:
        write_reports(report, Path(output_directory).expanduser().resolve())
    return report
