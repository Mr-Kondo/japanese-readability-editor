# Signed and clock number comparison

## Decision

Adopt the scoped comparison fix for v0.25.2, with the lexical limits below.
This record concerns Issue #219.
No upstream implementation was read or copied.

## Fixed comparison

The user approved the checklist on 2026-11-29.
The same 58 locally authored cases are used for the old and candidate implementations.
They were authored independently of upstream implementation, by the implementer.
Expectations were frozen before candidate execution.
The fixture is `tests/fixtures/signed-clock-numbers.json`.

| Category               | Cases | Old implementation                 | Candidate result                |
| ---------------------- | ----: | ---------------------------------- | ------------------------------- |
| Meaning changes        |    14 | 3 flagged; 1 exact expected result | 14 flagged; all 14 exact        |
| Equivalent expressions |    20 | 10 false alarms                    | Zero false alarms; all 20 exact |
| Controls               |    24 | Zero false alarms                  | Zero false alarms; all 24 exact |

An exact result matches both complete missing and added lists.
A flagged case has at least one missing or added item.
For example, the old implementation flags a seconds change but also flags equivalent hour notation.
Detection alone therefore does not establish correct extraction.

The old runtime source SHA-256 is `1fb00e93da2d43365db007362d8ebce9b4fd54c8a020e48648ed87319213df07`.
The fixture SHA-256 is `336580d14c0bcb703fad5af29e302f0d53b78596b60176c920fc7d62b4f0d3bf`.
The base commit is `460b8bd8245dd44d7a8e596645890c4887d00a2c`.
Final candidate SHA-256:
`7668e0d1e0518270980b5ee49ae3182a584965c2bb3149325d80c691927c5c83`.
The fixture, 78-pair screen and 208-document screen were rerun against this candidate.

## Boundaries

- Adjacent `▲` and `△` mean negative. ASCII and Unicode minus notation compare equally.
- Only adjacent valid `午前` or `午後` hours ending in `時` are clock qualifiers.
- `午前0時` and `午前12時` mean midnight; `午後0時` and `午後12時` mean noon.
- Durations ending in `時間`, invalid qualified hours and separated qualifiers keep prior behavior.
- Dates, numeric ranges, list markers, protected Markdown code and URLs remain controls.
- Existing percent and counter normalization stays in effect.
- Valid clock hours normalize padding; other padded numbers and durations keep prior behavior.
- Minus signs directly after extracted numeric items, or separated only by whitespace, remain range separators.
  Kanji and katakana labels also block minus interpretation, preserving unrecognized-counter ranges.
- Displayed items retain normalized source notation and source line numbers.

## Validation and reviews

The frozen tests produced 24 assertion failures in 63 comparison tests.
Four optional-analyzer tests were skipped.
The failures include missing sign/period changes and false alarms on equivalent clocks.
Red logs, frozen source, hashes and review responses are private under `feedback/issue-219/`.
Planning and Red-test reviews preceded the runtime change.
Three supplementary methods were added after the 63-test frozen Red run.
Audit follow-ups added nine more methods; the final comparison suite has 75 tests.
Implementation and effect reviews follow validation.

Before candidate execution, 78 existing OPQ3 rewrite pairs were frozen as a regression screen.
Six pairs contain target notation; 23 already have numeric alarms under the old implementation.
The screen rejects newly introduced alarms unless independently confirmed as scoped true changes.
Another screen freezes 208 tracked Markdown documents under `docs`, `evals` and the skill.
It rejects unexplained extraction changes or extra or lost numeric items.
Every changed item must be an adjacent sign or valid clock normalization.

The candidate changed no numeric alarms in the 78 existing rewrite pairs.
URL alarms also remained unchanged on those same pairs.
The 208-document screen found 29 extraction differences.
All 29 match the predeclared sign or clock patterns; no numeric items were added or lost.
The screen compares ordered occurrences, including repeated values on the same source line.
The private adjudication record contains each before/after item and source location.
Context inspection found 19 negative values and 10 qualified clock hours among those 29 items.
An earlier 31st change incorrectly treated a masked phone-number separator as a minus sign.
A failing regression test reproduced that case.
The fix excludes asterisks before minus signs.
These are extraction checks.
The ratio of changed items does not estimate a real-world false-alarm rate.

The first candidate exposed a protected-URL failure for non-ASCII paths.
The fix masks extended URL paths only for number extraction.
It records the complete extended path in the existing URL-report fields.
Thus `https://example.com/第3版` to `https://example.com/第4版` raises a URL-change alarm.
The failing test for that URL report was retained before the correction.
Term and role extraction retain their old URL masking.
The same 208 frozen documents show no changes in terms, roles or URL extraction.
The advisor also reproduced a URL mask swallowing a following Markdown table cell.
A failing test was retained before treating `|` as a path delimiter.
Another failing test covered following numbers after Markdown emphasis.
Matched surrounding Markdown emphasis delimits the path; internal path characters remain intact.
Underscore closers cannot split an internal word.
Matched asterisk emphasis around negative numbers retains the sign and identifier protection.
A further failing test pinned the boundary between URLs and subsequent prose numbers.
The audit added full-width exclamation marks, question marks, colons and semicolons to this check.
Both failures were retained before correction; the final focused tests pass.

## Limits

These are synthetic regression cases, also used by the focused unittest.
They provide no independent held-out estimate of accuracy.
The existing-pair screen is historical model output, not live user evidence.
They do not measure real-world frequency, generalization or reader benefit.
Separated qualifiers and triangle signs remain outside this change.
An adjacent triangle used as a bullet can still be interpreted as a negative sign.
Inherited qualifiers (`午後1時から5時`) are not propagated to later hours.
Word-form negatives (`マイナス3.2%`) are not equated with triangle signs.
Minus signs after kanji or katakana labels are not recognized as negative signs.
Whitespace-separated numeric items retain unsigned range interpretation, even for a list of signed values.
Identifiers masked with symbols other than the tested ASCII asterisk can still be read as negative values.
Supplementary failing tests preserved `3名-5名`, `第3章-2節` and `3人 -5人` without new alarms.
Supplementary tests pin these limits and padding differences for durations and counts.
These limits are outside the 20 frozen equivalent cases.
Zero alarms in that group is a bounded result.
This remains a lexical comparison aid; it does not prove that the complete text preserves meaning.
Bare clock hours are unqualified morning values for equality: `3時` equals `午前3時`.
Adding `午前` to a bare hour therefore produces no alarm, even if it changes the intended meaning.
Adding `午後` to `3時` therefore raises an alarm, even if the writer intended clarification.
A bare non-ASCII URL path ends at whitespace or the enumerated punctuation delimiters.
Unpunctuated prose attached to that URL is ambiguous and is masked as part of the path.
Editing that attached prose can therefore also raise a URL-change alarm on an unchanged URL.
For example, `https://example.com/で午後5時に配信` hides the trailing clock.
Separate prose from a URL with whitespace or punctuation before relying on number comparison.
This local path-mask extension is an explicit compatibility limit, not complete URL parsing.
Unlisted punctuation, including curly quotes and full-width comma or period, can remain inside the path.
Optional Sudachi tests were skipped; the extraction evidence uses the regex analyzer.

## References

- [Issue #219](https://github.com/Mr-Kondo/japanese-readability-editor/issues/219)
- [Approved checklist](../works/for-agent/checklist/005-signed-clock-number-evaluation.md)
