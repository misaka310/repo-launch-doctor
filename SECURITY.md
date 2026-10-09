# セキュリティポリシー

## サポート対象

既定ブランチの最新版をサポートします。過去リリースで再現する問題でも、まず既定ブランチ上で影響が残っているかを確認します。

## 脆弱性の報告

脆弱性は公開Issueへ書かず、GitHubのPrivate Vulnerability Reportingを使用してください。

- 非公開報告: https://github.com/misaka310/repo-launch-doctor/security/advisories/new
- Security overview: https://github.com/misaka310/repo-launch-doctor/security

実際の認証情報、秘密鍵、セッションCookie、個人情報、非公開リポジトリの内容を公開Issueへ載せないでください。Private Vulnerability Reportingが利用できない場合も、機密情報を公開せず、公開Issueには「非公開連絡手段が必要」であることだけを書いてください。

報告には次を含めてください。

- 影響するバージョンまたはcommit
- OSとPythonのバージョン
- 合成データだけを使った最小再現
- 期待した結果と実際の結果
- 想定する影響範囲と攻撃条件
- 本来伏せるべき内容がレポートへ出たか

## 対応と開示

- 受領後できるだけ早く内容を確認し、再現可否と影響範囲を整理します。
- 修正が必要な場合は、再現テストを追加してから修正し、既定ブランチへ反映します。
- 修正公開前に攻撃手順や実データを公開しないでください。公開時期は報告者と調整します。
- 影響が確認できなかった場合も、判断理由をPrivate Vulnerability Reporting上で返します。

## 安全性の境界

Repo Launch Doctorは、上限を設けた静的・読み取り専用の検査を行います。対象リポジトリに書かれたコマンドは実行しません。Git追跡状態とignore状態の確認に `git ls-files` と `git check-ignore` を使用する場合があります。

秘密情報らしいファイルの内容は生成レポートへコピーしません。Git履歴は検査せず、専用のシークレットスキャナーやセキュリティ監査の代替ではありません。

`INCOMPLETE` のレポートを「公開して安全」という根拠に使用しないでください。
