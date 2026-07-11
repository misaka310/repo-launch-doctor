# 設定リファレンス

検査対象リポジトリのルートへ `.repo-launch-doctor.json` を置きます。

未知のキーはエラーになります。すべてのOSで、設定内のパス区切りには `/` を使用できます。

## 項目

### `project_type`

次のいずれかを指定します。

- `auto`
- `web`
- `static-web`
- `desktop`
- `cli`
- `library`
- `docs`

`static-web` はfaviconを確認しますが、health endpointは要求しません。自動判定が合わない場合だけ明示してください。

### `ignore_paths`

テキスト内容を読まないパスの配列です。glob形式で指定します。

標準では `.git`、依存ツリー、キャッシュ、仮想環境、レポート、カバレッジ、`dist`、`build` などの内容を読みません。ただし、可能な範囲でファイル名とGit追跡状態は安全性チェックへ残します。

GitリポジトリでないZIP展開先では、ルートの `.gitignore` にある一般的なパターンを補助的に使用します。判定元はレポートの `ignore_detection_source` で確認できます。

この項目を `.gitignore` の代わりにしないでください。追跡済みの秘密情報候補を `secret-risk-file` から隠すことはできません。

### `ignore_checks`

抑制するcheck IDの配列です。抑制したIDと件数はレポートに表示されます。

次の安全性チェックは抑制できません。

- `secret-risk-file`
- `scan-incomplete`
- `internal-check-error`

### `expected_ports`

実行コードに存在するはずのポート番号です。

`tests/`、`docs/`、`examples/`、`.github/`、生成済みレポート内の値は検出対象から外します。

### `expected_start_commands`

必須のルート起動ファイルまたは検出コマンドです。

```json
["start.bat", "npm run dev"]
```

### `expected_health_endpoints`

必須のendpointです。

```json
["/health"]
```

### `accepted_generated_paths`

意図的にGit管理する生成物を限定的に許可します。

```json
["public/generated-demo/**"]
```

`build/`、`logs/`、依存ツリー全体を許可せず、公開する必要がある小さな成果物だけに絞ってください。

### `max_files`

内容を読むテキストファイル数の上限です。既定値は `10000` です。

上限を超えるテキストが存在すると、判定は `INCOMPLETE` になります。

### `max_paths`

列挙するファイルパス数とGit追跡パス数の上限です。既定値は `100000` です。

パス列挙が上限へ達すると、判定は `INCOMPLETE` になります。

### `max_file_bytes`

内容を読む1ファイルあたりの最大サイズです。既定値は `1000000` です。

これより大きいファイルも、ファイル名とGit追跡状態の確認には参加します。個別の巨大ファイルやバイナリを読まないことだけでは `INCOMPLETE` になりません。
