# Project Koios maintenance scope

This repository is the Project Koios fork of SNAKES, the Net Algebra Kit for Editors and Simulators.

## Upstream baseline

- Active upstream repository: <https://codeberg.org/fpom/snakes>
- Historical GitHub repository: <https://github.com/fpom/snakes>
- Baseline commit: `2291c6e627c85fc2932a83cc2eb9b712495b5d7a`
- Baseline tree: `de44619776b1aba3b1cd068c6887db01b7116fc6`
- Baseline version: `0.9.33`

The upstream copyright and LGPL license remain applicable. Local changes must not be represented as upstream changes.

## Initial maintenance policy

The fork initially preserves SNAKES semantics and the `snakes` import namespace. Changes are introduced incrementally when exercised Project Koios use cases expose a concrete compatibility defect or missing boundary.

The first maintained baseline targets Python 3.14 core colored-net behavior: typed tokens, enabled-mode discovery, firing, independent branches, and joins.

SNAKES expressions, declarations, and PNML deserialization are trusted-code facilities. Project Koios integrations must not evaluate untrusted expressions or deserialize untrusted PNML or pickle payloads.

Calculator execution, durable observations, retries, audit, and replay remain outside the SNAKES firing kernel.

## Revision notes

Every Project Koios commit carries a concise `Revision note:` paragraph in its commit message body. `REVISION_NOTES.md` records the initial commits that predate this convention without rewriting published history.

Edits to inherited upstream source carry an adjacent `Project Koios:` comment explaining the compatibility or behavioral reason. New Project Koios code documents its purpose and important semantic boundaries with docstrings or comments; comments are not repeated on self-explanatory mechanical lines.
