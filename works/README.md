[日本語の案内](for-human/README.md)

# works/

Development documents record design intent and requirements, plus plans and checklists.
They are kept apart from the code.

## Folders

- `for-agent/`: the source of truth, written in English. Agents read it to understand or rebuild the work.
  - `checklist/`: work checklists, approved before implementation starts.
  - `requirement-definition-document/`: who needs what, constraints, and hardware/software choices.
  - `implementation-plan/`: implementation plans.
  - `design-document/`: design, behavior specs, and ADRs. Each numbered folder covers one component.
- `for-human/`: Japanese summaries made from `for-agent/`. When they differ, `for-agent/` wins.

`requirements-document/` is not created in this repository because it would be empty.

## Review Policy

both

## Language

The 15 documents migrated in Issue #223 are now in English, together with their indexes.
The indexes link to immutable Japanese originals from before the Issue #224 translation.
Japanese examples remain where their exact wording is evidence.
The historical `for-agent/checklist/001-works-migration.md` remains in Japanese.
It is outside the 15-document translation scope. `for-human/` contains Japanese summaries.
