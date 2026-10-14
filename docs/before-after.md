# Before/After evidence

## Current status: 5 verified public-history cases

These cases compare immutable commits from public third-party repositories. Repo Launch Doctor did not modify those repositories. Each pair was found from a public commit that added a launcher or start script, then independently checked at both the parent SHA and the changed SHA.

A case is included only when both SHAs fetch successfully, check out exactly, produce complete Doctor scans, and the source diff directly explains why `missing-start-entrypoint` changes from present to absent.

| Repository | Before SHA | After SHA | Concrete public change | Reproduced result |
|---|---|---|---|---|
| `Ckala62rus/go-architecture-v2` | `2fc3164e0d8cce622d5f9dc30141df61e1de6c61` | `df7c7b4f0aece8aaa4a2829f2a905419d023663c` | Added root `start.bat` for the Docker Compose application. | Finding present before and absent after. |
| `cbogdan97/automation_test` | `dab37fe8a9243a3436ba14381329db34e147aa26` | `4f89826f29b32764df58255cb77f6f70cf17ca62` | Added root `start.bat` invoking `npm run cy:open`. | Finding present before and absent after. |
| `FredrikBWinLas/TicTacToeYellowBelt` | `c343ecc4bf0055e02941f025d64eeefcdf17563d` | `8b895bdfe1a2e9c75818dfa3ca7b8a293df3a24f` | Added root `run.bat` with the `dotnet run` command. | Finding present before and absent after. |
| `Jrock474/Back-End-Project` | `1c458ffb806ffd576c35f9f5b0c03f58e4da203d` | `19a57b0de1a1bf1c1898b6a986e27e0fa6fe19fe` | Added root `package.json` script `start: nodemon scripts.js`. | Finding present before and absent after. |
| `kierajreed/random-recipe-wiki` | `c55ec709a2d8c62e38f6d892b9148387c0caf050` | `a1a64d1eeeaf93e3a46469d3850bdaaa93b5c5e0` | Replaced the placeholder package script with `start: node index.js`. | Finding present before and absent after. |

The corresponding fixed-SHA reports are published under `benchmarks/results/targets/`; the same ten commits are part of the formal 20-target benchmark.

## Rejected candidates

A commit message alone is not evidence. Candidates were rejected when either scan was incomplete, the before commit did not actually trigger the finding, or the added command was nested in a subproject and therefore did not establish a root repository launcher. Rejected examples are recorded in `benchmarks/label-history.md`.

## Scope

These five cases demonstrate the rule on this fixed evidence set. They do not prove that every repository layout is supported, that the launcher works at runtime, or that all missing launch instructions will be detected. Repo Launch Doctor remains a static inspection tool.
