# Fixed-SHA benchmark

This benchmark evaluates Repo Launch Doctor against 20 public repository revisions pinned to immutable 40-character commit SHAs. The corpus includes five verified Before/After pairs, ten additional negative examples, and labels for two checks. It is an explicit networked workflow; normal unit tests and GitHub Actions do not fetch the corpus.

The Before/After entries compare public third-party history. Repo Launch Doctor did not modify those repositories.

## Run in resumable batches

Target IDs contain the repository owner, name, and the first 12 characters of the pinned SHA. This allows two commits from the same repository to coexist without cache or result collisions.

```bash
python benchmarks/run_benchmarks.py \
  --only ckala62rus--go-architecture-v2--2fc3164e0d8c \
  --only ckala62rus--go-architecture-v2--df7c7b4f0aec \
  --allow-partial
```

Continue with another batch using `--resume`. A cached result is reused only when its JSON is valid and the local Git repository has the expected origin URL, contains the pinned commit, and has that exact commit checked out.

```bash
python benchmarks/run_benchmarks.py --resume
```

`--force` bypasses successful target-result reuse and refetches the pinned SHA. Fetch, checkout, and Doctor scan have independent timeouts and error stages.

## Fetch contract

The runner does not use a normal clone. For each target it initializes a repository under `.benchmark-cache/repositories/`, configures `origin`, fetches only the pinned commit with `--depth=1 --no-tags`, and checks out `FETCH_HEAD` detached.

Local repositories, scan reports, resume data, research candidates, and partial aggregates remain under `.benchmark-cache/`, which is ignored by Git.

## Partial and formal results

A partial run exits with code 1 by default. `--allow-partial` changes only that inspection exit code; it does not make the run complete or publish formal results.

Formal files are replaced only when all 20 targets meet every condition:

- fetch succeeded;
- checkout succeeded at the pinned SHA;
- Doctor returned a complete scan;
- no execution error occurred; and
- all 20 targets are eligible for metrics.

A complete run publishes:

```text
benchmarks/results/latest.json
benchmarks/results/latest.md
benchmarks/results/targets/*.json
```

The current published run records 20 successful fetches, 20 successful checkouts, 20 complete scans, 20 metric-eligible targets, and zero execution errors. See [`results/latest.md`](results/latest.md).

## Labels and metrics

Labels in `manifest.json` describe repository facts at the pinned SHA. They are assigned from source layout, documentation, and the actual public diff—not from the result the Doctor happened to produce. An execution failure is excluded from classification metrics rather than counted as a false negative.

Current results:

| Check | Positive | Negative | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `missing-start-entrypoint` | 5 | 15 | 5 | 0 | 0 | 15 | 1.0 | 1.0 |
| `readme-missing-verification` | 6 | 4 | 6 | 0 | 0 | 4 | 1.0 | 1.0 |

These figures are exact for this fixed corpus only. They do not establish universal accuracy or runtime correctness.

Research methodology, accepted and rejected candidates, and prior corpus changes are recorded in [`label-history.md`](label-history.md). The five verified public-history pairs are documented in [`../docs/before-after.md`](../docs/before-after.md).
