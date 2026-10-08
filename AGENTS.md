# Repository instructions

## 仕様の正本

- 仕様の正本: `README.md`
- 公開リポジトリ向けガード運用の正本: `docs/evaluation.md` の「公開リポジトリ運用の正本」
- 実装前に意図する仕様を正本へ反映し、仕様変更時は同じ変更で正本と検証を更新する。

## Public repository guard

- ローカル `pre-push` はRepo Launch Doctorを維持し、公開事故の境界チェックとして使う。
- Pull RequestではRepo Launch DoctorとOpenSSF Scorecardを実行する。
- default branchへのpushと週次では公式OpenSSF Scorecard Actionを実行する。
- OpenSSF Best Practicesは毎PRのCIではなく、定期的な公開品質・OSS運用の見直しに使う。
- 共通workflowの役割分担を変更する場合は、先に`docs/evaluation.md`を更新し、各公開リポジトリの管理workflowと矛盾させない。

## Repository boundaries

- このリポジトリの責務と既存の利用者向け挙動を維持する。
- README、CONTRIBUTING、docs、既存テストに矛盾がある場合は、実装だけを正として進めず差分を解消する。

## Verification

- リポジトリに記載されたtest、build、lint、typecheck、E2Eの入口を使用する。
- 仕様、実装、テスト、利用者向け文書が一致するまで完了扱いにしない。
