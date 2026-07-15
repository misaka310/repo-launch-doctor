# Changelog

## 0.3.0

- Parse Python project entry points with `tomllib`, including scripts and GUI scripts.
- Only suggest Python test commands when pytest or unittest evidence exists.
- Detect README coverage from Markdown headings rather than incidental prose.
- Add a fixed-SHA public repository benchmark runner, report schema, and decision records.
- Make external benchmark runs resumable with validated repository and per-target caches, independent fetch/checkout/scan timeouts, and repository-plus-SHA target IDs that support Before/After commits from the same repository.
- Publish formal benchmark artifacts only after a complete 20-target run; partial runs remain under `.benchmark-cache` and cannot overwrite public evidence.
- Replace oversized or incomplete corpus targets with classification-equivalent fixed-SHA repositories and record every replacement and rejected candidate.
- Add network-free benchmark-runner regression tests covering shallow fetches, cache invalidation, failure accounting, resume/force behavior, and publication boundaries.
- Recognize Node.js `package.json` `bin` declarations and descriptive root shell scripts such as `runqemu.sh` as entry points, and auto-classify documentation-only repositories so they do not require application launchers.
- Add five verified public-history Before/After pairs and retain hard negative examples for Node.js CLI, documentation-only, and descriptive shell-launcher layouts.
- Publish a complete balanced 20-target result with zero execution errors: TP 5 / FP 0 / FN 0 / TN 15 for `missing-start-entrypoint` and TP 6 / FP 0 / FN 0 / TN 4 for `readme-missing-verification`.
- Add a current-repository audit that fixes the 30 targets before scanning, delays manual labels until all attempts finish, preserves excluded targets, and publishes baseline plus post-fix metrics.
- Expand entrypoint recognition to Make targets, Docker/Compose declarations, Go `main` packages, browser-extension manifests, documented launch commands, and common package preview/playground scripts.
- Recognize .NET libraries, Maven aggregators, and explicitly described library/framework/documentation collections so non-app repositories are not required to provide an application launcher.
- Recognize concrete README verification commands and manual playground/preview procedures without requiring an exact `Testing` heading.
- Skip additional known binary asset formats during text inspection instead of marking otherwise complete scans as unreadable.

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
