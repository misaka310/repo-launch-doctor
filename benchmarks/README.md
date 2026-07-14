# Fixed-SHA benchmark

Run `python benchmarks/run_benchmarks.py` explicitly. It clones each manifest repository into a temporary directory, checks out the pinned commit, and writes `results/latest.json` and `results/latest.md`. Normal unit tests and CI do not run this networked command.
