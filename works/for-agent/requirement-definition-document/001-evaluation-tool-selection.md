# Survey of Libraries, Operating Models, and Supporting Skills for Human Evaluation

Research date: 2026-10-16. Desk research prioritizing official documentation and repositories. Installation, launch, and Japanese-language interaction were not tested. “Inferences” below are design judgments for this project, not official product recommendations.

## Which tools fit this project?

### Takeaway: Tool Fit

For a small evaluation focused on blind A/B choice, tie, unable to judge, rationale, and JSON storage, local HTML without external dependencies is the leading option. If many evaluators, ongoing assignment, or precise span annotation are needed from the start, try Label Studio first. Gradio and Streamlit are strong choices for a short Python prototype, but they do not replace experiment design or safe data storage.

### Cited Findings: Tool Fit

| Candidate                           | Verified capabilities and operation                                                                                                                                                                                                                                                                                                                | Project-specific work still needed                                                                                                                                                              |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Static HTML + standard browser APIs | FileReader can read a local file selected by the user. Blob URL creation is a standard API. These provide a basis for reading a local file and saving results as a file. [FileReader](https://developer.mozilla.org/en-US/docs/Web/API/FileReader), [createObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static) | Implement the evaluation form, left/right assignment, input validation, resume, aggregation, and explicit save confirmation.                                                                    |
| Gradio                              | A Python UI library. Flagging can record inputs and outputs to a CSV on the machine running the app. The current CSVLogger description accounts for concurrent processing. [Flagging](https://gradio.app/main/docs/gradio/flagging)                                                                                                                | Configure candidate sides, tie, and unable-to-judge in a custom form. The Flag button alone does not provide evaluator IDs, resume, duplicate-response prevention, or assignment management.    |
| Streamlit                           | Provides selection, form submission, text input, evaluation buttons, and result download through `download_button`. [Widgets](https://docs.streamlit.io/develop/api-reference/widgets), [Download](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)                                                                     | Build the placement of the source and candidates, evaluation protocol, persistent storage, and left/right correspondence in the app.                                                            |
| Label Studio                        | The Pairwise tag can compare two texts. Choices allows arbitrary options, and Labels annotates text spans. [Pairwise](https://labelstud.io/tags/pairwise.html), [Choices](https://labelstud.io/tags/choices.html), [Labels](https://labelstud.io/tags/labels.html)                                                                                 | Do not infer tie support from the Pairwise specification alone. Explicitly represent A / B / tie / unable to judge with Choices. Remove candidate names and assign sides while preparing input. |
| Argilla                             | LabelQuestion, RatingQuestion, TextQuestion, RankingQuestion, and SpanQuestion can be combined. SpanQuestion supports a setting that permits overlapping spans. [Questions](https://docs.argilla.io/latest/reference/argilla/settings/questions/)                                                                                                  | Tie support through Ranking alone was not verified. Representing A / B / tie / unable to judge as a LabelQuestion is the reliable option.                                                       |

- Label Studio supports JSON / CSV export. Its raw JSON retains source data, annotations, evaluator, elapsed time, and other fields. By default, unannotated tasks are omitted, so compare against the original ledger when calculating missingness. [Export](https://labelstud.io/guide/export)
- Argilla stores settings and responses on local disk and can export records as dictionaries or lists. Publishing to the Hub is not required. [Import / Export](https://docs.argilla.io/latest/how_to_guides/import_export/)
- Gradio’s current `main` pyproject lists Python >=3.10 and Apache-2.0. This may not match the Python compatibility range of the project itself. [pyproject](https://github.com/gradio-app/gradio/blob/main/pyproject.toml)
- Apache-2.0 was confirmed in the official repositories for Streamlit, Label Studio, and Argilla. This checks the main projects’ licenses, not all dependencies or commercial-edition terms. [Streamlit LICENSE](https://github.com/streamlit/streamlit/blob/develop/LICENSE), [Label Studio LICENSE](https://github.com/HumanSignal/label-studio/blob/develop/LICENSE), [Argilla repository](https://github.com/argilla-io/argilla)
- **Argilla’s official README says its original authors have moved to another project, are not adding new features, will continue necessary bug fixes and patches, and are seeking maintainers.** Do not select it as a foundation for ongoing expansion based only on its past feature list. [Argilla README](https://github.com/argilla-io/argilla)

### Inferences: Tool Fit

- Recommended order: static HTML for solo or small-group work; Label Studio where a shared operating base already exists; reuse Gradio / Streamlit if already adopted; consider Argilla for continuity if it is already in use. Evaluator count is not the only branching condition; assignment, access control, and span selection matter too.
- The minimum version need not require precise mouse-based span annotation. Record “candidate A / sentence number / quoted problem text / problem type / desired change.” Adopt Labels or a similar tool when research requires exact character offsets. Custom span selection increases verification burden for Japanese, emoji, and selections across line breaks.
- Gradio Flagging can support collection, but a simple “useful / not useful” flag does not capture why meaning changed or where. Do not use the built-in Flag unchanged as the final form.
- Building authentication, a database, a public server, and real-time collaboration into the first static HTML version has a high opportunity cost. Until need is demonstrated, each evaluator can save a JSON file for later integration.

### Gaps: Tool Fit

- Japanese IME, spans across paragraphs, math and Markdown rendering, keyboard-only operation, concurrent saves, and browser differences have not been tested for any tool.
- It was not confirmed that Label Studio Enterprise’s blind-review and assignment features are available in Community Edition. Do not treat overlap / blind review in official marketing articles as OSS functionality.
- Current stable versions, all dependency licenses, vulnerabilities, and future maintenance SLAs have not been audited. Some Gradio official guides failed to redirect to the Markdown API when retrieved, so current defaults for public settings are not asserted.

## How should local operation and data storage work?

### Takeaway: Local Operation and Storage

Running locally and making no external connections are different claims. The first version should send no text to an API, use no external CDN, and provide explicit JSON save and reload.

### Cited Findings: Local Operation and Storage

- Streamlit says it collects usage statistics but does not view or store information included in the app. `browser.gatherUsageStats = false` disables statistics reporting. [Configuration / Telemetry](https://docs.streamlit.io/develop/concepts/configuration/options)
- Argilla’s Docker deployment uses a local server, database, and Elasticsearch configuration. This differs from installing only its Python SDK. [Docker deployment](https://docs.argilla.io/latest/getting_started/how-to-deploy-argilla-with-docker/)
- Argilla sends anonymous usage information; `HF_HUB_DISABLE_TELEMETRY=1` disables it. Its documentation says it does not collect records or dataset names. [Telemetry](https://docs.argilla.io/latest/reference/argilla-server/telemetry/)
- Gradio’s official 4.44.1 documentation describes `analytics_enabled` / `GRADIO_ANALYTICS_ENABLED` controls. This is a past-version specification; verify the API of the selected version at implementation time. [Versioned Interface docs](https://gradio.app/4.44.1/docs/gradio/interface)
- Label Studio can be installed locally and stores annotations in SQLite and other storage. [Install](https://labelstud.io/guide/install.html), [Export storage](https://labelstud.io/guide/export.html)
- The behavior of localStorage for `file:` URLs is not guaranteed by the specification. In private browsing, data is deleted when the last private tab is closed. [MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- Using textContent prevents a string from being interpreted as HTML. This is a basic choice when evaluation text is inserted into the UI. [MDN textContent](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent)

### Inferences: Local Operation and Storage

- Do not make localStorage the only store in the static version. Allow interim results to be exported and imported as JSON, and show when there are unsaved changes. If real-world use requires automatic persistence, move storage to a local server while keeping the same JSON format.
- Remove names, skill versions, and model names that might reveal candidate identity from the evaluator’s screen. Rejoin them through a mapping table during post-collection integration. Hiding the names in the display is not strict blinding if the distributed JSON contains the mapping. The author may also remember the original text, which remains a limit on blinding.
- Even without an added dependency such as JSON Schema, the local version can explicitly validate required keys, types, duplicate IDs, text hashes, and known choices. Include the evaluation protocol version and source task ID in output so results can be traced to the input text and skill version.

### Gaps: Local Operation and Storage

- The execution machine’s installation state, startup without network access, traffic capture, and recovery from file-save failure were not tested. Official telemetry descriptions alone do not demonstrate complete network isolation.

## How should aggregation libraries and skills divide responsibilities?

### Takeaway

Keep the evaluation UI separate from statistical processing. Initially aggregate counts, wins/losses, tie rate, missingness, and meaning-change counts. Once human data exists, use SciPy / statsmodels as optional dependencies in the analysis environment rather than required dependencies of the skill.

### Cited Findings

- SciPy’s `stats.bootstrap` supports confidence intervals, paired data, resampling counts, and random-state control. [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
- statsmodels’ `cohens_kappa` accepts a contingency table for two evaluators and supports unweighted, linear-weighted, and quadratic-weighted kappa. [Cohen kappa](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.cohens_kappa.html)
- statsmodels also provides `fleiss_kappa` for categorical ratings by multiple evaluators. [Fleiss kappa](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html)
- The session-provided hugging-face:huggingface-gradio skill supports Python UI components, Blocks, and event wiring. [Local SKILL.md](/Users/masatomiwada/.codex/plugins/cache/openai-curated-remote/hugging-face/1.0.0/skills/gradio/SKILL.md)
- The provided data:statistical-analysis skill covers effect sizes, confidence intervals, small samples, and multiple-comparison cautions. [Local SKILL.md](/Users/masatomiwada/.codex/plugins/cache/claude-cowork/data/1.0.0/skills/statistical-analysis/SKILL.md)
- The provided skill-creator says to improve skills using actual use and demonstrated failures, and that passing a validation script does not prove decision quality. [Local SKILL.md](/Users/masatomiwada/.codex/skills/.system/skill-creator/SKILL.md)

### Inferences

- The data unit here is the source text. Multiple votes on the same source text must not be treated as independent source texts. Resample at the source-text level while retaining all evaluators for each source. `paired=True` helps preserve pairing, but does not automatically resolve crossed evaluator/source structure.
- Gradio skills can support UI usability, statistical skills can support aggregation choices, and skill-creator can support carrying evaluated failures into existing prompts or examples. None of these skills guarantees Japanese human-evaluation validity or replaces evaluators.
- Use feedback to identify candidate improvements by failure type, then compare before and after revisions on separate, unused source texts. Do not automatically train on the feedback or immediately generalize a small number of preferences to every mode.
- A reasonable expected benefit is better traceability and identification of recurring weaknesses through structured records. There is no project-specific evidence showing that adding a UI or library will improve prose quality or reduce rework by a particular percentage.

### Gaps

- Whether SciPy / statsmodels are installed, compatibility with the selected environment, suitability of kappa under missingness or category imbalance, and a specific cluster-bootstrap implementation are unverified. No numerical analysis was run.
- “Using a library” or “installing a skill” is distinct from demonstrating actual invocation, storage, or quality improvement on the host. The referenced skills were inspected as research subjects; no tool was built and no skill was revised.
