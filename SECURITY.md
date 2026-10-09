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

<!-- managed-by: repo-launch-doctor-security-baseline-v1 -->

## Reporting a vulnerability

Please do **not** publish suspected vulnerabilities in a public issue. Report them privately through GitHub's security-advisory flow for this repository:

https://github.com/misaka310/repo-launch-doctor/security/advisories/new

Include the affected version or commit, reproduction steps, impact, and any suggested mitigation. Reports that include a minimal proof of concept are especially useful.

## Response timeline

- Initial acknowledgement target: within 7 days.
- Triage and severity assessment target: within 14 days.
- Fix timing depends on impact and complexity; critical issues are prioritized before routine feature work.
- Coordinated public disclosure should wait until a fix or mitigation is available whenever practical.

## Supported versions

The current default branch and the latest published release, when releases exist, receive security fixes. Older snapshots may not receive backports.
