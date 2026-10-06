# Scriptwriting Gates

One reusable skill for building **evidence-led, natural-sounding video scripts** in any industry.

For marketing agencies, car sellers, fitness creators, educators, service businesses and technology content. No private creator profile, script archive, analytics database or paid-tool dependency is included.

It takes a script from **brief → research → concept → hook → escalating body → proof → spoken edit → complete review**. It is not just a prompt telling an AI to “make this engaging”.

## What's included

- **30 writing gates**, individually reviewed with evidence.
- **4 hook checks** for benefit, emotion, understandable curiosity and credibility.
- **All 33 maintained Humanizer checks**, plus factual and locked-wording parity.
- **7 desire/contrast checks**, including understandable causal mechanism.
- Real-reference transfer, closest-match/weak-control/freshness checks, five audience states and a sentence-by-sentence value ladder.
- A Python validator that catches missing checks, fabricated quotations, nonexistent local assets, stale evidence and mechanical contradictions.
- Separate script readiness, approval, resource fulfillment and actual final-cut production clearance.

This preserves the whole writing/review method while replacing one account's niche, voice, infrastructure and private benchmarks with the user's own brief and evidence. The gates are quality tests, not sentence slots. No forced celebrity hook, AI-only vocabulary, generic setup ending or one-line-per-persona recipe.

## Install

The installable skill is [`skills/scriptwriting-gates`](skills/scriptwriting-gates/SKILL.md). Copy the **whole folder**, not just `SKILL.md`, into your agent's skill directory. It contains all references and the optional checker. No other Humanizer or script-library skill needs installing.

For a local Codex installation, place the folder under `~/.codex/skills/`. For a Claude Code project installation, place it under `.claude/skills/`. These examples use the hosts' normal skill folders; other skill-capable agents can use their own equivalent. Restart/reload your host if required by its skill discovery behavior.

For a chat tool without filesystem skill support, provide `SKILL.md` plus all four linked reference documents. Say that Python validation was not run if the host cannot execute it. Do not claim the chat alone ran the bundled checker.

## Use

```text
Use $scriptwriting-gates to write a 45-second video for first-time car buyers.
My goal is enquiries, not comment bait. Use only these supplied sources.
Keep any unsupported claims blocked and show the full review.
```

```text
Use scriptwriting-gates to revise this gym video in my voice.
Keep the approved opening exactly. Don't invent health or body-transformation results.
```

```text
Audit this agency script with scriptwriting-gates. Do not rewrite it.
Show each gate's evidence and separate script findings from missing final footage.
```

Provide audience, goal, duration, tone/voice samples, factual sources, CTA/resource, exact locks and sponsorship context. Historical transcripts with comparable dated results improve reference transfer; private analytics should stay in your own local workspace, never be committed to this repository.

Start with the [workflow](skills/scriptwriting-gates/references/workflow.md), [complete gates](skills/scriptwriting-gates/references/gates.md), [Humanizer](skills/scriptwriting-gates/references/humanizer.md) and [output/packet contract](skills/scriptwriting-gates/references/packet-contract.md). Three [fictional practice briefs](examples/briefs.md) show industry adaptation and evidence limitations.

## Validate a review

Python 3.10+; standard library only. From the repository root:

```bash
python3 skills/scriptwriting-gates/scripts/validate.py --packet /absolute/path/review.json --root /absolute/path/artifacts
python3 skills/scriptwriting-gates/scripts/validate.py --spoken-file /absolute/path/Script.md
python3 -m unittest discover -s tests -v
```

The standalone spoken scan covers a **mechanical subset only**. Full packet validation also checks all registers and resolving receipts. Neither proves source truth, persuasive quality, real audience reactions, successful product testing, actual human listening, independent approval or final-cut comprehension. Its G25 punctuation scan does not replace all 33 Humanizer checks. Receipts can resolve while editorial reasoning remains wrong.

**New account with no analytics?** You still get a useful provisional draft and every applicable review. G21/G28 remain explicitly blocked as “winner transfer unverified”; no fabricated winners and no pretending cold start passed. Wording approval is possible without measured history, but is not full gate clearance or a performance guarantee.

Customizable voice defaults include first person, hook word budget, audience jargon and dash style. Changes are declared customizations, not evidence that the strict defaults passed. Accuracy and honest evidence are not customizable away.

## Privacy and permissions

No telemetry, network calls, account access, database connection, publishing or file mutation is performed by the validator. It reads only the files you specify; local evidence paths must stay inside the supplied artifact root. Runtime outputs may contain your own script/evidence: keep them private.

The skill does not grant permission to upload, send, post, schedule, buy, install integrations or change accounts. Approval of wording is separate from any external action. Health, safety, finance and regulated campaign claims still need appropriate authoritative substantiation and qualified review when applicable.

MIT licensed. Humanizer lineage and required upstream MIT attribution are in [NOTICE](skills/scriptwriting-gates/NOTICE.md). Synthetic examples and test fixtures are not real customer claims, approvals or measured winners.
