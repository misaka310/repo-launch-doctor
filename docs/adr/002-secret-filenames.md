# ADR 002: Filename risk is separate from content inspection

## Decision

Secret-risk checks use filenames and Git tracking/ignore state, never values from the file. This keeps a read-only safety check from exposing secret contents in findings or reports.

## Trade-off

This deliberately has false positives (for example, a safe fixture named `secrets.json`) and false negatives (a secret in an innocuously named file). It is suppressible only through correct Git ignore state, not by hiding the check. The corpus will measure this check when labels are added.
