# Output and validation contract

## Human-readable artifact

Keep the current version on top, with version, actual status, source/approval state and exact spoken SHA-256 where useful. Do not manufacture an approval to fill a field.

```text
# Campaign title

Current: v1 | WORK IN PROGRESS / writing checks complete
Wording approval: not received / exact verified version and evidence
Production: pending / separately reviewed exact cut

## Spoken script (v1)
Only words meant to be spoken.

## Full review — v1
### G1–G30
### H1–H4
### Every-sentence ladder
### Audience states
### G26 desire and contrast
### G25 Humanizer — all 33
### Truth sheet
### Production notes and outstanding checks

## Superseded — v0 — actual date and reason
Actual older status/approval/rejection and genuine feedback.
Exact old script and its historical review.
```

Each review table has ID, result, exact quote/asset/source and reason/missing evidence. N/A has its topic-specific reason and is not counted as PASS. Include four truth-sheet buckets and detailed claim/source rows. Below Humanizer record factual/locked parity and explicit rehearsal method, measured timing, actual evidence and pending human production checks. Include G21's closest-match/control/freshness/transfer analysis and G26's five generalized subquestions. Do not put this audit, a URL, prompts or editing cues in the spoken body.

Version-specific approval and independent review are actual records, not agent-authored checkboxes. Preserve old copies and genuine feedback. A changed script needs a new review and cannot inherit approval. Script-stage writing/evidence completeness does not mean final production, human delivery, CTA distribution or permission to publish passed.

## Machine-readable packet

Copy [packet-template.json](packet-template.json) into your **private work directory**, fill it from actual review evidence, and keep its source paths relative to a private artifact root. The provided template is deliberately incomplete/BLOCKED, not a passing example. Never commit a client packet to the skill repository.

Run Python 3.10+ from the skill directory, or prefix `scripts/validate.py` with its absolute location:

```bash
python3 scripts/validate.py --packet /absolute/path/review.json --root /absolute/path/artifacts
python3 scripts/validate.py --packet /absolute/path/review.json --root /absolute/path/artifacts --spoken-file /absolute/path/Script.md
```

The checker is read-only, standard-library-only and makes no network calls. Exits: 0 when a full packet has no recorded unresolved writing/integrity checks; 1 for unresolved/failing checks; 2 for unreadable/invalid CLI input. Standalone `--spoken-file` can return 0 for its limited mechanical scan while `writing_ready` remains false. A full packet's `writing_ready: true` means the **reported evidence protocol is complete and mechanically consistent**, not that a machine established persuasive quality, source truth or authentic approval.

### Fields

| Field | Meaning |
|---|---|
| `version` | Packet schema version, exactly `v1`. The human script revision is recorded in the artifact/version notes. |
| `spoken_script` | Exact complete current narration; not a summary. Optional `spoken_sha256` must match its exact UTF-8 bytes if supplied; the checker emits that hash. |
| `mode` | `draft`, `revision` or `audit`. Audit additionally needs `locked_script` with the exact unchanged input. |
| `profile` | Explicit `hook_max_words` integer, `first_person_allowed` boolean, `jargon_terms` literal string list, `allow_dash_style` boolean. Optional `banned_openers` literal prefixes; optional `specialist_audience` declares intentional narrowly targeted maturity coverage; optional `allow_curly_quotes` boolean retains an expressly chosen typography style. Defaults are viewer-first, 18-word hook budget, no dash-style narration, four STAY including beginners. Document user authority for customizations in the human review. |
| `gates` | Exactly G1–G30 once each. |
| `hook_checks` | Exactly H1–H4 once each. |
| `desire_checks` | Exactly D1–D7 once each. |
| `humanizer` | Exactly integer IDs 1–33 once each, `status`, `reason`, `quotes`. |
| `ladder` | One row per spoken sentence in order, `sentence`, `adds`, `viewer_effect`. Multiple sentences in one paragraph need multiple rows. The checker treats line breaks as speech units too; abbreviations/decimal punctuation can require careful alignment. |
| `audience_states` | Exactly `never_done`, `just_started`, `outsourced`, `struggling`, `competent`; each has `hook` STAY/SKIP/N/A, `reason`, current spoken `quotes`. One quote may serve several states when the editorial rationale is real. |
| `claims` | Every factual claim, not only figures. Each: `claim`, `spoken_quote`, `basis`, `checked_date`, `source_url`; optional `evidence_artifact`. Basis: `primary_documentation`, `user_supplied`, `observed_test`, `inference`, `historical_metric`. Blank URL is allowed only with an actual local evidence file. Numerical sentences need resolving claim receipts; nonnumerical completeness remains editorial. |
| `history` | `mode`: `measured` or `cold_start`; nonempty `search_scope`, `control_notes`, `recent_coverage`; `parents` with `id`, actual `transcript`, `source` HTTP(S) URL or local relative file, `metric`, `observed_at`, `window`. Measured mode needs at least two real comparison receipts and G21/G28 `parent_ids` resolving here. A two-example limited cohort is disclosed, not padded to ten. Cold start keeps G21/G28 BLOCKED and can use an empty parent list. |
| `parity` | PASS/REVISE/BLOCKED/N/A and nonempty factual/locked-wording `reason`; writing completion needs PASS. It is a reviewer report, not semantic diff proof. |
| `rehearsal` | `method`: `human`, `synthetic`, `not_run`; actual positive finite `seconds` for performed rehearsals, null for not_run; `evidence` identifies actual method/artifact or missing check. An actual synthetic rehearsal may clear script timing, not human delivery; estimates are not a performed rehearsal. |
| `production` | Separate status: PENDING/PASS/REVISE/BLOCKED/N/A. The checker always emits `production_verified: false`; it never watched a final cut and cannot certify a supplied production PASS. |

### Review-row contract

G/H/D rows have `id`, `status`, nonempty `reason`, `quotes`, `artifacts`, `sources`, `parent_ids`. All arrays are explicit, even when empty. Status is exactly PASS/REVISE/BLOCKED/N/A. Source entries have HTTP(S) `url`, real non-future ISO `checked_date` (YYYY-MM-DD), and the actual `claim` supported. No URL-embedded credentials.

- All quoted text must resolve in the current narration after whitespace normalization. Quotations anchor a judgment; they cannot prove a viewer's inferred emotion/question is correct.
- A PASS needs an actual spoken anchor except artifact/reference gates G7/G21/G22/G28. G7/G22 need a **real nonempty local artifact file** under the supplied root; for a remote artifact, inspect it and save authorized evidence locally. An arbitrary URL, commit string or path in prose is not verified existence.
- G21/G28 PASS needs IDs resolving to actual supplied parent receipts. IDs/URLs/metric strings are not independently verified by this offline tool. The reviewer must retrieve/check them and compare windows.
- G15/G24/G27 PASS needs claim/source evidence. Humanizer quotes may be empty for a clean scan or genuinely formatting-only N/A; the reason must describe the actual result.
- Paths cannot be absolute, contain `..`, or resolve via symlink outside the supplied root. The checker rejects missing/empty files rather than silently counting them as proof.
- No free-form “gate-exception” comment turns a mechanically failing gate into PASS. Legitimate style changes are explicit profile configuration with actual user evidence in the review.

The mechanical coverage is eight **gate IDs/subsets**, not eight fully proven editorial gates: G4 hook count, G5 configured stock opener scan, G8 point-of-view scan, G10 configured jargon scan, G11 conservative recital scan, G13 URL/handle scan, G14 bracket-cue scan, G25 punctuation/emoji subset. G13 does not automatically recognize every long literal prompt; review it manually. G10 cannot prove audience comprehension; G25 cannot replace all 33 checks. Conservative heuristics may miss unusual syntax or flag legitimate speech; inspect hits, adjust explicitly authorized style rather than argue away a failure, and rerun.

`receipts_valid` can be true with honest BLOCKED/REVISE rows: the record is internally valid, but not finished. `writing_ready` additionally refuses unresolved applicable results, missing rehearsal and contradictions. H1–H4 are essential cumulative checks and cannot be waived through N/A. `human_delivery_verified` and `production_verified` are always false; `human_rehearsal_reported` only identifies a structurally valid reviewer-supplied human rehearsal receipt, not authenticated listening. Production and actual approval are independent. A completed packet must still be read by a competent reviewer from the viewer's seat.
