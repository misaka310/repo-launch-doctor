# Extended current audit — after fixes

- Selected / eligible / excluded repositories: 30 / 29 / 1
- Unit: individual warning instance (repository + path, or repository + Markdown source + target)
- Manual review was completed after all selected scan attempts.

| Check | Actual issues | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `secret-risk-file` | 5 | 5 | 0 | 0 | 1.0000 | 1.0000 |
| `generated-artifact-present` | 9 | 9 | 0 | 0 | 1.0000 | 1.0000 |
| `broken-markdown-link` | 58 | 58 | 0 | 0 | 1.0000 | 1.0000 |

TN is not reported because there is no finite enumerated set of all possible file and link instances.

## Scope limitations

- The repositories are the same selected current snapshot used by the main current audit.
- Secret review covers Doctor's sensitive-file scope plus a bounded independent scan for common credential patterns; it is not a full secret scanner.
- Runtime validity, exploitability, and whether a committed development certificate is used in production were not tested.
- TN is intentionally omitted for instance-level checks because the negative instance universe is not enumerated.
