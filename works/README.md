[日本語の案内](for-human/README.md)

# works/

Development documents: design intent, requirements, plans, and checklists, kept apart from the code.

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

All documents in this repository are still in Japanese. English versions are pending translation.
