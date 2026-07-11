# Repo Launch Doctor

ローカルリポジトリを読み取り専用で検査し、**起動しやすさ・検証可能性・公開前の危険**をまとめるPython CLIです。

READMEが初見ユーザーに通じるか、起動入口があるか、リンク切れや秘密情報らしいファイル、ログ・キャッシュの混入、Webアプリのfaviconやhealth endpoint不足などを確認し、JSON・Markdown・HTMLで改善案を出します。

## 主な機能

- READMEの要件、セットアップ、使い方、検証、制限事項を確認
- ルートのBAT/PowerShell/Python起動入口と`package.json` scriptsを検出
- Markdown内のローカルリンク・画像リンク切れを検出
- `.env`、秘密鍵、Cookie、ローカル設定などの危険なファイル名を検出
- ログ、キャッシュ、仮想環境、依存ツリー、build成果物の混入を検出
- Webアプリのfavicon宣言・実ファイルと`/health`・`/status`を確認
- ポート、起動コマンド、test・lint・typecheck・buildコマンドを一覧化
- 秘密値の内容はレポートへ出さず、該当パスと対処だけを表示
- 対象リポのスクリプトやコマンドは実行しない

## 必要環境

- Python 3.11以上
- Gitは任意。利用できる場合だけ`git ls-files`で追跡済みファイルを判定します
- Windows、Linux、macOS

外部Pythonパッケージは不要です。

## セットアップ

リポジトリをcloneまたはZIP展開したら、そのフォルダで実行できます。インストールせずに使う場合は次の形式です。

```powershell
python -m repo_launch_doctor scan C:\path\to\target-repo --output reports\target
```

CLIとしてインストールする場合は次です。

```powershell
python -m pip install -e .
repo-launch-doctor scan C:\path\to\target-repo --output reports\target
```

## Windowsでの最短利用

`run-doctor.bat`へ検査したいフォルダを渡します。

```bat
run-doctor.bat C:\path\to\target-repo
```

引数を省略するとRepo Launch Doctor自身を検査します。

```bat
run-doctor.bat
```

処理後に次のHTMLレポートを開きます。

```text
reports/repo-launch-doctor/report.html
```

## 使い方

基本コマンドは次です。

```powershell
python -m repo_launch_doctor scan <対象フォルダ> --output <出力先> --fail-on <基準>
```

`--fail-on`は終了コード1にする基準です。

| 値 | 動作 |
|---|---|
| `none` | 検出結果に関係なく正常終了。ローカル確認向け |
| `blocker` | BLOCKERがあれば終了コード1。既定値 |
| `high` | HIGH以上があれば終了コード1 |
| `medium` | MEDIUM以上があれば終了コード1 |

CIで公開前チェックとして使う例です。

```powershell
python -m repo_launch_doctor scan . --output reports/ci --fail-on high
```

## 出力

出力先には同じ内容を用途別に保存します。

```text
report.json   CI、集計、別ツール連携用
report.md     GitHub Issueやレビューへの貼り付け用
report.html   人が確認するダッシュボード
```

重要度は次の意味です。

| 重要度 | 意味 |
|---|---|
| BLOCKER | 公開前に止めるべき秘密情報リスクなど |
| HIGH | 起動不能や重大なドキュメント不整合につながる問題 |
| MEDIUM | 検証、保守、通常利用を弱くする問題 |
| LOW | 公開品質や分かりやすさの改善点 |
| INFO | 検出した機能やコマンド |

スコアは比較用の目安です。点数だけで公開可否を判断せず、個別のFindingを確認してください。

## プロジェクト別設定

対象リポ直下に`.repo-launch-doctor.json`を置くと、期待値や例外を設定できます。[設定例](.repo-launch-doctor.example.json)をコピーして編集してください。

```json
{
  "project_type": "web",
  "ignore_paths": ["private/**"],
  "ignore_checks": [],
  "expected_ports": [8717],
  "expected_start_commands": ["start.bat"],
  "expected_health_endpoints": ["/health"],
  "accepted_generated_paths": ["public/generated-demo/**"]
}
```

`project_type`には`auto`、`web`、`static-web`、`desktop`、`cli`、`library`、`docs`を指定できます。静的サイトは`static-web`にするとfaviconは検査しつつhealth endpointを要求しません。

## 検証

単体・E2Eテストを実行します。

```powershell
python -m unittest discover -s tests -v
```

構文確認とDoctor自身の検査です。

```powershell
python -m compileall repo_launch_doctor tests
python -m repo_launch_doctor scan . --output reports/self --fail-on none
```

設計と実装計画は次にあります。

- [設計](docs/superpowers/specs/2026-07-11-repo-launch-doctor-design.md)
- [実装計画](docs/superpowers/plans/2026-07-11-repo-launch-doctor.md)

## 安全性

- 対象リポのファイルは変更しません
- 対象リポに書かれたコマンドは実行しません
- 秘密情報らしいファイルは内容をレポートへ転記しません
- `.git`、依存ツリー、モデル、メディア、大容量ファイルは既定で読み飛ばします
- シンボリックリンク経由で対象ルート外のファイルを読みません
- 検査ファイル数と1ファイルあたりのサイズに上限があります

詳細は[セキュリティ方針](SECURITY.md)を参照してください。

## 制限事項

- 静的検査なので、READMEに書かれたコマンドが実際に成功するかまでは判定しません
- 独自形式の起動方法や動的に作られるパスは検出できない場合があります
- 秘密情報の内容スキャンではなく、危険なファイル名と公開構成を中心に検査します
- スコアはセキュリティ監査、法務確認、脆弱性診断の代替ではありません
- Gitがないフォルダでは「追跡済みか」を区別できないため、存在する危険ファイルを保守的に警告します

## License

MIT License
