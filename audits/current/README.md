# Current public-repository audit

This audit measures Repo Launch Doctor against repositories as they existed at the time of selection. It is the primary evidence for current behavior. The historical fixed-SHA corpus under `benchmarks/` is a separate regression test and is not evidence that current repositories still have those historical problems.

## Order of work

The workflow enforces this order:

1. Select all repositories without using Doctor output.
2. Record each selected default-branch HEAD commit.
3. Attempt every selected repository scan.
4. Review source and README evidence only after all attempts finish.
5. Assign manual labels and calculate TP, FP, FN, and TN.

The recorded commit is an audit timestamp. It is not used to search for a convenient historical failure.

## Selection

The July 2026 audit selected 30 public repositories: five each from Python, JavaScript, TypeScript, Go, C#, and Java GitHub Search results.

Selection constraints:

- not a fork;
- not archived;
- 2 to 100 stars;
- repository size from 50 to 5,000 KB;
- pushed since January 1, 2026;
- first 100 results sorted by recent update, then deterministically reordered with a declared seed.

This is a stratified snapshot of small, recently pushed repositories. It is not a statistically representative sample of all GitHub repositories.

The selected repositories and their HEAD commits are in [`selection.json`](selection.json). Manual labels and rationales are in [`manual-review.json`](manual-review.json).

## Results

Thirty repositories were selected. Twenty-nine were checked out and scanned completely. One selected repository was excluded because Windows could not check out a path containing the reserved name `aux.js`; it was not replaced with a more convenient candidate.

### Before fixes discovered by this audit

| Check | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `missing-start-entrypoint` | 1 | 15 | 0 | 13 | 0.0625 | 1.0000 |
| `readme-missing-verification` | 16 | 6 | 1 | 6 | 0.7273 | 0.9412 |

The baseline is preserved in [`results/baseline.md`](results/baseline.md). It showed that the start-entrypoint rule was not useful in its previous form because it treated many libraries, documentation workspaces, frameworks, browser extensions, and documented non-BAT launch commands as missing an entrypoint.

### After fixes, using the same repositories and manual labels

| Check | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `missing-start-entrypoint` | 1 | 0 | 0 | 28 | 1.0000 | 1.0000 |
| `readme-missing-verification` | 16 | 0 | 1 | 12 | 1.0000 | 0.9412 |

The complete result and per-repository rationales are in [`results/latest.md`](results/latest.md).

The remaining verification false negative is a repository with no README. Doctor reports `missing-readme`, but does not additionally emit `readme-missing-verification`. This limitation is retained rather than counted as a successful verification detection.

These figures describe only this 29-repository eligible snapshot. They do not establish universal accuracy, runtime correctness, or the prevalence of repository problems across GitHub.

## Extended instance-level audit

The same completed 29-repository snapshot was also reviewed for individual `secret-risk-file`, `generated-artifact-present`, and `broken-markdown-link` instances. Labels were assigned per path or per Markdown source/target pair, rather than treating a whole repository as one result.

### Before fixes discovered by the extended review

| Check | Actual issues | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `secret-risk-file` | 5 | 5 | 5 | 0 | 0.5000 | 1.0000 |
| `generated-artifact-present` | 9 | 3 | 3 | 6 | 0.5000 | 0.3333 |
| `broken-markdown-link` | 58 | 58 | 27 | 0 | 0.6824 | 1.0000 |

### After fixes, using the same repositories and labels

| Check | Actual issues | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `secret-risk-file` | 5 | 5 | 0 | 0 | 1.0000 | 1.0000 |
| `generated-artifact-present` | 9 | 9 | 0 | 0 | 1.0000 | 1.0000 |
| `broken-markdown-link` | 58 | 58 | 0 | 0 | 1.0000 | 1.0000 |

The secret review confirmed five warning instances. Four private-key-bearing certificate-bundle instances across two repositories merit private maintainer notification; redacted drafts were prepared locally, but no maintainer has been contacted. Exact secret-related repositories, paths, certificate subjects, passwords, and values are intentionally withheld from public artifacts until private notification occurs. One additional confirmed warning is a tracked development environment containing a non-placeholder sensitive assignment, but no evidence showed that it was a live external credential.

Generated-artifact and broken-link truth instances are published in [`extended-review.json`](extended-review.json). Aggregate before/after results are in [`results/extended-baseline.md`](results/extended-baseline.md) and [`results/extended-latest.md`](results/extended-latest.md).

For these instance-level checks, TN is not reported because there is no finite enumerated universe of every possible non-secret file, non-generated path, or valid link instance. The secret review included a bounded independent scan for common credential patterns, but it is not a substitute for a dedicated secret scanner.

## Reproduce

Network access and Git are required.

To re-scan the published selection from a fresh clone:

```bash
python audits/current/current_audit.py scan --resume
python audits/current/current_audit.py packet
# Review every eligible target and update audits/current/manual-review.json,
# including a reviewed_at timestamp after the completed scan.
python audits/current/current_audit.py publish
```

Use `python audits/current/current_audit.py select` only when starting a new audit after archiving the previous selection and results. Selection refuses to overwrite an existing `selection.json` unless `--force` is given, and outcome-dependent reselection is rejected while raw results exist. Raw repositories, scan reports, and the review packet stay under ignored `.current-audit-cache/`. Published evidence contains repository URLs, commit SHAs, labels, rationales, and aggregate metrics without local absolute paths.
