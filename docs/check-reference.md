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

`broken-markdown-link`は、インラインコードとフェンスコード内のMarkdown例を検査対象から外し、`about:`・`cid:`などURIスキーム付き参照と、拡張子のない`/getting-started`のようなサイト内ルートをローカルファイルとして扱いません。`/assets/image.png`のような拡張子付きルート相対ファイルは検査し、同じMarkdownファイル内の同一リンクは1件にまとめます。
