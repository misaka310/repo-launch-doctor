from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .constants import SEVERITY_ORDER
from .models import Finding, ScanReport

VERDICT_LABELS = {
    "PASS": "静的公開前チェックに合格",
    "PASS_WITH_NOTES": "静的チェック合格・改善点あり",
    "FAIL": "静的チェックで公開前の修正が必要",
    "INCOMPLETE": "静的検査未完了",
}

SEVERITY_LABELS = {
    "BLOCKER": "公開を止める問題",
    "HIGH": "重大",
    "MEDIUM": "改善推奨",
    "LOW": "軽微",
    "INFO": "情報",
}

ASSURANCE_COVERAGE_LABELS = {
    "repository_files": "リポジトリファイル",
    "readme_and_entrypoints": "README・起動入口",
    "git_tracking": "Git追跡・ignore状態",
    "git_history": "Git履歴",
    "runtime": "実際の起動・動作",
    "dependencies": "依存関係・脆弱性",
    "github_settings": "GitHub設定",
    "binary_contents": "バイナリ・画像・PDF等の内部",
}

COVERAGE_LABELS = {
    "scan_complete": "検査完了",
    "git_tracked_file_detection": "Git追跡判定",
    "git_ignore_detection": "ignore判定",
    "ignore_detection_source": "ignore判定元",
    "skipped_reasons": "内容を読まなかった理由",
    "ignored_paths": "内容読取の除外パス",
    "ignored_checks": "無効化したチェック",
    "suppressed_findings": "抑制したFinding",
    "incomplete_reasons": "未完了の理由",
    "scan_errors": "読取エラー",
}

SIGNAL_LABELS = {
    "project_type": "プロジェクト種別",
    "start_commands": "起動入口",
    "verification_commands": "検証コマンド",
    "ports": "ポート",
    "health_endpoints": "ヘルスチェック",
}


def render_json(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"


def _display_value(value: object) -> str:
    if isinstance(value, list):
        return "なし" if not value else ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "なし" if not value else ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value)


def _assurance_coverage(report: ScanReport) -> dict[str, object]:
    coverage = report.metadata.get("coverage", {})
    return coverage if isinstance(coverage, dict) else {}


def render_markdown(report: ScanReport) -> str:
    score = "N/A（検査未完了）" if report.score is None else f"{report.score}/100"
    assurance = str(report.metadata.get("assurance_level", "static"))
    coverage = _assurance_coverage(report)
    lines = [
        "# Repo Launch Doctor レポート",
        "",
        f"- 保証レベル: **{assurance}**",
        f"- 静的判定: **{report.verdict} — {VERDICT_LABELS[report.verdict]}**",
        f"- 対象: `{report.repository}`",
        f"- 生成日時: `{report.generated_at}`",
        f"- 読み取ったテキスト: **{report.files_scanned}**",
        f"- 確認したファイルパス: **{report.paths_discovered}**",
        f"- 静的スコア: **{score}**",
        "",
        "> この判定は静的検査の結果です。`not_checked` の領域はPASSの保証範囲に含まれません。",
        "",
        "## 保証範囲",
        "",
        "| 領域 | 状態 |",
        "|---|---|",
    ]
    for key, label in ASSURANCE_COVERAGE_LABELS.items():
        lines.append(f"| {label} (`{key}`) | `{coverage.get(key, 'not_reported')}` |")

    lines.extend(
        [
            "",
            "## 重要度別件数",
            "",
            "| 重要度 | 件数 |",
            "|---|---:|",
        ]
    )
    for severity, count in report.counts.items():
        lines.append(f"| {severity} | {count} |")

    lines.extend(["", "## 詳細な検査範囲", ""])
    coverage_keys = (
        "scan_complete",
        "git_tracked_file_detection",
        "git_ignore_detection",
        "ignore_detection_source",
        "skipped_reasons",
        "ignored_paths",
        "ignored_checks",
        "suppressed_findings",
        "incomplete_reasons",
        "scan_errors",
    )
    for key in coverage_keys:
        label = COVERAGE_LABELS[key]
        lines.append(
            f"- **{label} (`{key}`):** `{_display_value(report.metadata.get(key, []))}`"
        )

    lines.extend(["", "## 検出した実行・検証シグナル", ""])
    for key in (
        "project_type",
        "start_commands",
        "verification_commands",
        "ports",
        "health_endpoints",
    ):
        label = SIGNAL_LABELS[key]
        lines.append(
            f"- **{label} (`{key}`):** `{_display_value(report.metadata.get(key, []))}`"
        )

    lines.extend(["", "## 指摘事項", ""])
    findings = report.sorted_findings()
    if not findings:
        lines.append("指摘事項はありません。")
    else:
        for finding in findings:
            lines.extend(
                [
                    f"### [{finding.severity}] {finding.title}",
                    "",
                    f"- Check: `{finding.check_id}`",
                    f"- Path: `{finding.path}`",
                    f"- 根拠: {finding.evidence}",
                    f"- 対応: {finding.recommendation}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _table_rows(items: Iterable[tuple[str, object]]) -> str:
    return "".join(
        f"<tr><th scope='row'>{html.escape(key)}</th><td><code>{html.escape(_display_value(value))}</code></td></tr>"
        for key, value in items
    )


def _finding_card(finding: Finding) -> str:
    severity_class = finding.severity.casefold()
    return "".join(
        [
            f"<article class='finding {severity_class}'>",
            "<div class='finding-head'>",
            f"<span class='badge'>{html.escape(finding.severity)}</span>",
            f"<h3>{html.escape(finding.title)}</h3>",
            "</div>",
            f"<dl><div><dt>Check</dt><dd><code>{html.escape(finding.check_id)}</code></dd></div>",
            f"<div><dt>Path</dt><dd><code>{html.escape(finding.path)}</code></dd></div>",
            f"<div><dt>根拠</dt><dd>{html.escape(finding.evidence)}</dd></div>",
            f"<div><dt>対応</dt><dd>{html.escape(finding.recommendation)}</dd></div></dl>",
            "</article>",
        ]
    )


def render_html(report: ScanReport) -> str:
    score = "N/A" if report.score is None else str(report.score)
    assurance = str(report.metadata.get("assurance_level", "static"))
    coverage = _assurance_coverage(report)
    count_cards = "".join(
        (
            f"<a class='metric' href='#severity-{severity.casefold()}'>"
            f"<span>{html.escape(severity)}</span><strong>{count}</strong></a>"
        )
        for severity, count in report.counts.items()
    )

    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in report.sorted_findings():
        grouped[finding.severity].append(finding)

    finding_sections: list[str] = []
    for severity in SEVERITY_ORDER:
        items = grouped.get(severity, [])
        open_attr = " open" if severity in {"BLOCKER", "HIGH"} and items else ""
        cards = "".join(_finding_card(item) for item in items)
        if not items:
            cards = "<p class='empty'>該当なし</p>"
        finding_sections.append(
            f"<details id='severity-{severity.casefold()}' class='severity-group'{open_attr}>"
            f"<summary><span>{html.escape(severity)} — {html.escape(SEVERITY_LABELS[severity])}</span>"
            f"<strong>{len(items)}</strong></summary><div class='finding-list'>{cards}</div></details>"
        )

    assurance_rows = _table_rows(
        (
            (f"{label} ({key})", coverage.get(key, "not_reported"))
            for key, label in ASSURANCE_COVERAGE_LABELS.items()
        )
    )
    signal_rows = _table_rows(
        (
            (f"{SIGNAL_LABELS[key]} ({key})", report.metadata.get(key, []))
            for key in (
                "project_type",
                "start_commands",
                "verification_commands",
                "ports",
                "health_endpoints",
            )
        )
    )
    coverage_rows = _table_rows(
        (
            (f"{COVERAGE_LABELS[key]} ({key})", report.metadata.get(key, []))
            for key in (
                "scan_complete",
                "git_tracked_file_detection",
                "git_ignore_detection",
                "ignore_detection_source",
                "skipped_reasons",
                "ignored_paths",
                "ignored_checks",
                "suppressed_findings",
                "incomplete_reasons",
                "scan_errors",
            )
        )
    )

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Repo Launch Doctor — {html.escape(report.verdict)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-2: #eef3f9;
      --text: #172033;
      --muted: #5f6b7c;
      --border: #d8e0ea;
      --accent: #1769e0;
      --blocker: #c62828;
      --high: #d95f02;
      --medium: #9a6b00;
      --low: #147d92;
      --info: #2e7d32;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0b1220;
        --surface: #111b2e;
        --surface-2: #17243a;
        --text: #e7edf7;
        --muted: #a9b6c8;
        --border: #2d3c54;
        --accent: #73a8ff;
        --blocker: #ff6b6b;
        --high: #ff9d5c;
        --medium: #f4c95d;
        --low: #65d3e5;
        --info: #80d887;
      }}
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); line-height: 1.6; }}
    a {{ color: inherit; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 28px auto 64px; }}
    .hero, .panel, .severity-group {{
      background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
      box-shadow: 0 8px 28px rgba(15, 23, 42, .07);
    }}
    .hero {{ padding: clamp(22px, 4vw, 36px); display: grid; gap: 22px; }}
    .eyebrow {{ margin: 0 0 6px; color: var(--muted); font-weight: 700; letter-spacing: .04em; }}
    h1 {{ margin: 0; font-size: clamp(26px, 5vw, 46px); line-height: 1.2; overflow-wrap: anywhere; }}
    .status-row {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: end; }}
    .verdict {{ font-size: clamp(28px, 6vw, 54px); font-weight: 850; line-height: 1; }}
    .verdict-note {{ color: var(--muted); font-weight: 650; }}
    .score {{ margin-left: auto; text-align: right; }}
    .score strong {{ display: block; font-size: clamp(30px, 5vw, 48px); line-height: 1; }}
    .score span {{ color: var(--muted); }}
    .metadata {{ margin: 0; color: var(--muted); }}
    .scope-note {{ margin: 0; padding: 12px 14px; border-radius: 12px; background: var(--surface-2); color: var(--muted); }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 10px; }}
    .metric {{
      background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px;
      padding: 13px 15px; display: flex; justify-content: space-between; text-decoration: none;
    }}
    .metric:hover, .metric:focus-visible {{ outline: 3px solid color-mix(in srgb, var(--accent) 35%, transparent); }}
    .panel {{ margin-top: 18px; padding: clamp(18px, 3vw, 26px); overflow-x: auto; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 11px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ width: min(310px, 36%); }}
    code {{ color: var(--accent); overflow-wrap: anywhere; white-space: normal; }}
    .severity-group {{ margin-top: 14px; overflow: clip; }}
    summary {{
      cursor: pointer; padding: 17px 20px; display: flex; justify-content: space-between;
      gap: 16px; font-weight: 800; background: var(--surface-2);
    }}
    summary:focus-visible {{ outline: 3px solid var(--accent); outline-offset: -3px; }}
    .finding-list {{ padding: 6px 18px 18px; }}
    .finding {{
      border: 1px solid var(--border); border-left: 7px solid var(--info);
      border-radius: 14px; padding: 18px; margin-top: 12px; background: var(--surface);
    }}
    .finding.blocker {{ border-left-color: var(--blocker); }}
    .finding.high {{ border-left-color: var(--high); }}
    .finding.medium {{ border-left-color: var(--medium); }}
    .finding.low {{ border-left-color: var(--low); }}
    .finding.info {{ border-left-color: var(--info); }}
    .finding-head {{ display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }}
    .finding h3 {{ margin: 0; font-size: 18px; }}
    .badge {{ font-size: 12px; font-weight: 850; letter-spacing: .06em; background: var(--surface-2); border-radius: 999px; padding: 4px 9px; }}
    dl {{ margin: 14px 0 0; display: grid; gap: 8px; }}
    dl div {{ display: grid; grid-template-columns: 92px 1fr; gap: 10px; }}
    dt {{ color: var(--muted); font-weight: 700; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    .empty {{ color: var(--muted); margin: 14px 2px 0; }}
    @media (max-width: 640px) {{
      main {{ width: min(100% - 20px, 1120px); margin-top: 10px; }}
      .hero, .panel, .severity-group {{ border-radius: 14px; }}
      .score {{ margin-left: 0; text-align: left; }}
      dl div {{ grid-template-columns: 1fr; gap: 0; }}
      th, td {{ display: block; width: 100%; }}
      th {{ border-bottom: 0; padding-bottom: 2px; }}
      td {{ padding-top: 2px; }}
    }}
  </style>
</head>
<body>
<main>
  <section class="hero" aria-labelledby="report-title">
    <div>
      <p class="eyebrow">Static readiness · assurance: {html.escape(assurance)}</p>
      <h1 id="report-title">{html.escape(report.repository)}</h1>
    </div>
    <div class="status-row">
      <div>
        <div class="verdict">{html.escape(report.verdict)}</div>
        <div class="verdict-note">{html.escape(VERDICT_LABELS[report.verdict])}</div>
      </div>
      <div class="score"><strong>{html.escape(score)}</strong><span>static score / 100</span></div>
    </div>
    <p class="scope-note">このPASSは静的検査の結果です。実起動、依存関係、GitHub設定、バイナリ内部などの <code>not_checked</code> 領域は保証しません。</p>
    <p class="metadata">生成 {html.escape(report.generated_at)} · テキスト {report.files_scanned}件 · パス {report.paths_discovered}件</p>
    <nav class="metrics" aria-label="重要度別Finding">
      {count_cards}
    </nav>
  </section>

  <section class="panel">
    <h2>保証範囲</h2>
    <table><tbody>{assurance_rows}</tbody></table>
  </section>

  <section class="panel">
    <h2>詳細な検査範囲</h2>
    <table><tbody>{coverage_rows}</tbody></table>
  </section>

  <section class="panel">
    <h2>検出した実行・検証シグナル</h2>
    <table><tbody>{signal_rows}</tbody></table>
  </section>

  <section class="panel" aria-labelledby="findings-title">
    <h2 id="findings-title">指摘事項</h2>
    {''.join(finding_sections)}
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
