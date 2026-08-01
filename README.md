# Repo Launch Doctor

[![Tests](https://github.com/misaka310/repo-launch-doctor/actions/workflows/tests.yml/badge.svg)](https://github.com/misaka310/repo-launch-doctor/actions/workflows/tests.yml)

公開前のローカルリポジトリを**読み取り専用**で静的検査し、初見ユーザーが起動方法を見つけられる構成か、ドキュメントと実装が噛み合っているか、公開してはいけないファイルが混ざっていないかをレポートするPython CLIです。

対象リポジトリに書かれたコマンドは実行しません。実際の起動成功を保証するツールではなく、起動入口・検証入口・公開構成の不備を事前に見つけるためのツールです。結果はJSON・Markdown・HTMLで保存します。

## こんなときに使います

- GitHubで公開する前に、README・LICENSE・SECURITY・設定例を確認したい
- clone後の起動入口やテスト入口が見つけやすいか確認したい
- `.env`、秘密鍵、Cookie、ローカル設定が追跡されていないか確認したい
- `build/`、ログ、キャッシュ、仮想環境などがGitへ混入していないか確認したい
- Markdownの画像・相対リンク切れを確認したい
- Webアプリのfaviconやhealth endpoint不足を確認したい

## 必要環境

- Python 3.11以上
- WindowsまたはLinux
- Gitは任意。利用できる場合は追跡済み・ignore済みを正確に区別します

外部Pythonパッケージは不要です。

## 最短セットアップ

### Windows

cloneまたはZIP展開後、検査対象フォルダを渡します。対象フォルダを`run-doctor.bat`へドラッグ＆ドロップしても実行できます。

```bat
run-doctor.bat C:\path\to\target-repo
```

処理後、時刻付きフォルダへレポートを保存してHTMLを開きます。

```text
reports/<repo-name>-<timestamp>/report.html
```

引数を省略するとRepo Launch Doctor自身を検査します。

```bat
run-doctor.bat
```

既定では`HIGH`以上を検出すると終了コード1になります。第2引数で変更できます。

```bat
run-doctor.bat C:\path\to\target-repo none
run-doctor.bat C:\path\to\target-repo blocker
run-doctor.bat C:\path\to\target-repo medium
```

使用するPythonを固定する場合は、`REPO_LAUNCH_DOCTOR_PYTHON`へPython 3.11以上の実行ファイルの絶対パスを設定します。

### Windows・Linux共通

インストールせず、clone先から実行できます。

```bash
python -m repo_launch_doctor scan /path/to/target-repo --output reports/target --fail-on high
```

CLIとしてインストールする場合:

```bash
python -m pip install .
repo-launch-doctor scan /path/to/target-repo --output reports/target --fail-on high
```

バージョン確認:

```bash
repo-launch-doctor --version
```

## 判定の読み方

| 判定 | 意味 |
|---|---|
| `PASS` | 指摘事項なし |
| `PASS_WITH_NOTES` | 公開を止める問題はないが、改善点あり |
| `FAIL` | `BLOCKER`または`HIGH`があり、公開前に修正が必要 |
| `INCOMPLETE` | 上限到達、読取失敗、内部チェック失敗などにより検査未完了。公開判断には使わない |

`INCOMPLETE`ではスコアを表示しません。`--fail-on none`を指定しても終了コード2になります。

| 重要度 | 意味 |
|---|---|
| `BLOCKER` | Git追跡済み秘密情報候補や、検査未完了など公開判断を止める問題 |
| `HIGH` | 起動入口不足、READMEの重大不足、リンク切れ、未保護の秘密情報候補 |
| `MEDIUM` | 検証・保守・公開品質を弱くする問題 |
| `LOW` | 分かりやすさや事故防止の改善点 |
| `INFO` | 情報 |

点数だけではなく、個別のFindingと`scan_complete`を確認してください。

## 出力

```text
report.json   CI、集計、別ツール連携用
report.md     GitHub Issueやレビューへの貼り付け用
report.html   人が確認する折り畳み式レポート
```

![Repo Launch DoctorのPASSレポート](docs/report-preview.png)

共有時の個人情報漏えいを避けるため、レポートには既定で対象リポジトリ名だけを記録します。絶対パスが必要な場合のみ明示します。

```bash
repo-launch-doctor scan . --include-absolute-path
```

## 主な検査対象

- READMEの要件、セットアップ、使い方、検証、制限事項
- ルートのランチャーと、READMEに記載された一般的な起動入口
- Markdown内の相対リンク・画像リンク
- Git追跡状態を含む秘密情報らしいファイル名と機密設定項目
- Git追跡済みのログ、キャッシュ、依存ツリー、仮想環境、build成果物
- Webアプリのfavicon、`/health`、`/status`、実行コード内のポート
- 実在するtest・lint・typecheck・buildコマンド
- LICENSE、SECURITY、必要な設定例
- 検査範囲、除外範囲、上限到達、読取失敗、内部チェック失敗

秘密情報候補の値はレポートへ出力しません。

## プロジェクト別設定

対象リポ直下へ`.repo-launch-doctor.json`を置きます。

```json
{
  "project_type": "web",
  "ignore_paths": [],
  "ignore_checks": [],
  "expected_ports": [8717],
  "expected_start_commands": ["start.bat"],
  "expected_health_endpoints": ["/health"],
  "accepted_generated_paths": ["public/generated-demo/**"],
  "max_files": 10000,
  "max_paths": 100000,
  "max_file_bytes": 1000000
}
```

設定例は[.repo-launch-doctor.example.json](.repo-launch-doctor.example.json)、全項目は[設定リファレンス](docs/configuration.md)、check ID一覧は[チェックリファレンス](docs/check-reference.md)を参照してください。

重要な挙動:

- 未知の設定キー・check IDはエラーにします
- `secret-risk-file`、`scan-incomplete`、`internal-check-error`は無効化できません
- `ignore_paths`は内容読取の除外です。Git追跡済みの秘密情報候補を隠しません
- 抑制したFindingと除外範囲はレポートへ明示します
- 自動判定が合わない場合は`project_type`を明示してください

## Git履歴を検査する

現在の作業ツリーとは別に、選択したコミットで追加されたテキスト、秘密情報らしいファイル名、コミットメッセージを検査できます。

```bash
# PRやpush対象の範囲
python -m repo_launch_doctor history-scan . --range origin/main..HEAD --output reports/history

# ローカル参照から到達できる全履歴
python -m repo_launch_doctor history-scan . --all-history --output reports/full-history

# pre-push hookなどが作成したSHA一覧
python -m repo_launch_doctor history-scan . --commits-file commits.txt --output reports/outgoing
```

秘密値を追加した後のコミットで削除していても、追加時のコミットを対象に含めれば検出します。

## CIで使う

```bash
python -m repo_launch_doctor scan . --output reports/ci/current --fail-on high
python -m repo_launch_doctor history-scan . --range "$BASE_SHA..$HEAD_SHA" --output reports/ci/history
```

同梱の`.github/workflows/repo-launch-doctor.yml`は公開リポジトリ向けです。PRごとに実行し、連続更新時は古い実行をキャンセルします。非公開リポジトリでは明示的な`workflow_dispatch`だけを実行します。

終了コード:

- `0`: 指定基準を超えるFindingなし
- `1`: 指定基準以上、または履歴内の秘密情報候補を検出
- `2`: 設定エラー、Git範囲解決失敗、入出力エラー、内部チェック失敗、検査未完了

## 開発と評価資料

通常の検証:

```bash
python -m repo_launch_doctor scan . --output reports/self --fail-on high
python -m unittest discover -s tests -v
python -m compileall repo_launch_doctor tests
```

CI構成、対応Python、公開リポジトリ監査、固定SHAベンチマーク、precision・recallの解釈と再現手順は、[評価・研究資料](docs/evaluation.md)へ分離しています。

## 安全性

- 対象リポジトリを変更しません
- 対象リポジトリに記載されたコマンドを実行しません
- 秘密情報候補の内容をレポートへ転記しません
- 通常スキャンでは`.git`、依存ツリー、モデル、メディア、大容量ファイルの内容を読みません
- `history-scan`はGitからコミットメッセージとテキスト差分だけを読みます
- シンボリックリンクを追跡しません
- 上限到達、読取失敗、内部チェック失敗を成功扱いしません

脆弱性報告は[SECURITY.md](SECURITY.md)を参照してください。

## 制限事項

- 静的検査です。READMEに書かれたコマンドが実際に成功するかは判定しません
- あらゆる秘密値・業務機密・未知形式を完全には判定できません
- バイナリ、画像、PDF、ZIP、モデル内部の秘密情報は内容検査しません
- 独自ビルドシステムや動的に生成される入口は検出できない場合があります
- 自動プロジェクト種別判定は推定です
- スコアはセキュリティ監査、脆弱性診断、法務確認の代替ではありません
- Gitがないフォルダでは追跡状態を区別できません

## Contributing

不具合報告や改善提案は歓迎します。[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。

## License

MIT License
