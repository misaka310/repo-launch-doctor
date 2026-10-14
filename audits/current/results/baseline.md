# Current public-repository audit

Selection completed: 2026-07-14T18:37:01.341101+00:00
All scan attempts completed: 2026-07-14T19:01:58.582992+00:00
Manual review completed: 2026-07-15T01:06:39.947301+00:00
Tool version: 0.3.0
Selected / eligible / excluded: 30 / 29 / 1

Repositories were selected first, every selected HEAD commit was attempted second, and manual labels were assigned only after all attempts finished. Excluded targets are not included in classification metrics.

This is a stratified snapshot of 30 small, recently pushed public repositories across six language buckets. It is not a statistically representative sample of all GitHub repositories.

## Metrics

| Check | + | - | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `missing-start-entrypoint` | 1 | 28 | 1 | 15 | 0 | 13 | 0.0625 | 1.0000 |
| `readme-missing-verification` | 17 | 12 | 16 | 6 | 1 | 6 | 0.7273 | 0.9412 |

## False positives

- `colfin22/intro-quiz` `077ff57ce4052057687cf2ac2a3bfe58951d512e` — observed `['readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `rizmyabdulla/Ripple` `499496d2cca546b3b85b0aef68a0b3b5a334239a` — observed `['broken-markdown-link', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `ismayc/world-cup-viewer` `0dd6deda9237379f1c5cc5e3046e2ab05553a15e` — observed `['readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `fratei/creative-ware-hq` `7b17d0798ec9f42609fd0c5b725aa3e72ee2a816` — observed `['broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `sseanliu/PaperClip` `b8cbf3a2d66e34a8cf0261c5fd37428ee830c5c2` — observed `['missing-start-entrypoint', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `vaneui/vaneui` `37808f6b5f2932dd465da3e4c53276286ee93e2b` — observed `['missing-start-entrypoint', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `obsidianlabs-io/obsidian-admin-vue` `95e85e3f489ea23bbbe41b67093cfc2c9536edd6` — observed `['secret-risk-file', 'secret-risk-file', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'generated-artifact-present', 'readme-missing-verification', 'missing-favicon', 'readme-missing-limitations']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `stolostron/volsync-addon-controller` `d0924b2b2a0b108394ab499a8de6d146f5ed7098` — observed `['missing-start-entrypoint', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `openshift/lightspeed-agentic-operator` `eb885d352da5889430c217735f0ae34ca726fee0` — observed `['broken-markdown-link', 'missing-start-entrypoint', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `toolsdotgo/sfm` `c669389cf90f89085811535ba6bddf6fd2e64fa9` — observed `['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `bonnetn/minecraft-reverse-proxy` `e205833b64dfecec33641c3aba166897117a0c34` — observed `['missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `scribe-org/Scribe-Server` `bf1e6b7b06203e9c0b6a3c0b88ddd3b544d7bf3f` — observed `['missing-start-entrypoint', 'readme-missing-usage', 'readme-missing-verification', 'missing-favicon', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `Doughm/UCurses` `5875a2e0e125abf4ea845e4ee950b8e3bd337a1b` — observed `['missing-start-entrypoint', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `thomhurst/Sourcy` `ce105d55e4e09dd4eea1fe043e399a1a6457de8c` — observed `['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'generated-artifact-present', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `kellylford/QuickMail` `1cf730a87312b867be6bb895f164061acd83e8b8` — observed `['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'markdown-link-outside-root', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'readme-missing-limitations']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `Particular/NServiceBus.Persistence.AzureTable` `27aa8c7ef17dd392a82a0c14ad55459e75a61225` — observed `['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'missing-config-example', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': False}`
- `credfeto/credfeto-cache-proxy` `cb1d80a6268239f742b50dcd9065efe370b5e202` — observed `['secret-risk-file', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'generated-artifact-present', 'markdown-link-outside-root', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `apache/johnzon` `1b58078bb9496219c17374f48657cdb231bb4632` — observed `['missing-readme', 'missing-start-entrypoint']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`
- `KirtiPatiya25/DSA` `25e7c1d7d87533e4b8b0d4d875e24ad714682e76` — observed `['missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`

## False negatives

- `apache/johnzon` `1b58078bb9496219c17374f48657cdb231bb4632` — observed `['missing-readme', 'missing-start-entrypoint']`; labels `{'missing-start-entrypoint': False, 'readme-missing-verification': True}`

## Excluded targets

- `nlp-compromise/it-compromise` `d766d4ee8d962b45dc75ae03d178c9e1cb4c8abe` — stage `checkout`: error: invalid path 'data/lexicon/aux.js'


## Reviewed repositories

### colfin22/intro-quiz

- Commit: `077ff57ce4052057687cf2ac2a3bfe58951d512e`
- Language bucket: Python
- Doctor project type: `static-web`
- Doctor findings: `['readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README provides a Docker Compose launch command and the Dockerfile declares the service command.
- `readme-missing-verification` label: `false` — The README documents `python -m pytest` in its contributor verification guidance.

### opendatahub-io/agentic-ci

- Commit: `b8b5c540195290facffee7cdcbb6b9c84067177f`
- Language bucket: Python
- Doctor project type: `docs`
- Doctor findings: `['readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The packaged CLI exposes the agentic-ci command and the README documents its usage.
- `readme-missing-verification` label: `true` — The README documents product use but no concrete test or verification command.

### varghese25/PythonCourse_26_03_2025

- Commit: `1549826fcec45120a78bfdd31c962d7a4a481c76`
- Language bucket: Python
- Doctor project type: `auto`
- Doctor findings: `['generated-artifact-present', 'generated-artifact-present', 'generated-artifact-present', 'missing-license', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a collection of Python course examples rather than one application that requires a repository-level launcher.
- `readme-missing-verification` label: `true` — The README contains course notes but no concrete verification guidance.

### Rayan-ouer/minimal-token-db-api

- Commit: `506d44db5c1e1542d975e2dd703e6e594adc3a7b`
- Language bucket: Python
- Doctor project type: `auto`
- Doctor findings: `['missing-license', 'readme-missing-usage', 'readme-missing-verification', 'missing-security-doc', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The README provides Docker Compose startup and the container declares the application command.
- `readme-missing-verification` label: `true` — The README contains no test or verification procedure.

### rizmyabdulla/Ripple

- Commit: `499496d2cca546b3b85b0aef68a0b3b5a334239a`
- Language bucket: Python
- Doctor project type: `cli`
- Doctor findings: `['broken-markdown-link', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The pyproject declares the ripple CLI and the README documents command-line usage.
- `readme-missing-verification` label: `false` — The README Quick checks section gives Ruff, mypy, pytest, and CLI help commands.

### ismayc/world-cup-viewer

- Commit: `0dd6deda9237379f1c5cc5e3046e2ab05553a15e`
- Language bucket: JavaScript
- Doctor project type: `web`
- Doctor findings: `['readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README and package scripts provide npm run dev as the launch command.
- `readme-missing-verification` label: `false` — The README Develop block explicitly documents npm test and npm run build, with additional schedule validation guidance.

### adobe/helix-markdown-support

- Commit: `ddcabc331a5960c60e599c4aef062652ac0a91c4`
- Language bucket: JavaScript
- Doctor project type: `library`
- Doctor findings: `['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a JavaScript library, so an application launcher is not expected.
- `readme-missing-verification` label: `false` — The README Development section explicitly documents npm test and npm run lint.

### fratei/creative-ware-hq

- Commit: `7b17d0798ec9f42609fd0c5b725aa3e72ee2a816`
- Language bucket: JavaScript
- Doctor project type: `auto`
- Doctor findings: `['broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This repository is a company operations and documentation workspace, not a runnable application requiring a launcher.
- `readme-missing-verification` label: `true` — The README has no concrete test or verification procedure.

### sseanliu/PaperClip

- Commit: `b8cbf3a2d66e34a8cf0261c5fd37428ee830c5c2`
- Language bucket: JavaScript
- Doctor project type: `static-web`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The Chrome extension README gives a complete Load unpacked installation and usage path, which is its supported entrypoint.
- `readme-missing-verification` label: `true` — The README has no explicit test or verification procedure.

### SnowCait/nostter-deck

- Commit: `c41981c0b9f65792b38044db3393028a3ef65bae`
- Language bucket: TypeScript
- Doctor project type: `web`
- Doctor findings: `['secret-risk-file', 'missing-health-check', 'missing-license', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The package scripts provide Vite and Tauri development commands.
- `readme-missing-verification` label: `true` — The README contains IDE setup only and does not document tests or verification commands.

### vaneui/vaneui

- Commit: `37808f6b5f2932dd465da3e4c53276286ee93e2b`
- Language bucket: TypeScript
- Doctor project type: `static-web`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-verification', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a React component library; it does not require an application launcher, and it also exposes a playground command.
- `readme-missing-verification` label: `false` — The README explicitly describes npm run playground as the local development and manual-testing path.

### obsidianlabs-io/obsidian-admin-vue

- Commit: `95e85e3f489ea23bbbe41b67093cfc2c9536edd6`
- Language bucket: TypeScript
- Doctor project type: `web`
- Doctor findings: `['secret-risk-file', 'secret-risk-file', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'generated-artifact-present', 'readme-missing-verification', 'missing-favicon', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The README provides pnpm dev and the package declares development commands.
- `readme-missing-verification` label: `false` — The README lists pnpm check, pnpm check:ci, unit, E2E, lint, and typecheck quality gates.

### omnidotdev/runa-app

- Commit: `cc8903b013a53ead4faa344dfc3910c72020716b`
- Language bucket: TypeScript
- Doctor project type: `web`
- Doctor findings: `['secret-risk-file', 'secret-risk-file', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README provides bun run dev and the package declares dev and start scripts.
- `readme-missing-verification` label: `true` — The README documents startup but no test or verification command.

### kuldeeprajput-dev/own-typing

- Commit: `e0e3e0ac6c513f56241e612290fa7e24606acd76`
- Language bucket: TypeScript
- Doctor project type: `web`
- Doctor findings: `['markdown-link-outside-root', 'markdown-link-outside-root', 'missing-health-check', 'readme-missing-usage', 'missing-config-example', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The README provides npm run dev and npm run start.
- `readme-missing-verification` label: `false` — The README lists build, lint, and typecheck commands as concrete quality checks.

### stolostron/volsync-addon-controller

- Commit: `d0924b2b2a0b108394ab499a8de6d146f5ed7098`
- Language bucket: Go
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README explicitly provides make run for local controller startup.
- `readme-missing-verification` label: `false` — The README contains a detailed testing workflow for the downstream operator catalog.

### openshift/lightspeed-agentic-operator

- Commit: `eb885d352da5889430c217735f0ae34ca726fee0`
- Language bucket: Go
- Doctor project type: `auto`
- Doctor findings: `['broken-markdown-link', 'missing-start-entrypoint', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README documents both the oc-agentic CLI entrypoint and make run for the operator.
- `readme-missing-verification` label: `false` — The README Testing section documents make test, make test-e2e, and targeted go test commands.

### toolsdotgo/sfm

- Commit: `c669389cf90f89085811535ba6bddf6fd2e64fa9`
- Language bucket: Go
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a Go CLI and the README clearly documents the sfm command and subcommands.
- `readme-missing-verification` label: `true` — The README provides usage examples but no test or verification procedure.

### bonnetn/minecraft-reverse-proxy

- Commit: `e205833b64dfecec33641c3aba166897117a0c34`
- Language bucket: Go
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README gives a complete docker run command and the Dockerfile declares the application command.
- `readme-missing-verification` label: `true` — The README does not document a test or verification command.

### scribe-org/Scribe-Server

- Commit: `bf1e6b7b06203e9c0b6a3c0b88ddd3b544d7bf3f`
- Language bucket: Go
- Doctor project type: `static-web`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-usage', 'readme-missing-verification', 'missing-favicon', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The README explicitly documents make build, make migrate, and make run for local startup.
- `readme-missing-verification` label: `true` — The README setup section does not document the available make test command or another verification procedure.

### Doughm/UCurses

- Commit: `5875a2e0e125abf4ea845e4ee950b8e3bd337a1b`
- Language bucket: C#
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a Unity framework imported into another project, not a standalone application requiring a repository launcher.
- `readme-missing-verification` label: `true` — The README explains installation and use but no test or verification workflow.

### thomhurst/Sourcy

- Commit: `ce105d55e4e09dd4eea1fe043e399a1a6457de8c`
- Language bucket: C#
- Doctor project type: `auto`
- Doctor findings: `['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'generated-artifact-present', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a set of .NET source-generator libraries, so no application launcher is expected.
- `readme-missing-verification` label: `true` — The README provides library usage but no concrete test or verification command.

### kellylford/QuickMail

- Commit: `1cf730a87312b867be6bb895f164061acd83e8b8`
- Language bucket: C#
- Doctor project type: `auto`
- Doctor findings: `['broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'markdown-link-outside-root', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The README documents build.bat run and dotnet run --project QuickMail.
- `readme-missing-verification` label: `false` — The README provides a build command and states that every push and pull request is built in GitHub Actions.

### Particular/NServiceBus.Persistence.AzureTable

- Commit: `27aa8c7ef17dd392a82a0c14ad55459e75a61225`
- Language bucket: C#
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'missing-config-example', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a persistence library, so a standalone application launcher is not expected.
- `readme-missing-verification` label: `false` — The README has a Running tests locally section with the required environment setup.

### credfeto/credfeto-cache-proxy

- Commit: `cb1d80a6268239f742b50dcd9065efe370b5e202`
- Language bucket: C#
- Doctor project type: `auto`
- Doctor findings: `['secret-risk-file', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'broken-markdown-link', 'missing-start-entrypoint', 'generated-artifact-present', 'markdown-link-outside-root', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The repository is a containerized application and its Dockerfile declares the executable ENTRYPOINT and health check.
- `readme-missing-verification` label: `true` — The README shows build-status badges but gives no reproducible local test or verification procedure.

### nuhkoca/Proje-Bulteni-Android-App

- Commit: `cf37bca75d8b41c41ace50f8debb4128f62fd346`
- Language bucket: Java
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `true` — This is an Android application, but the README gives no build, install, run, or Android Studio launch guidance; the generic Gradle wrapper alone is not a clear user entrypoint.
- `readme-missing-verification` label: `true` — The README contains only a description and license, with no verification procedure.

### apache/johnzon

- Commit: `1b58078bb9496219c17374f48657cdb231bb4632`
- Language bucket: Java
- Doctor project type: `auto`
- Doctor findings: `['missing-readme', 'missing-start-entrypoint']`
- `missing-start-entrypoint` label: `false` — This is a multi-module Java library project, so no standalone launcher is expected.
- `readme-missing-verification` label: `true` — There is no README, so no README verification guidance exists.

### DevOps26HN/AI-Mock-Interview-Platform

- Commit: `b4faca9a87de91680387b2890bec8cfee7dd3924`
- Language bucket: Java
- Doctor project type: `static-web`
- Doctor findings: `['secret-risk-file', 'broken-markdown-link', 'missing-license', 'missing-favicon', 'missing-security-doc', 'readme-missing-limitations']`
- `missing-start-entrypoint` label: `false` — The README provides Docker Compose startup and complete per-service local launch commands.
- `readme-missing-verification` label: `false` — The README contains a Testing Strategy section and additional subsystem testing guidance.

### KirtiPatiya25/DSA

- Commit: `25e7c1d7d87533e4b8b0d4d875e24ad714682e76`
- Language bucket: Java
- Doctor project type: `auto`
- Doctor findings: `['missing-start-entrypoint', 'missing-license', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — This is a collection of independent LeetCode solutions rather than one runnable application requiring a repository-level launcher.
- `readme-missing-verification` label: `true` — The README has no test or verification guidance.

### atolomei/odilon-server

- Commit: `1561962058417ff95e3a22eb976106020ddf6520`
- Language bucket: Java
- Doctor project type: `auto`
- Doctor findings: `['secret-risk-file', 'secret-risk-file', 'secret-risk-file', 'readme-missing-setup', 'readme-missing-usage', 'readme-missing-verification', 'missing-config-example', 'missing-security-doc', 'readme-missing-limitations', 'readme-missing-requirements']`
- `missing-start-entrypoint` label: `false` — The repository provides start-service.sh, odilon.bat, installers, and linked platform installation instructions.
- `readme-missing-verification` label: `true` — The README documents operation and examples but no test or verification procedure.
