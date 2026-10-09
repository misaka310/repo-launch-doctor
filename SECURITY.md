# セキュリティポリシー

## サポート対象

既定ブランチの最新版をサポートします。

## 脆弱性の報告

リポジトリでGitHub Private Vulnerability Reportingが有効な場合は、公開Issueではなくそちらを使用してください。実際の認証情報、秘密鍵、セッションCookie、個人情報、非公開リポジトリの内容を公開Issueへ載せないでください。

報告には次を含めてください。

- 影響するバージョンまたはcommit
- OSとPythonのバージョン
- 合成データだけを使った最小再現
- 期待した結果と実際の結果
- 本来伏せるべき内容がレポートへ出たか

## 安全性の境界

Repo Launch Doctorは、上限を設けた静的・読み取り専用の検査を行います。対象リポジトリに書かれたコマンドは実行しません。Git追跡状態とignore状態の確認に `git ls-files` と `git check-ignore` を使用する場合があります。

秘密情報らしいファイルの内容は生成レポートへコピーしません。Git履歴は検査せず、専用のシークレットスキャナーやセキュリティ監査の代替ではありません。

`INCOMPLETE` のレポートを「公開して安全」という根拠に使用しないでください。

## Private vulnerability reporting

Please report suspected vulnerabilities privately through GitHub's private vulnerability reporting form:
https://github.com/misaka310/repo-launch-doctor/security/advisories/new

Do not disclose exploit details, credentials, tokens, personal data, or other sensitive information in a public issue.
We aim to acknowledge a vulnerability report within 7 days, complete the initial assessment within 30 days, and coordinate disclosure after a fix is available, normally within 90 days. If remediation needs longer, we will communicate the revised disclosure timeline through the private report.
