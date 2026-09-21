# チェックリファレンス

## 無効化できない安全性チェック

| Check ID | 既定の重要度 | 目的 |
|---|---:|---|
| `secret-risk-file` | BLOCKER/HIGH | 秘密情報らしいファイル名とGit状態を確認し、内容をレポートへコピーせず警告する |
| `scan-incomplete` | BLOCKER | 上限到達や読取失敗で検査範囲が欠けたとき、公開判断を止める |
| `internal-check-error` | MEDIUM | 個別チェックの失敗を黙って見落とさず表示する |

## ドキュメントと導線

| Check ID | 既定の重要度 |
|---|---:|
| `missing-readme` | HIGH |
| `readme-missing-requirements` | LOW |
| `readme-missing-setup` | MEDIUM |
| `readme-missing-usage` | MEDIUM |
| `readme-missing-verification` | MEDIUM |
| `readme-missing-limitations` | LOW |
| `broken-markdown-link` | HIGH |
| `markdown-link-outside-root` | MEDIUM |
| `missing-start-entrypoint` | HIGH |
| `expected-start-command-missing` | HIGH |

## リポジトリ衛生

| Check ID | 既定の重要度 |
|---|---:|
| `generated-artifact-present` | 追跡済み/Git不明はMEDIUM、未追跡かつignoreなしはLOW |
| `workspace-specific-dependency` | HIGH |
| `internal-agent-plan-tracked` | HIGH |
| `hardcoded-local-path` | MEDIUM |
| `hardcoded-ip-address` | 到達可能なグローバルアドレスはMEDIUM、プライベートアドレスはLOW |
| `missing-license` | MEDIUM |
| `missing-security-doc` | LOW |
| `missing-config-example` | ローカル設定が必要と見られる場合にLOW |

## Webアプリ

| Check ID | 既定の重要度 |
|---|---:|
| `missing-favicon` | LOW |
| `missing-health-check` | MEDIUM |
| `expected-port-missing` | MEDIUM |
| `expected-health-endpoint-missing` | MEDIUM |

設定した期待値は既知のプロジェクトに対する検査精度を高めますが、コマンドの実行成功までは証明しません。Repo Launch Doctorは対象リポジトリのコマンドを実行しません。

`missing-start-entrypoint`は、実行可能なアプリまたはツールに利用入口が見つからない場合に出します。ライブラリ、フレームワーク、ドキュメント集、教材・独立サンプル集にはアプリ用ランチャーを要求しません。入口として認識するのは、ルートランチャー、Node/Python CLI、Makefileの起動ターゲット、Docker/Compose、Goの`main`、ブラウザ拡張manifest、一般的なREADME起動コマンドなどです。

`readme-missing-verification`は、検証用見出しに加えて、README内の具体的なtest・lint・typecheck・build-checkコマンドや、明示された手動テスト用playground/previewも証拠として扱います。README自体がない場合は`missing-readme`を出し、このcheckは重ねて出しません。

`secret-risk-file`は、秘密情報らしいファイルをGit状態と合わせて確認します。`.env.example`など明示的な例示ファイルは除外します。追跡済みの`.env.*`、`.npmrc`、`.pypirc`は、機密性のあるキーに空でない非テンプレート値が設定されている場合に警告します。PEM・KEY・PFX・P12などの秘密鍵を含み得る形式は、内容をレポートへ転記せずファイル単位で警告します。これは専用シークレットスキャナーではなく、既知のトークン形式を網羅的に探索するものではありません。

`generated-artifact-present`は、Pythonキャッシュ、依存ツリー、生成出力に加えて、追跡済みの`.idea`や`.DS_Store`などローカル環境由来の項目を検出します。一方、`build/`という名前でも、追跡済みのTypeScript・YAML・Props・スクリプトなどが置かれたソース／設定ディレクトリは生成物として扱いません。

`workspace-specific-dependency`は、Git追跡された通常のプロジェクト文書・実装・スクリプトが、Windowsの絶対パス、ユーザープロファイル相対パス、またはユーザーホーム配下にあるエージェント用shared Skillディレクトリを必須依存にしている場合に出します。共有Skillはエージェント側の作業支援であり、cloneしたリポジトリの通常build・test・runtime依存へしないことを意図しています。テストfixture、examples、benchmarks、audits内の検査用文字列はこのcheckから除外します。

`internal-agent-plan-tracked`は、`docs/superpowers/`配下に内部エージェント向け計画書がGit追跡されている場合に出します。製品として残すべき設計判断は通常の`docs/`へ整理し、一時的なagent実行計画を公開・配布用treeへ混ぜないことを意図しています。
`hardcoded-local-path`は、作業マシン固有の絶対パスがリポジトリへ残っていないかを確認します。対象は`C:\`などのドライブ絶対パスと、`/home/`、`/Users/`、`/root/`、`/media/`、`/mnt/<drive>/`、`/cygdrive/<drive>/`配下のパスです。`C:\path\to\target-repo`や`/home/<user>/app`のような説明用プレースホルダー、`%USERPROFILE%`・`${HOME}`などの変数展開、URL内の`/home/...`は対象外です。Gitがignoreしている未追跡ファイルは公開されないため検査しません。`tests/`、`test/`、`fixtures/`、`examples/`、`benchmarks/`、`audits/`配下は検査用文字列として`workspace-specific-dependency`と同じく除外します。レポートにはファイル名、行番号、`C:\`や`/home/`といったルート部分だけを記録し、パス本体は転記しません。Git追跡されたファイルがエージェント用shared Skillディレクトリへ依存している場合は、別途`workspace-specific-dependency`がHIGHとして報告します。

`hardcoded-ip-address`は、環境固有のIPv4リテラルを確認します。`192.168.*`、`10.*`、`172.16-31.*`、`100.64-127.*`のプライベートアドレスはLOW、その他の到達可能なアドレスはMEDIUMです。loopback（`127.*`）、`0.*`、ネットマスク・ブロードキャスト、link-local（`169.254.*`）、multicast以上（`224.*`以降）、RFC 5737の文書用アドレス、RFC 2544のベンチマーク用アドレスは対象外です。`v1.2.3.4`や`1.2.3.4-beta`のようなバージョン表記、`<AssemblyVersion>1.0.0.0</AssemblyVersion>`のようにversion・release・assembly・buildの直後に置かれた4桁組、`10.0.0.0`のようなネットワークアドレス表記も除外します。前後に手がかりのない散文中の4桁組バージョン番号は誤検知し得ます。IPv6、Gitがignoreしている未追跡ファイル、および`tests/`などの検査用ディレクトリは対象外です。アドレスの値はレポートへ転記せず、ファイル名、行番号、私設／到達可能の区別だけを記録します。

`broken-markdown-link`は、インラインコードとフェンスコード内のMarkdown例を検査対象から外し、`about:`・`cid:`などURIスキーム付き参照と、拡張子のない`/getting-started`のようなサイト内ルートをローカルファイルとして扱いません。`/assets/image.png`のような拡張子付きルート相対ファイルは検査し、同じMarkdownファイル内の同一リンクは1件にまとめます。
