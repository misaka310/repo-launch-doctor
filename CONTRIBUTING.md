# Contributing

不具合報告と改善提案を歓迎します。

## Issueを作る前に

1. 既定ブランチの最新版で確認する
2. 小さな合成リポジトリで再現する
3. 認証情報、個人情報、非公開リポジトリ名、ローカル絶対パスを除く
4. OS、Pythonバージョン、実行コマンド、期待結果、実際の結果を書く

実際の `.env`、Cookie、秘密鍵、非公開ソース一式、個人パスを含むレポートは添付しないでください。

## 開発時の検証

```bash
python -m repo_launch_doctor scan . --output reports/self --fail-on high
python -m unittest discover -s tests -v
python -m compileall repo_launch_doctor tests
```

チェックを変更する場合は、正常系または異常系の回帰テストを追加してください。公開を止めるチェックには、秘密値そのものをレポートへ出さないテストも必要です。

CLIは外部依存なしを基本とします。標準ライブラリでは安全に実現できず、公開ユーザーへ明確な利益がある場合だけ依存追加を検討します。
