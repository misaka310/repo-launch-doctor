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
