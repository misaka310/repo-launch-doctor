# 評価・研究資料

この文書は、Repo Launch Doctorの利用手順ではなく、検査規則の評価方法、公開監査、回帰ベンチマーク、結果の解釈をまとめます。通常の導入と操作は[README](../README.md)を参照してください。

## 評価の目的

Repo Launch Doctorは静的検査ツールです。評価では、次の点を確認します。

- 実際の公開リポジトリで、起動入口・検証手順・秘密情報候補・生成物・Markdownリンクの問題を適切に検出できるか
- 誤検出を減らしながら、既知の問題を見逃さないか
- 仕様変更後も、固定した入力に対して判定が退行しないか
- 検査未完了や読取失敗を成功として扱わないか

評価値は、特定の標本と確認済みcheck IDに対する結果です。すべてのGitHubリポジトリ、未知の秘密情報形式、実行時の安全性を代表する値ではありません。

## 現在の公開リポジトリ監査

[現在の公開リポジトリ監査](../audits/current/README.md)では、選定条件を先に固定した公開リポジトリ群を走査し、その後に人手で正解ラベルを付けています。

公開資料には次を含みます。

- 選定条件と固定したHEAD
- 全対象への走査結果
- 人手レビューの根拠
- check IDごとのTP、FP、FN、TN
- 修正前後のprecisionとrecall
- 検査できなかった対象と理由

秘密情報候補については、値そのものや未通知の対象を公開資料へ転記しません。

## 固定SHA回帰ベンチマーク

[固定SHAの回帰ベンチマーク](../benchmarks/README.md)は、過去に確認した入力を固定し、規則変更後も既知の判定が維持されるかを確認するための資料です。

固定SHAベンチマークは現在の外部リポジトリ状態を示すものではありません。現在の挙動を評価する資料は公開リポジトリ監査、退行防止に使う資料は固定SHAベンチマークとして分離しています。

## 製品側の検証

通常の開発検証は次で実行します。

```bash
python -m repo_launch_doctor scan . --output reports/self --fail-on high
python -m unittest discover -s tests -v
python -m compileall repo_launch_doctor tests
```

PRではWindowsとUbuntuのPython 3.12を検証します。Python 3.11〜3.13の全互換性検査は`workflow_dispatch`で実行します。Windowsでは、別フォルダをカレントディレクトリにして`run-doctor.bat`を呼ぶ経路も確認します。

## 公開監査の再現

ネットワーク接続とGitが必要です。

```bash
python audits/current/current_audit.py scan --resume
python audits/current/current_audit.py packet
# 全対象を確認してmanual-review.jsonへ根拠とreviewed_atを記録
python audits/current/current_audit.py publish
```

新しい監査を開始する場合だけ、既存結果を退避したうえで`select`を実行します。選定後に結果を見て対象を都合よく差し替えない運用にしています。

## 結果の解釈

- precisionとrecallは、記載された標本とcheck IDにだけ適用されます。
- 静的検査の成功は、対象ソフトウェアが実際に起動することを保証しません。
- 秘密情報検査は既知形式と機密キーへの値代入を対象にします。専用secret scannerや人手監査の代替ではありません。
- バイナリ、画像、PDF、ZIP、モデル内部の内容は評価対象外です。
- 自動プロジェクト種別判定、favicon、health endpoint、起動入口の検出には推定が含まれます。
- `INCOMPLETE`、上限到達、読取失敗、内部エラーは合格として扱いません。

## 関連資料

- [現在の公開リポジトリ監査](../audits/current/README.md)
- [固定SHA回帰ベンチマーク](../benchmarks/README.md)
- [設定リファレンス](configuration.md)
- [チェックリファレンス](check-reference.md)
- [セキュリティ方針](../SECURITY.md)
