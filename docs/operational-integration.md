# CodexProのリモート送信境界

この文書は、作者のワークスペース（CodexPro）が複数リポジトリの共有`pre-push`ゲートとしてRepo Launch Doctorを内部運用する際の設計方針です。Repo Launch Doctorを自分のリポジトリで使うだけなら、この文書を読む必要はありません。

CodexPro運用では、Repo Launch Doctorを「Publicリポジトリだけで呼ぶチェック」ではなく、**GitHubへ送信する直前の共通Doctor**として扱います。公開済みかどうかはDoctorを呼ぶ条件には使わず、送信経路と追加保護を選ぶための事実として使います。

## 全リポジトリ共通

- `git push` の`pre-push`で、実際にGitが選んだremote名・remote URL・ref更新を使ってRepo Launch Doctorを必ず実行する。
- `origin`を推測して判定しない。push先remoteのGitHub metadataからvisibilityを機械的に取得する。
- GitHub remoteなのにmetadataまたはvisibilityを確定できない場合は、送信境界ではfail-closedでpushを止める。
- Private/Publicのどちらでも、remoteへ新しく送るcommit/historyをDoctorの`history-scan`で検査する。秘密情報候補・危険なcommit内容・検査異常はpush前に止める。
- リポジトリごとの「Public Doctor hookを先に手動導入できていること」を安全性の前提にしない。共有`pre-push`が共通入口を所有する。

## Publicリポジトリ

Publicでは作業ブランチのpush時点で内容が外部から閲覧可能になるため、**最初の公開防止境界はPR後のGitHub Actionsではなくローカル`pre-push` Doctor**です。

- 作業ブランチをremoteへpushする前にローカルDoctorを通し、outgoing historyに加えてpush先tipの**exact repository state**を`scan --fail-on high`で検査する。
- default branchへの直接pushを許可せず、作業ブランチ → Pull Request → mergeの経路だけを許可する。
- Pull RequestではGitHub Actionsの`public-readiness`をもう一度実行し、ローカル検査の代替ではなく独立した二重検査・merge条件として使う。
- GitHub Rulesetはdefault branchに対してPull Request必須と`public-readiness`必須の両方を強制し、bypassを設けない。
- PrivateからPublicへvisibilityを変更する場合は、変更前に全到達履歴のDoctor baselineを成功させる。Public化後のActionsを「初回漏えい防止」として扱わない。

## Privateリポジトリ

Privateでもremote送信前Doctorは省略しません。ただしPrivateの通常pushでは、既存repository全体のREADME品質やbroken linkなど**release-readiness由来の負債で日常pushを止めず**、remoteへ新しく送るcommit/historyの安全検査を必須にします。Public専用のexact repository scan・PR/ruleset要件はPublic化またはPublic送信時だけ追加します。

この分担では、ローカル`pre-push`が「remoteへ出してよいか」、PublicのPR Actions/Rulesetが「default branchへ取り込んでよいか」を担当します。
