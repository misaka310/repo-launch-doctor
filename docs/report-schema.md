# レポートスキーマ

`report.json` には `schema_version` が含まれます。

## Version 1.0

トップレベル項目:

- `schema_version`
- `repository`
- `generated_at`
- `files_scanned`
- `paths_discovered`
- `verdict`
- `score`
- `counts`
- `metadata`
- `findings`

`verdict` が `INCOMPLETE` の場合、`score` は `null` です。

`repository` は既定で共有しやすいフォルダ名だけを保持します。絶対パスは `--include-absolute-path` を明示した場合だけ含まれます。

CIや他ツールは、次の順に判定してください。

1. `verdict != "INCOMPLETE"`
2. `metadata.scan_complete == true`
3. 自分たちの運用基準に応じた重要度件数

数値スコアだけを公開可否の根拠にしないでください。`verdict` と `score` は静的検査だけの結果です。実起動、依存関係、GitHub設定、バイナリ内部などは `metadata.coverage` で `not_checked` として明示されます。

## 主なmetadata

- `assurance_level`: 現在は常に `static`
- `coverage`: 各検査領域の `checked`、`partial`、`incomplete`、`not_checked` 状態
  - `repository_files`: リポジトリ内のファイル・パス検査
  - `readme_and_entrypoints`: READMEと起動入口の静的検査
  - `git_tracking`: Git追跡・ignore判定
  - `git_history`: `scan`単体では未検査。`history-scan`を別途実行する
  - `runtime`: 実際のセットアップ・起動・操作は未実行
  - `dependencies`: 依存関係の脆弱性・ライセンスは未検査
  - `github_settings`: ruleset、branch protectionなどのリモート設定は未検査
  - `binary_contents`: 画像、PDF、ZIP、モデルなどの内部は未検査
- `scan_complete`: 検査が上限到達や読取エラーなしで完了したか
- `git_tracked_file_detection`: Git追跡状態を取得できたか
- `git_ignore_detection`: ignore判定を利用できたか
- `ignore_detection_source`: `git`、`.gitignore-fallback`、`unavailable` のいずれか
- `skipped_reasons`: 内容を読まなかった理由と件数
- `suppressed_findings`: 設定で抑制したcheck IDと件数
