# Fixed-SHA benchmark results

Generated: 2026-07-14T17:16:41.179823+00:00
Tool version: 0.3.0
Complete run: `true`; partial result: `false`

## Execution summary

- Targets: 20
- Fetch succeeded / failed: 20 / 0
- Checkout succeeded / failed: 20 / 0
- Scans complete / incomplete: 20 / 0
- Eligible for metrics: 20
- Execution errors: 0

## Metrics

| Check | + | - | TP | FP | FN | TN | Precision | Recall | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `missing-start-entrypoint` | 5 | 15 | 5 | 0 | 0 | 15 | 1.0000 | 1.0000 | sufficient |
| `readme-missing-verification` | 6 | 4 | 6 | 0 | 0 | 4 | 1.0000 | 1.0000 | sufficient |

## Targets

- `ckala62rus--go-architecture-v2--2fc3164e0d8c` `2fc3164e0d8cce622d5f9dc30141df61e1de6c61` — Go web application (before launcher) — verdict `FAIL` — findings: missing-start-entrypoint, generated-artifact-present, missing-license, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `ckala62rus--go-architecture-v2--df7c7b4f0aec` `df7c7b4f0aece8aaa4a2829f2a905419d023663c` — Go web application (after launcher) — verdict `PASS_WITH_NOTES` — findings: generated-artifact-present, missing-license, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `cbogdan97--automation_test--dab37fe8a924` `dab37fe8a9243a3436ba14381329db34e147aa26` — Cypress application (before launcher) — verdict `FAIL` — findings: missing-readme, missing-start-entrypoint, missing-license, missing-security-doc
- `cbogdan97--automation_test--4f89826f29b3` `4f89826f29b32764df58255cb77f6f70cf17ca62` — Cypress application (after launcher) — verdict `FAIL` — findings: missing-readme, missing-license, missing-security-doc
- `fredrikbwinlas--tictactoeyellowbelt--c343ecc4bf00` `c343ecc4bf0055e02941f025d64eeefcdf17563d` — .NET console application (before launcher) — verdict `FAIL` — findings: missing-start-entrypoint, missing-license, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `fredrikbwinlas--tictactoeyellowbelt--8b895bdfe1a2` `8b895bdfe1a2e9c75818dfa3ca7b8a293df3a24f` — .NET console application (after launcher) — verdict `PASS_WITH_NOTES` — findings: missing-license, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `jrock474--back-end-project--1c458ffb806f` `1c458ffb806ffd576c35f9f5b0c03f58e4da203d` — Node.js backend (before start script) — verdict `FAIL` — findings: secret-risk-file, missing-readme, missing-start-entrypoint, generated-artifact-present, missing-favicon
- `jrock474--back-end-project--19a57b0de1a1` `19a57b0de1a1bf1c1898b6a986e27e0fa6fe19fe` — Node.js backend (after start script) — verdict `FAIL` — findings: secret-risk-file, missing-readme, generated-artifact-present, missing-favicon
- `kierajreed--random-recipe-wiki--c55ec709a2d8` `c55ec709a2d8c62e38f6d892b9148387c0caf050` — Node.js application (before start script) — verdict `FAIL` — findings: missing-start-entrypoint, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `kierajreed--random-recipe-wiki--a1a64d1eeeaf` `a1a64d1eeeaf93e3a46469d3850bdaaa93b5c5e0` — Node.js application (after start script) — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `pallets--click--b67832c2167e` `b67832c2167e5b0ff6764a8c04a0a9087e697b5a` — Python CLI — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `psf--black--51abf53080b0` `51abf53080b09eab12143727641ff1e2cd39d8c9` — Python CLI — verdict `FAIL` — findings: broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, readme-missing-limitations, readme-missing-requirements
- `fazilet1820--laraveluppgift--1ea9b1fd97bd` `1ea9b1fd97bdd1b8da7d3d729a000b0816f00eec` — Laravel web application — verdict `PASS_WITH_NOTES` — findings: generated-artifact-present, missing-health-check, missing-license, readme-missing-usage, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `gabrielvelasco--lead-management--ca4899e5458a` `ca4899e5458a1f4db062f60abf85b2f89b7ef596` — FastAPI web application — verdict `FAIL` — findings: broken-markdown-link, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, generated-artifact-present, missing-license, readme-missing-setup, readme-missing-usage, missing-config-example, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `pytest-dev--pytest--67a174fcee35` `67a174fcee355334c53588be2eeba8df702477e9` — Python CLI/library — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, readme-missing-limitations, readme-missing-requirements
- `gothinkster--react-redux-realworld-example-app--ee72eba40563` `ee72eba4056392c95a27bc48d385d3f54ba38a18` — Web application — verdict `PASS_WITH_NOTES` — findings: missing-health-check, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `sindresorhus--open-cli--199a2033ae41` `199a2033ae41c65928b8b8bfd7936082a135aa8c` — Node.js CLI — verdict `FAIL` — findings: secret-risk-file, readme-missing-verification, missing-config-example, readme-missing-limitations, readme-missing-requirements
- `kettanaito--naming-cheatsheet--7b90cd7b2d3c` `7b90cd7b2d3ccb104a4443d5e7e152b8fd400533` — Documentation-only — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `cu-ecen-aeld--assignments-3-and-later-jqiaobln--002d42426770` `002d4242677098a65c7352d4f39784c103da1649` — Embedded Linux assignment repository — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, missing-config-example, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `pallets--itsdangerous--672971d66a2e` `672971d66a2ef9f85151e53283113f33d642dabd` — Python library — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-security-doc, readme-missing-limitations, readme-missing-requirements

## False positives

- None

## False negatives

- None

## Execution error details

- None
