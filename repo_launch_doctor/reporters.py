from __future__ import annotations

import html
import json
from pathlib import Path

from .models import ScanReport


def render_json(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"


def render_markdown(report: ScanReport) -> str:
    lines = [
        "# Repo Launch Doctor Report",
        "",
        f"- Repository: `{report.root}`",
        f"- Generated: `{report.generated_at}`",
        f"- Files scanned: **{report.files_scanned}**",
        f"- Score: **{report.score}/100**",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    for severity, count in report.counts.items():
        lines.append(f"| {severity} | {count} |")

    lines.extend(["", "## Detected capabilities", ""])
    for key in ("project_type", "start_commands", "verification_commands", "ports", "health_endpoints"):
        value = report.metadata.get(key, [])
        lines.append(f"- **{key}:** `{value}`")

    lines.extend(["", "## Findings", ""])
    findings = report.sorted_findings()
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            lines.extend(
                [
                    f"### [{finding.severity}] {finding.title}",
                    "",
                    f"- Check: `{finding.check_id}`",
                    f"- Path: `{finding.path}`",
                    f"- Evidence: {finding.evidence}",
                    f"- Fix: {finding.recommendation}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: ScanReport) -> str:
    count_cards = "".join(
        f"<div class='metric'><span>{html.escape(severity)}</span><strong>{count}</strong></div>"
        for severity, count in report.counts.items()
    )
    finding_cards = []
    for finding in report.sorted_findings():
        severity_class = finding.severity.casefold()
        finding_cards.append(
            "".join(
                [
                    f"<article class='finding {severity_class}'>",
                    f"<div class='finding-head'><span class='badge'>{html.escape(finding.severity)}</span>",
                    f"<h3>{html.escape(finding.title)}</h3></div>",
                    f"<p><strong>Check:</strong> <code>{html.escape(finding.check_id)}</code></p>",
                    f"<p><strong>Path:</strong> <code>{html.escape(finding.path)}</code></p>",
                    f"<p><strong>Evidence:</strong> {html.escape(finding.evidence)}</p>",
                    f"<p><strong>Recommended fix:</strong> {html.escape(finding.recommendation)}</p>",
                    "</article>",
                ]
            )
        )
    if not finding_cards:
        finding_cards.append("<p class='empty'>No findings.</p>")

    capabilities = []
    for key in ("project_type", "start_commands", "verification_commands", "ports", "health_endpoints"):
        capabilities.append(
            f"<tr><th>{html.escape(key)}</th><td><code>{html.escape(str(report.metadata.get(key, [])))}</code></td></tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Repo Launch Doctor Report</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, Segoe UI, sans-serif; }}
    body {{ margin: 0; background: #0f172a; color: #e2e8f0; }}
    main {{ width: min(1100px, calc(100% - 32px)); margin: 32px auto 64px; }}
    .hero, .panel, .finding {{ background: #111c33; border: 1px solid #334155; border-radius: 18px; }}
    .hero {{ padding: 28px; display: grid; gap: 20px; }}
    h1, h2, h3, p {{ margin-top: 0; }}
    .score {{ font-size: clamp(42px, 8vw, 72px); font-weight: 800; line-height: 1; }}
    .muted {{ color: #94a3b8; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; }}
    .metric {{ background: #0b1325; border-radius: 12px; padding: 14px; display: flex; justify-content: space-between; }}
    .panel {{ margin-top: 18px; padding: 22px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; vertical-align: top; }}
    code {{ color: #bae6fd; overflow-wrap: anywhere; }}
    .finding {{ padding: 20px; margin-top: 12px; border-left-width: 7px; }}
    .finding.blocker {{ border-left-color: #ef4444; }}
    .finding.high {{ border-left-color: #f97316; }}
    .finding.medium {{ border-left-color: #eab308; }}
    .finding.low {{ border-left-color: #38bdf8; }}
    .finding.info {{ border-left-color: #22c55e; }}
    .finding-head {{ display: flex; align-items: baseline; gap: 10px; }}
    .badge {{ font-size: 12px; font-weight: 800; letter-spacing: .08em; background: #0b1325; border-radius: 999px; padding: 5px 9px; }}
    .empty {{ color: #86efac; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <p class="muted">Repo Launch Doctor</p>
      <h1>{html.escape(report.root)}</h1>
      <p class="muted">Generated {html.escape(report.generated_at)} · {report.files_scanned} readable files scanned</p>
    </div>
    <div><div class="score">{report.score}<span class="muted">/100</span></div></div>
    <div class="metrics">{count_cards}</div>
  </section>
  <section class="panel">
    <h2>Detected capabilities</h2>
    <table><tbody>{''.join(capabilities)}</tbody></table>
  </section>
  <section class="panel">
    <h2>Findings</h2>
    {''.join(finding_cards)}
  </section>
</main>
</body>
</html>
"""


def write_reports(report: ScanReport, output_directory: Path) -> dict[str, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_directory / "report.json",
        "markdown": output_directory / "report.md",
        "html": output_directory / "report.html",
    }
    paths["json"].write_text(render_json(report), encoding="utf-8")
    paths["markdown"].write_text(render_markdown(report), encoding="utf-8")
    paths["html"].write_text(render_html(report), encoding="utf-8")
    return paths
