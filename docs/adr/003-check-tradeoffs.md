# ADR 003: Check-level trade-offs and corpus coverage

| Check family | Primary priority | Likely false positive | Likely miss | Suppressible | Corpus result |
|---|---|---|---|---|---|
| `missing-start-entrypoint` | Avoid false positives | libraries, metadata CLI | unusual build systems | yes, project type | `benchmarks/results/latest.md` |
| `readme-missing-*` | Avoid false positives | prose-only README | nonstandard headings | yes | `benchmarks/results/latest.md` |
| verification commands | Avoid false positives | mixed frameworks | custom runners | n/a (metadata) | `benchmarks/results/latest.md` |
| `secret-risk-file` | Avoid false negatives | safe named fixtures | arbitrary names | no | not yet labeled |
| `scan-incomplete` | Avoid false negatives | conservative read failure | none known | no | unit tests |
| `hardcoded-local-path` | Avoid false positives | prose or fixtures that quote a real path | non-ASCII single-segment paths, placeholder-looking real paths | yes | not yet labeled |
| `hardcoded-ip-address` | Avoid false positives | four-part version numbers without a prefix or suffix | IPv6, addresses split across tokens | yes | not yet labeled |

The benchmark corpus initially labels the confirmed entrypoint regression. Other check IDs must receive independently reviewed labels before their precision/recall is claimed. LOW/MEDIUM remaining false positives are listed by the generated result; they are not silently relabeled.
