# Changelog

## 0.3.0

- Parse Python project entry points with `tomllib`, including scripts and GUI scripts.
- Only suggest Python test commands when pytest or unittest evidence exists.
- Detect README coverage from Markdown headings rather than incidental prose.
- Add a fixed-SHA public repository benchmark runner, report schema, and decision records.
- Make external benchmark runs resumable with validated repository and per-target caches, independent fetch/checkout/scan timeouts, and owner-qualified target IDs.
- Publish formal benchmark artifacts only after a complete 20-target run; partial runs remain under `.benchmark-cache` and cannot overwrite public evidence.
- Replace oversized or incomplete corpus targets with classification-equivalent fixed-SHA repositories and record every replacement and rejected candidate.
- Add network-free benchmark-runner regression tests covering shallow fetches, cache invalidation, failure accounting, resume/force behavior, and publication boundaries.
- Publish the first complete 20-target result: 20 fetches, 20 checkouts, 20 complete scans, 20 metric-eligible targets, and zero execution errors.

## 0.2.0

- パス/Git状態の列挙とテキスト内容の読取を分離
- 追跡済みのbuild、cache、依存ツリー、log、仮想環境を内容を読まず検出
- 未追跡かつGit ignoreされていない生成物をLOWで表示
- 上限到達や読取失敗を `INCOMPLETE` とし、スコアを表示しない設計へ変更
- `.ico` などのバイナリfaviconを内容を読まず確認
- tests、docs、examples、reportsの値を実行ポート・health endpointから除外
- 共有用レポートから絶対パスを既定で除外
- PASS/FAIL/INCOMPLETE、検査範囲、抑制Finding、折り畳みHTMLを追加
- Windowsランチャーを呼び出し元フォルダに依存しない構成へ変更し、出力を時刻別に分離
- 未知の設定キーと無効なcheck IDをエラー化
- Windows、Ubuntu、macOS × Python 3.11〜3.13のCI matrixを追加
- GitなしのZIP展開先で `.gitignore` の一般的な規則を補助利用し、判定元をレポートへ表示
