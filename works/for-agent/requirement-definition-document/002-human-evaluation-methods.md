# Human Evaluation and Feedback Methods for Japanese Text Generation and Editing

Research and access date: 2026-10-16 (the user's client date). “Cited Findings” reports what the inspected primary sources say; “Inferences” are proposals and reasoning for this tool. No projected effects have been measured. Conference dates follow each paper's bibliographic record.

## What should be evaluated?

### Takeaway: What to Evaluate

Separate readability from meaning preservation. Also design reader-comprehension tests and editor checks comparing source and edited text as different tasks.

### Cited Findings: What to Evaluate

- Yamashita et al. (LREC 2026, 11–16 May 2026), “Evaluation of Document-Level Text Simplification in Japanese”: Five native Japanese speakers evaluated 1,128 pairs from 188 JADOS source texts and six system types. They separately rated preservation of essential information (0/1), preservation of main content (1–3), sentence-level simplicity (1–3), and document-level simplicity (1–3). The setup used sources up to 2,000 characters and simplification to about 150 characters for sixth-grade readers. This is direct prior work on Japanese at document level. — [Paper §3](https://aclanthology.org/2026.lrec-1.85.pdf), [bibliographic record](https://aclanthology.org/2026.lrec-1.85/)
- Agrawal & Carpuat (TACL 2024), “Do Text Simplification Systems Preserve Meaning?”: English paragraph-comprehension questions included “cannot be answered from the text” to detect meaning loss through deletion. Questions cover only some information; correct answers do not prove that all information was preserved. — [Paper §3](https://aclanthology.org/2024.tacl-1.24.pdf)
- Carrer et al. (HumEval 2024), “Towards Holistic Human Evaluation of Automatic Text Simplification”: Using 18 target readers and 18 controls for 12 texts in German, the study found a gap between subjective difficulty and actual comprehension. It also found no significant evidence that post-editing automatic simplifications was faster than manual simplification. — [Paper §§3–4](https://aclanthology.org/2024.humeval-1.7.pdf)

### Inferences: What to Evaluate

- This skill is for general meaning-preserving editing, not summaries for children. Do not adopt the 2026 paper's premises “shorter and simpler words are always better” or “preserving only the gist is enough.” Fix audience, purpose, and genre in each case beforehand; also check appropriate retention of technical terms and the author's voice.
- Proposed minimum evaluation axes: (1) preservation of original meaning, facts, and conditions; (2) comprehensibility for the target reader; (3) natural Japanese; and (4) adherence to the request and preservation of style. Give meaning changes a separate flag so they are not hidden in an overall average.
- Show the source and edited text to editors. Show readers in a comprehension test only one version of the same content. If the same person reads both versions before answering, information learned from the source can help comprehension of the edited version.
- A comprehension test can be a second phase later. Prepare 2–3 questions independently from the source, with human-verified answers and evidence locations. Include numbers, negation, conditions, causality, and referents. Also record whether the reader recognizes information absent from the text as unanswerable.

### Gaps: What to Evaluate

- The actual target audience, genres, and acceptable scope for omitting information in this skill are not yet defined. An impression of readability does not establish improved comprehension.
- There is no basis for directly generalizing evaluation criteria for child-oriented Wikipedia summaries to technical documents, email, or creative writing.

## How should pairwise comparison and ratings be combined?

### Takeaway: Pairwise Comparison and Ratings

Anonymous pairwise comparison is convenient for before/after revisions, but alone it does not reveal why one is better or whether either meets an absolute quality threshold. Combine preference with defect categories, locations, and proposed fixes.

### Cited Findings: Pairwise Comparison and Ratings

- van der Lee et al. (INLG 2019), “Best practices for the human evaluation of automatically generated text”: Recommends reporting evaluator characteristics, counts, and rationale; randomizing and counterbalancing order; using multiple evaluators; and reporting inter-rater agreement and interval estimates. It distinguishes exploratory analysis from confirmatory hypothesis testing. — [Paper Table 3, §4](https://aclanthology.org/W19-8643.pdf)
- Ethayarajh & Jurafsky (EMNLP 2022), “The Authenticity Gap in Human Evaluation”: Ranking systems by mean ratings assumes strong properties about human preferences and can reverse preferences under certain conditions. Their proposed SPA method is different from ordinary pairwise comparison; measuring the probability of superiority does not measure its magnitude. — [Paper §§3, 8, Limitations](https://aclanthology.org/2022.emnlp-main.406.pdf)

### Inferences: Pairwise Comparison and Ratings

- Minimum UI: show the source and anonymized A/B versions, hiding old/new generation-condition names, with “A / about the same / B / unable to judge” for each axis. Randomize A/B sides and item order, and save display order. Do not claim pairwise comparison is always better than ratings.
- For a single-output review, consider three levels with short anchors. Example for meaning preservation: “material change / minor concern / no issue within the reviewed scope.” Prefer category distributions and defect rates to a composite quality score averaging numerical ratings.
- Preference rationale: “where,” “what problem,” “why it matters,” and “how to fix it.” Save relevant source/output excerpts and character locations; proposed revisions are optional. Do not derive improvement rules from scores alone.
- Example: 「条件を満たす場合は申請できる」→「申請できる」. Even if shorter and natural, the evaluation must be able to fail meaning preservation because a condition was dropped. This is an illustrative artificial example, not a measured case.

### Gaps: Pairwise Comparison and Ratings

- The relative time and agreement of pairwise comparison versus three-level ratings for this Japanese skill have not been tested. A halo effect also remains: evaluators attracted to readability may miss meaning changes.

## How should small pilots and reliability be handled?

### Takeaway: Small Pilots and Reliability

Treat the first 24–40 documents as an exploratory study of operational feasibility and evaluation criteria. Do not confuse the number of rating forms with the number of independent texts.

### Cited Findings: Small Pilots and Reliability

- Card et al. (EMNLP 2020), “With Little Power Comes Great Responsibility”: Typical small-rater NLP studies may lack power to detect small differences. Plan power with explicit assumptions and simulation, accounting for both document-level and evaluator-level variation. — [Paper §§2, 5](https://aclanthology.org/2020.emnlp-main.745.pdf), [authors' public notebook](https://github.com/dallascard/NLP-power-analysis)
- Artstein & Poesio (Computational Linguistics 2008), “Inter-Coder Agreement for Computational Linguistics”: Agreement coefficients depend on assumptions and scales. Krippendorff's α can handle nominal and ordinal distances. Interpret a coefficient's number with care. — [Paper §3](https://aclanthology.org/J08-4004.pdf)

### Inferences: Small Pilots and Reliability

- Proposal: first select 24–40 documents without imbalance across major genres, lengths, and editing modes. Have 2–3 people independently evaluate each pair. Adjust criteria in 3–5 practice items and preserve pre-adjudication records for the main evaluation. These counts are operational starting points, not a guarantee of statistical adequacy.
- Compare revisions on the same set of sources; report wins, ties, and meaning-preservation failure rate by document ID. Retain each evaluator's vote. Do not treat 30 documents × 3 evaluators = 90 votes as 90 independent samples.
- If interval estimates are reported, a minimal option is a cluster bootstrap that resamples documents while keeping all evaluators' votes for each document together. This uncertainty is conditional on that evaluator group. Generalizing to evaluators in general requires a mixed model that also handles evaluator effects or two-way resampling.
- Disagreement is generally not a reason to delete a case. Report nominal-label α, ordinal-distance α for ordinal ratings, raw agreement, and label distribution; then investigate misunderstood definitions, reader differences, and legitimate preferences. With a single user, do not calculate agreement; label it “individual preference.”
- Approximate explanation: near a 50% win rate for independent binomial observations, the usual approximate 95% margin is ±1.96√(0.25/n). At n=30 it is about ±18 percentage points; at n=100, about ±10 points. This illustrates error only; it is neither an interval for a real test accounting for ties and evaluator/document correlation nor an expected effect size.

### Gaps: Small Pilots and Reliability

- The skill's baseline defect rate and genre- and evaluator-level variation are unknown, so the number of people and documents needed to verify effects is undetermined. A nonsignificant result in a small pilot does not prove “no effect.”

## How should automatic metrics connect to human feedback?

### Takeaway: Automatic Metrics and Human Feedback

Automatic metrics are supporting signals for people, not replacements for human conclusions. Saving feedback alone does not change the skill's behavior.

### Cited Findings: Automatic Metrics and Human Feedback

- Alva-Manchego et al. (Computational Linguistics 2021), “The (Un)Suitability of Automatic Evaluation Metrics for Text Simplification”: Correlation between metrics and human ratings varies with simplification quality, generation method, and reference set. Operation-level metrics such as SARI have limits for measuring overall simplicity. — [Paper §§4–6](https://aclanthology.org/2021.cl-4.28.pdf)
- However, in Agrawal & Carpuat's (2024) English paragraph-comprehension task, SARI correlated with system ranking better than the other comparison metrics. Because the target, granularity, and criteria differ from the 2021 study, it is inappropriate to conclude categorically that “SARI is worthless.” — [Paper §6, Table 3](https://aclanthology.org/2024.tacl-1.24.pdf)
- Yamashita et al. (2026) report that agreement with LLM ratings varies by model and axis, and that document-level simplicity tends to be rated lower for texts with higher kanji density and longer sentences. — [Paper §§4–5](https://aclanthology.org/2026.lrec-1.85.pdf)

### Inferences: Automatic Metrics and Human Feedback

- Improvement loop: human feedback → classify content/language/request-adherence issues → add representative failures as regression cases → have a person review rules or examples → anonymously compare old and new versions on unused documents. The first version does not need to insert feedback into the skill automatically.
- Link source and edited texts, human revisions, evidence for comments, generation model/conditions, skill version, and evaluation-criteria version. Aggregate by genre, reader, and mode.
- It is reasonable to hide automatic scores before human review. Whether this reduces score-induced bias should be checked in a pilot.

### Gaps: Automatic Metrics and Human Feedback

- The correspondence between automatic metrics and human judgments for this skill remains unknown. Even high text similarity can conceal changes to numbers, negation, agents, or conditions, so similarity cannot guarantee meaning preservation.

## What effects can be predicted?

### Takeaway: Predicted Effects

What can reasonably be expected is improved traceability of improvement points and better-informed next revision decisions. The current evidence cannot predict a percentage improvement in comprehension, time, or prose quality.

### Cited Findings: Predicted Effects

- The observed gap between readers' impressions and comprehension, and the absence of confirmed post-editing time savings, show that text that looks easier does not necessarily provide immediate practical benefit. — [Carrer et al. 2024](https://aclanthology.org/2024.humeval-1.7.pdf)
- There is little basis for assuming a small sample with few evaluators can reliably detect small differences between models. — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)

### Inferences: Predicted Effects

- Direct effect (reasonable expectation, unmeasured): Preserve which text and passage should be fixed and why, making recurring defects easier to classify and prioritize. This is easier to aggregate than free-text feedback alone, but the additional input burden may reduce continued participation.
- Indirect effect (conditional): Similar failures may decrease only if feedback is actually reflected in skill rules/examples and improvements are re-evaluated on unused documents. The human-evaluation tool itself does not improve generated text.
- Conditions that could defeat the prediction: generalizing one evaluator's preferences to all readers; optimizing one score across mixed genres; over-optimizing for brevity; or reusing improvement data as outcome-validation data.
- Separate goals from predictions. For example, “improve preference without worsening the rate of material meaning changes” and “complete one input quickly” are design goals, not numerical predictions of likely achievement. Decide after measurement.

### Gaps: Predicted Effects

- No experiment has been run on this tool, this skill, or its Japanese target users. There is no baseline for assigning a numerical improvement rate, time saving, or number of iterations. Do not present a provisional adoption criterion as an expected effect.
