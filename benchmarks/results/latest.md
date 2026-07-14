# Fixed-SHA benchmark results

Generated: 2026-07-14T15:52:48.745038+00:00
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
| `missing-start-entrypoint` | 0 | 20 | 0 | 9 | 0 | 11 | 0.0000 | null | no_positive_labels |
| `readme-missing-verification` | 0 | 1 | 0 | 0 | 0 | 1 | null | null | no_positive_labels |

## Targets

- `pallets--click` `b67832c2167e5b0ff6764a8c04a0a9087e697b5a` — Python CLI — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `tiangolo--typer` `3a3bd0f20a417835d4b4505a0bf834620e024cdb` — Python CLI — verdict `FAIL` — findings: secret-risk-file, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `psf--black` `51abf53080b09eab12143727641ff1e2cd39d8c9` — Python CLI — verdict `FAIL` — findings: broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, readme-missing-limitations, readme-missing-requirements
- `psf--requests` `f361ead047be5cb873174218582f7d8b9fcd9f49` — Python library — verdict `FAIL` — findings: secret-risk-file, secret-risk-file, secret-risk-file, secret-risk-file, secret-risk-file, secret-risk-file, secret-risk-file, readme-missing-usage, readme-missing-verification, missing-config-example, readme-missing-limitations, readme-missing-requirements
- `pallets--flask` `36e4a824f340fdee7ed50937ba8e7f6bc7d17f81` — Python library — verdict `FAIL` — findings: secret-risk-file, missing-health-check, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `pytest-dev--pytest` `67a174fcee355334c53588be2eeba8df702477e9` — Python CLI/library — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, readme-missing-limitations, readme-missing-requirements
- `pocketpy--pocketpy` `e14478543648be32ce4140c1d5a44d29677d6720` — Python runtime — verdict `FAIL` — findings: broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, missing-start-entrypoint, readme-missing-setup, readme-missing-verification, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `sindresorhus--open-cli` `199a2033ae41c65928b8b8bfd7936082a135aa8c` — Node.js CLI — verdict `FAIL` — findings: secret-risk-file, missing-start-entrypoint, readme-missing-verification, missing-config-example, readme-missing-limitations, readme-missing-requirements
- `sindresorhus--trash-cli` `ee5b70565263a1027b4027d89cfb281bb71551e4` — Node.js CLI — verdict `FAIL` — findings: secret-risk-file, missing-start-entrypoint, readme-missing-verification, missing-config-example, readme-missing-limitations, readme-missing-requirements
- `google--zx` `00a2c484e219c2e84bfc3a199febf7fbce2cfbf4` — Node.js CLI — verdict `FAIL` — findings: broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, missing-start-entrypoint, generated-artifact-present, readme-missing-verification, missing-config-example, missing-favicon, readme-missing-limitations, readme-missing-requirements
- `expressjs--express` `ae6dd37680e3a00618d6c8a3e522f0ee4eeba1a4` — Dynamic web framework — verdict `FAIL` — findings: secret-risk-file, missing-start-entrypoint, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `gothinkster--react-redux-realworld-example-app` `ee72eba4056392c95a27bc48d385d3f54ba38a18` — Web application — verdict `PASS_WITH_NOTES` — findings: missing-health-check, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `preactjs--preact` `67c9935e3e692bcf43f37b34bd7429054903c0d1` — JavaScript library — verdict `PASS_WITH_NOTES` — findings: missing-health-check, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `vuejs--core` `9e03beb6b4c85a9d5b49b731c08263aa648e2a2a` — JavaScript monorepo — verdict `PASS_WITH_NOTES` — findings: missing-health-check, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, readme-missing-limitations, readme-missing-requirements
- `changesets--changesets` `162419dc99278cbdd52db6eabfecd7b8b4eac640` — JavaScript monorepo — verdict `FAIL` — findings: broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, broken-markdown-link, missing-start-entrypoint, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `alangpierce--sucrase` `280ee202e73b18e396069782bd41e1eaaccbf620` — JavaScript compiler/library — verdict `FAIL` — findings: missing-start-entrypoint, readme-missing-setup, readme-missing-verification, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `kettanaito--naming-cheatsheet` `7b90cd7b2d3ccb104a4443d5e7e152b8fd400533` — Documentation-only — verdict `FAIL` — findings: missing-start-entrypoint, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `sindresorhus--electron-boilerplate` `74c68912708d7bd40f51116064c11306bebf65ec` — Desktop application — verdict `PASS_WITH_NOTES` — findings: generated-artifact-present, missing-health-check, readme-missing-usage, readme-missing-verification, missing-config-example, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `electron--simple-samples` `3e4372b0273272ce40a267ad4d583cd6201aa540` — Desktop application — verdict `FAIL` — findings: missing-start-entrypoint, readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-favicon, missing-security-doc, readme-missing-limitations, readme-missing-requirements
- `pallets--itsdangerous` `672971d66a2ef9f85151e53283113f33d642dabd` — Python library — verdict `PASS_WITH_NOTES` — findings: readme-missing-setup, readme-missing-usage, readme-missing-verification, missing-config-example, missing-security-doc, readme-missing-limitations, readme-missing-requirements

## False positives

- `pocketpy--pocketpy` `e14478543648be32ce4140c1d5a44d29677d6720`: ['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']
- `sindresorhus--open-cli` `199a2033ae41c65928b8b8bfd7936082a135aa8c`: ['secret-risk-file', 'missing-start-entrypoint', 'readme-missing-verification', 'missing-config-example', 'readme-missing-limitations', 'readme-missing-requirements']
- `sindresorhus--trash-cli` `ee5b70565263a1027b4027d89cfb281bb71551e4`: ['secret-risk-file', 'missing-start-entrypoint', 'readme-missing-verification', 'missing-config-example', 'readme-missing-limitations', 'readme-missing-requirements']
- `google--zx` `00a2c484e219c2e84bfc3a199febf7fbce2cfbf4`: ['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'generated-artifact-present', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'readme-missing-limitations', 'readme-missing-requirements']
- `expressjs--express` `ae6dd37680e3a00618d6c8a3e522f0ee4eeba1a4`: ['secret-risk-file', 'missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']
- `changesets--changesets` `162419dc99278cbdd52db6eabfecd7b8b4eac640`: ['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']
- `alangpierce--sucrase` `280ee202e73b18e396069782bd41e1eaaccbf620`: ['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']
- `kettanaito--naming-cheatsheet` `7b90cd7b2d3ccb104a4443d5e7e152b8fd400533`: ['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']
- `electron--simple-samples` `3e4372b0273272ce40a267ad4d583cd6201aa540`: ['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']

## False negatives

- None

## Execution error details

- None
