Completed: Translation delivery and 44 link repairs; local checks and both review modes passed.
Next: Publish the follow-up PR, pass CI, merge, and verify the published GitHub references.
Open: Public verification and follow-up delivery; Issue #224 records the final state.

# Issue #224: Agent Documents Translation Plan

## Link Repair Follow-up

On 2026-11-28, the user explicitly requested link repair and public verification.
This completes the approved reference-checking scope after translation delivery.
The existing approval covers the unchanged models and preservation strategy.
The earlier decision to retain 44 local absolute links is superseded.

**Scope:** The 44 occurrences in three translated human-evaluation documents.
Use the recorded research commit `26ec2c1d04da69409702f49408311c80af79174b`
for historical repository citations, retaining the original line as a GitHub `#L` fragment.
Markdown line citations use `?plain=1` to open the source view.
Use relative links for the three current memo destinations.
The former `design.md:42` citation refers to historical `docs/design.md:42` at that commit.
Its old line number no longer locates the dependency guidance in the translated counterpart.
For installed supporting skills, find and verify public source identity before linking.
If no identical public snapshot exists, distinguish the public reference from the local snapshot.
Keep historical claims, examples, dates, numbers, runtime, and frozen evaluations unchanged.
Do not add dependencies or a permanent link-checking framework.

| Role                 | Model                                     | Effort             | Responsibility                                                   |
| -------------------- | ----------------------------------------- | ------------------ | ---------------------------------------------------------------- |
| Coordinator          | `gpt-6.1-sol`                             | `high`             | Source mapping, decisions, integration, Issue and delivery       |
| Repair worker        | `gpt-6-luna`                              | `medium`           | Apply the approved URL mapping to the three documents            |
| Independent verifier | `gpt-6-luna`                              | `medium`           | Read-only checks of occurrence coverage and public targets       |
| External reviewers   | Sonnet 5.5 and `gemini-4-hydrogen-medium` | `medium` requested | Separate overview/detail reviews, freshly randomized per request |

- [x] Record user authorization, scope, models, and completion conditions.
- [x] Review the repair plan in both modes and resolve findings.
- [x] Map and repair all 44 occurrences without changing historical evidence.
- [x] Check destination files and line fragments, and confirm zero local absolute Markdown links in the three documents.
- [x] Run the existing Markdown tools and inspect the scoped diff.
- [x] Complete independent verification and both final review modes.
- [ ] Publish and merge a scoped PR after required CI succeeds.
- [ ] Verify the merged GitHub pages, rendered links, and all unique replacement destinations over HTTP.
- [ ] Update Issue #224 with evidence, preserve unrelated work, and remove the merged branch and temporary worktree.

This is a reference-only documentation repair. TDD and an effectiveness experiment do not apply.
Use occurrence accounting, Git object/line checks, rendered GitHub HTML, and HTTP destination checks instead.
The requirements survey contains only the three supporting-skill links; it has no repository line citations.
Keep a pre-edit occurrence table under ignored `feedback/`, including the old and proposed destinations.
Check inline links, definitions, images, raw HTML, and local-path patterns.
When no public skill identity is verifiable, use explicit plain text instead of an invented link.
Plan reviews: Claude Code overview; Antigravity detail, both supplied-text reviews.
Adopted source-view line anchors, full occurrence accounting, and explicit public-snapshot limits.
The historical commit was confirmed through GitHub's API and is an ancestor of `origin/main`.
Formatting fixes are restricted to this change; textlint never runs with `--fix`.
The changed documents are not frozen evaluation inputs; preserve all `evals/` files byte-for-byte.
The staged allowlist includes these three documents and this existing checklist.
Final overview: Claude Code; final detail: Antigravity. Both returned PASS with explicit read-only limits.
Independent coverage and AST checks pass. Exact body comparisons permit only the URL mapping,
two public-counterpart disclaimers, and three link-label clarifications.
The original list structure is preserved. Prettier and markdownlint pass.
The Japanese textlint preset reports 192 advisory findings in English prose; no automatic prose fixes were applied.
The post-merge Issue checklist is authoritative for the remaining delivery steps.
The original translation plan and its historical execution log follow below.

**Goal:** Translate the 15 migrated documents. Preserve meaning and evaluation evidence.

**Spec:** [Issue #224](https://github.com/Mr-Kondo/japanese-readability-editor/issues/224), [works policy](../../README.md), and the shared `~/.claude/docs/works-document-structure.md`.

**Approach:** Keep the existing document paths. Preserve Japanese originals in Git.
Use baseline commit `07b5c6dd68f12b745d3a5a6e5b177c6c28696498` and link it from the indexes.
Keep `for-human/` for Japanese summaries. Avoid two complete document sets.

**Tools:** Existing Prettier and markdownlint-cli2. Existing textlint with its Japanese preset.
Apply `karpathy-guidelines` and `ponytail`. Use `superpowers:writing-plans` for this plan.
Use the applicable Superpowers execution skill after approval.

**Models:** The role table specifies each proposed model and reasoning effort.
User approval includes delegation. Translation uses the available economical `gpt-6-luna` preset.
The cheapest model across providers has not been established.
Coordinator settings: `gpt-6.1-sol` with `high` effort, rechecked in local config on 2026-11-28.
The user also confirmed the coordinator's `high` effort. No model setting was changed.
Verify worker models and execution when launched. A successful launch alone proves neither.

**Approval:** The user must approve this checklist and proposed model before translation starts. Any different model or preservation strategy requires approval.

## Role Assignments

The user explicitly requires divided responsibilities. Delegate after checklist and model approval.
Each translation worker owns five documents. The coordinator row records current settings.
Other model entries are planned assignments.
The review rows show the first plan review's random assignment, drawn on 2026-11-28.
Draw and record a fresh overview/detail assignment for each subsequent review request.

| Role              | Agent and model                         | Reasoning effort | Ownership                                                                        | Boundary                                                      |
| ----------------- | --------------------------------------- | ---------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Coordinator       | Codex: `gpt-6.1-sol`                    | `high`           | Checklist, indexes, provenance, integration, Issue, and PR                       | Resolves design questions and accepts evidence                |
| Translation A     | Codex worker A: `gpt-6-luna`            | `medium`         | The two requirements and three implementation plans                              | Edits only its five documents                                 |
| Translation B     | Codex worker B: `gpt-6-luna`            | `medium`         | Two knowledge-index ADRs, two human-review documents, and readability principles | Edits only its five documents                                 |
| Translation C     | Codex worker C: `gpt-6-luna`            | `medium`         | Installer ADR, three structure-rule ADRs, and fiction references                 | Edits only its five documents; waits for provenance recording |
| Verification      | Fresh Codex worker: `gpt-6-luna`        | `medium`         | Original comparison, links, literals, frozen files, and tool results             | Read-only; no self-review of translations                     |
| Overview reviewer | Antigravity: `gemini-4-hydrogen-medium` | `medium`         | Scope, preservation strategy, and unnecessary changes                            | Independent review                                            |
| Detail reviewer   | Claude Code: Sonnet 5.5                 | `medium`         | Translation fidelity and verification evidence                                   | Separate from overview reviewer                               |

Run the three translation workers concurrently only after plan reviews are resolved.
Start verification in a freed slot after translation finishes. Keep its context independent.
Tell every editing worker that others share the checkout. Do not revert others' edits.
Send uncertain meanings and frozen-evidence questions to the coordinator before editing.
Record actual agent identities and models when launched. Planned assignments are not execution evidence.
Workers run formatters only on their five owned files. Never run repository-wide fixes.
Run textlint without `--fix`. Preserve Japanese evidence even when a linter flags it.
Japanese-preset findings on English prose are advisory; record any retained findings.

Use consistent terms: 採用 = adopted; 見送り = not adopted; 却下 = rejected; 凍結 = frozen.
俯瞰 = overview; 詳細 = detail. Preserve modal strength: must, should, and may are distinct.
An ADR can have `accepted` status while its proposed runtime rule was not adopted.

Coordinator indexes, all under `works/for-agent/`:

- `requirement-definition-document/index.md`
- `implementation-plan/index.md`
- `design-document/index.md`
- `checklist/index.md`

Update `works/README.md`. Check inbound links across tracked Markdown, including `for-human/`.
Use a temporary GitHub-slug link check against both the baseline and the completed files.
Map renamed headings and update affected inbound fragments outside frozen files.
If a frozen file needs an old fragment, retain an explicit anchor in the translated target.
Report existing broken links separately. Do not relabel new broken links as baseline failures.
Extract and compare numbers and dates, then URLs and code.
Compare evidence spans. Inspect meaningful differences.
Check ADR metadata, headings, tables, and link counts against the Japanese baseline.
At completion, inspect the changed-path allowlist with `git diff --name-only`.
Include the separately requested `AGENTS.md` default correction; exclude unrelated checkout changes.

## Scope and Invariants

### Preflight Interfaces

| Task or interface | Producer and consumer                         | Finding and ruling                                                   |
| ----------------- | --------------------------------------------- | -------------------------------------------------------------------- |
| Translation A     | Five requirement/plan files                   | Read/translate/check scope agrees; no shared output file             |
| Translation B     | Five knowledge/human-review/principles files  | Read/translate/check scope agrees; no shared output file             |
| Translation C     | Five installer/structure/fiction files        | Read/translate/check scope agrees; provenance recorded before launch |
| Coordinator and A | Plan headings consumed by inbound links       | Coordinator updates fragments after A finishes                       |
| Coordinator and B | Design headings consumed by indexes and links | Coordinator integrates after B finishes                              |
| Coordinator and C | Provenance link consumed by OPQ ADRs          | Keep the provenance section anchor stable                            |
| Verification      | All completed files and pinned originals      | Fresh read-only context; no translation ownership                    |

### Invariants

- Translate the 15 documents below. Update supporting indexes and language notes in `works/`.
- Fix inbound links when translated headings change their fragments.
- Preserve decisions and evaluation results. Keep dates, quantities, and thresholds unchanged.
- Preserve uncertainty and source URLs. Keep identifiers and code unchanged.
- Preserve Japanese examples and test stimuli when their wording is evidence.
- Translate explanatory prose and headings. Historical proposals remain proposals.
- Rejected changes stay rejected. Unverified claims stay unverified.
- Preserve existing unrelated changes in the checkout. Use an isolated checkout for execution if available; do not reset, stash, or include other work.
- Leave `evals/` and its frozen files unchanged. Leave skill runtime and `VERSION` unchanged.
- Documentation-only delivery needs no skill release or Mac installation update.
- No new dependency, installer, evaluation run, or permanent validation script is needed.

## Target Documents

Paths are relative to `works/for-agent/`.

| Group           | Documents                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Requirements    | `requirement-definition-document/001-evaluation-tool-selection.md`, `002-human-evaluation-methods.md`                     |
| Plans           | `implementation-plan/001-next-improvement-plan.md`, `002-public-document-corpus.md`, `003-concretization-example-plan.md` |
| Knowledge index | `design-document/001-knowledge-index/pilot-plan-adr.md`, `conclude-pilot-adr.md`                                          |
| Installer       | `design-document/002-installer/remove-install-py-adr.md`                                                                  |
| Structure rules | `design-document/003-structure-rules/opq-analysis-adr.md`, `opq-reeval-adr.md`, `section-single-message-adr.md`           |
| Human review    | `design-document/004-human-review-tooling/design-survey-document.md`, `integration-document.md`                           |
| Readability     | `design-document/005-readability-principles/design-principles-document.md`                                                |
| Fiction         | `design-document/006-fiction-mode/design-references-document.md`                                                          |

## Frozen OPQ Evidence

The two current Japanese ADRs already differ from historical `adr_sha256` values.
Do not repair historical records or describe this as a translation regression.
The inspected `check_frozen()` implementations compare runner and helper digests.
The `prepare()` functions read old `adr/` paths. Leave both operations unchanged.

Before translation, add baseline provenance to the design index.
Record each ADR's commit and path. Include its SHA-256 and immutable Japanese Git link.
Distinguish these snapshots from earlier evaluation-time versions.
Keep evaluation records unchanged. Finding missing evaluation-time originals is outside this issue.

| Pre-translation Japanese ADR | SHA-256 at baseline                                                |
| ---------------------------- | ------------------------------------------------------------------ |
| `opq-analysis-adr.md`        | `4bfee46da6a3da7c3bf50597bf31bc67153d5c5c4645d8d1da04da5f15c3b283` |
| `opq-reeval-adr.md`          | `b68792fba170fe30878228152b0a16c03d73f26272f3a9fac30f8d88e9665aa3` |

Keep the runner-path limitation documented. Fix relative links in the English ADRs.
Retain exact Japanese originals through the pinned Git baseline.

## Checklist

- [x] Read Issue #224 and repository policy. Read migration records and shared instructions.
- [x] Inventory the 15 documents and existing changes. Check frozen ADR values and Markdown tools.
- [x] Obtain user approval of this plan, Japanese-original preservation, and translation model.
- [x] Record completion conditions and baseline limitations in Issue #224 before translation.
- [x] Get separate overview and detail reviews of the plan. Resolve findings before translation.
- [x] Document original retrieval and OPQ provenance before replacing the two ADR bodies.
- [x] Translate all 15 documents and review them against their pinned Japanese originals.
- [x] Translate supporting indexes and remove pending notes. Update `works/README.md` language notes.
- [x] Describe the actual scope. Do not claim the old migration checklist was translated.
- [x] Check changed and inbound Markdown links, including heading fragments. Record baseline failures separately and introduce no new broken links.
- [x] Run Prettier with `proseWrap: preserve`. Then run markdownlint-cli2 with the works configuration.
- [x] Run textlint on changed Markdown. Classify retained findings; do not apply automatic fixes.
- [x] Compare dates and numerical conditions with the baseline. Check URLs and code blocks.
- [x] Compare Japanese examples and ADR metadata. Check decision status and deliberate link changes.
- [x] Confirm frozen evaluation files are unchanged. Confirm runtime and version files are unchanged.
- [x] Run `git diff --check` without RTK.
- [x] Get overview and detail reviews of the translations. Resolve findings and record actual models.
- [ ] Record review scope and limits. Create a scoped documentation PR and pass applicable CI.
- [ ] Merge within authorized permissions. Keep the Issue open while required delivery is pending.
- [ ] After verified merge, remove this task's merged branches and temporary checkout.
- [ ] Clean up disposable artifacts. Report retained evidence and blocked cleanup.
- [ ] Recheck every Issue acceptance condition and close only when verified.

## Review Focus and Verification Limits

Check accepted ADR status versus rejected proposals. Preserve normative strength and uncertainty.
Review Japanese evidence examples and adoption thresholds. Check translated heading fragments.
Check frozen-evidence provenance separately from English readability.

This is a documentation translation. TDD Red/Green and effectiveness experiments do not apply.
Compare source meaning and frozen files. Check links and formatting. Obtain independent reviews.
Run applicable CI checks. Do not add an evaluation campaign.

## Work Log

- 2026-11-28: All 15 translations were compared with pinned Japanese originals.
  Final random assignment: Claude Code overview; Antigravity detail. Both completed with PASS and limits.
  Resolved models were `claude-sonnet-5-5` and `gemini-4-hydrogen-medium`; effort was requested as `medium`.
  Claude read the indexes and policy. Antigravity read every original and translation.
  Updated checklist status and recorded actual reviewer evidence after Claude's minor notes.
  The coordinator verified exact fences, source URLs, ADR metadata, table rows, and inline literals.
  Some verifier findings quoted lossy command summaries. Exact-file checks disproved them; they were withdrawn.
  Link check: 151 affected links, zero new failures, 44 retained baseline failures.
  Prettier passed for the 22 translated/supporting files; five fragment-only public pages retain baseline formatting.
  Markdownlint passed for all 27 files. Japanese-preset textlint retained 782 advisory findings without fixes.
  Frozen evaluation, runtime, and version files are unchanged. No release or Mac update is required.
  Delivery checkboxes remain pending at this commit; Issue #224 records their eventual completion.
- 2026-11-28: Launched `/root/translation_a`, `/root/translation_b`, and `/root/translation_c`.
  Each spawn specifies the approved `gpt-6-luna` model and `medium` effort with independent context.
  Skill and kokugo validators passed. Full unit suite passed: 963 tests, 13 skipped.
  Detailed logs and the temporary link checker are retained under ignored `feedback/`.
- 2026-11-28: Plan overview: Antigravity `gemini-4-hydrogen-medium`, requested effort `medium`.
  Its first attempt read both plan files, then a command permission denial prevented a verdict.
  A second review used only supplied plan text and returned PASS with three suggestions.
  Detail: Claude Code resolved `claude-sonnet-5-5`, requested effort `medium`; read both files.
  Accepted scoped formatting and no textlint fixes.
  Added explicit indexes, shared terms, and scripted checks.
  Added frozen-fragment anchor preservation and moved provenance ahead of translation.
  Scanned all evaluation run hashes: no current target digest matches a frozen hash field.
  Known historical OPQ ADR hashes already mismatch the current originals.
  Other frozen plans refer to `evals/` documents outside the 15 targets.
  No frozen Markdown fragment into a target was found. Verify again after translation.
  Retained the approved verifier model; external reviewers provide different-model review.
  Do not add a post-translation digest to its own ADR. Final digests belong in verification evidence.
- 2026-11-28: User approved this checklist and requested proofreading.
  Execute Issue #224 with the approved roles. Check meaning and numerical conditions.
  Check references and evidence preservation.
  Created isolated branch `docs/issue-224-agent-translation` to preserve unrelated checkout changes.
  Plan scan: translation A/B/C own disjoint files. Index integration consumes their headings.
  Verification consumes completed translations and the immutable baseline. No worker edits indexes or evaluation files.
  Stage 2 TDD and stage 4 effectiveness reviews do not apply to translation-only documentation.
- 2026-11-28: Corrected coordinator effort from `medium` to `high` after the user's correction.
  Rechecked local Codex configuration. This corrects the document; it does not change settings.
- 2026-11-28: Added explicit models and effort for all roles after the user's correction.
  First plan review draw: Antigravity overview; Claude Code detail. Neither has been launched.
  Coordinator model is a planned project assignment; the current runtime remains unverified.
- 2026-11-28: User required role separation. Added explicit file ownership and independent verification.
  Checklist and model approval remain pending. No worker has been launched.
- 2026-11-28: Planning only. The connected GitHub tool retrieved the Issue after `gh` could not connect.
  Context-mode execution was rejected by the approval policy. Local read-only commands were used.
  No translation or review request has started. No model was delegated and the Issue was not changed.
  Existing user changes remain untouched.
- 2026-11-28: Plan and checklist index passed Prettier and markdownlint-cli2.
  Textlint findings were addressed by shortening English sentences. Final checks follow.
