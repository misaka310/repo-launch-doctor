# Fixed-SHA benchmark

This benchmark evaluates Repo Launch Doctor against 20 public repositories pinned to immutable 40-character commit SHAs. It is an explicit, networked verification workflow; normal unit tests and GitHub Actions do not fetch the corpus.

## Run in resumable batches

Use owner-qualified target IDs so repositories with the same basename cannot collide:

```bash
python benchmarks/run_benchmarks.py \
  --only pallets--click \
  --only tiangolo--typer \
  --only psf--black \
  --only psf--requests \
  --allow-partial
```

Continue with another batch using `--resume`. A cached result is reused only when its JSON is valid and the local Git repository has the expected origin URL, contains the pinned commit, and has that exact commit checked out.

```bash
python benchmarks/run_benchmarks.py --resume --only pytest-dev--pytest --allow-partial
```

`--force` bypasses successful target-result reuse and refetches the pinned SHA. Fetch, checkout, and Doctor scan each have independent timeouts and error stages.

## Fetch contract

The runner does not use a normal clone. For each target it initializes a local repository under `.benchmark-cache/repositories/`, configures `origin`, fetches only the pinned commit with `--depth=1 --no-tags`, and checks out `FETCH_HEAD` detached.

Local repositories, scan reports, per-target resume data, and partial aggregates remain under `.benchmark-cache/`, which is ignored by Git.

## Partial and formal results

A partial run exits with code 1 by default. `--allow-partial` changes only that inspection exit code; it does not make the run complete and does not publish formal results.

Formal files are written only when all 20 targets satisfy every condition below:

- fetch succeeded
- checkout succeeded at the pinned SHA
- Doctor returned a complete scan
- no execution error occurred
- all 20 targets are eligible for metrics

A complete run publishes:

```text
benchmarks/results/latest.json
benchmarks/results/latest.md
benchmarks/results/targets/*.json
```

Run the final aggregation with:

```bash
python benchmarks/run_benchmarks.py --resume
```

The current published run records 20 successful fetches, 20 successful checkouts, 20 complete scans, 20 metric-eligible targets, and zero execution errors. See [`results/latest.md`](results/latest.md).

## Metric semantics

Labels in `manifest.json` describe repository facts at the pinned SHA. A label is evaluated only for a target that fetched, checked out, and scanned completely. Fetch failures, checkout failures, scan timeouts, scan exceptions, and `INCOMPLETE` reports are execution failures, not false negatives.

Each check reports positive and negative label counts, TP, FP, FN, TN, precision, recall, and coverage status. A zero denominator is represented as `null`, never as 100%. The current corpus has no positive labels, so recall is `null` with `coverage_status: no_positive_labels`.

Target replacements and their fixed-SHA evidence are recorded in [`label-history.md`](label-history.md). Verified real-world Before/After cases remain at zero and are tracked separately in [`../docs/before-after.md`](../docs/before-after.md).
