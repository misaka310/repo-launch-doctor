# Fixed-SHA benchmark

Run `python benchmarks/run_benchmarks.py` explicitly. It fetches each pinned SHA into a temporary directory, scans it, and writes `results/latest.json` and `results/latest.md`. Normal unit tests and CI do not run this networked command.

The default command exits non-zero unless every manifest target fetches and scans completely. Use `--allow-partial` only to inspect a partial run; its result records `complete_run: false`, excludes failed and incomplete targets from metrics, and does not claim corpus precision or recall. `--only <name>` is for reproducing one target. Each metric reports positive/negative label counts and a coverage status; a zero denominator is `null`, never 100%.
