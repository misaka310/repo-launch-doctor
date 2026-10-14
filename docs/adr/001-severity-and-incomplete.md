# ADR 001: Severity, score, and incomplete scans

## Decision

`BLOCKER` prevents a release decision: a scan is incomplete or a secret-risk filename is tracked. `HIGH` is a concrete launch or documentation break. `MEDIUM` is material readiness evidence missing; `LOW` is a useful public-readiness improvement. `INFO` is non-scoring context.

An incomplete scan is always `BLOCKER`, has `score: null`, and exits 2 even when `--fail-on none` is selected. A partial inventory cannot support a public-release decision.

Scores subtract 40/20/8/2/0 respectively. They make prioritization visible, not a publication authorization: context, false positives, and unscanned concerns remain. The weights are deliberately simple and have no empirical calibration; the benchmark records accuracy per check instead of treating score as accuracy.

## Trade-off

The tool prefers avoiding unsafe success claims over returning a usable-looking partial result. This can stop scans on unreadable text that would not affect a particular release. The behavior is intentional and suppressible neither by `ignore_checks` nor `--fail-on none`.
