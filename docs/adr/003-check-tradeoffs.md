# ADR 003: Check-level trade-offs and corpus coverage

| Check family | Primary priority | Likely false positive | Likely miss | Suppressible | Corpus result |
|---|---|---|---|---|---|
| `missing-start-entrypoint` | Avoid false positives | libraries, metadata CLI | unusual build systems | yes, project type | `benchmarks/results/latest.md` |
| `readme-missing-*` | Avoid false positives | prose-only README | nonstandard headings | yes | `benchmarks/results/latest.md` |
| verification commands | Avoid false positives | mixed frameworks | custom runners | n/a (metadata) | `benchmarks/results/latest.md` |
| `secret-risk-file` | Avoid false negatives | safe named fixtures | arbitrary names | no | not yet labeled |
| `scan-incomplete` | Avoid false negatives | conservative read failure | none known | no | unit tests |

The benchmark corpus initially labels the confirmed entrypoint regression. Other check IDs must receive independently reviewed labels before their precision/recall is claimed. LOW/MEDIUM remaining false positives are listed by the generated result; they are not silently relabeled.
