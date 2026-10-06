#!/usr/bin/env python3
"""Validate review receipts and a conservative mechanical subset, not creative quality.

Uses only the standard library. Reads input files without changing them or contacting
any network. A resolved receipt is not independent verification of the reviewer's claim.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit

STATUSES = {"PASS", "REVISE", "BLOCKED", "N/A"}
COLLECTIONS = {"gates": [f"G{i}" for i in range(1, 31)],
               "hook_checks": [f"H{i}" for i in range(1, 5)],
               "humanizer": list(range(1, 34)),
               "desire_checks": [f"D{i}" for i in range(1, 8)]}
STATES = {"never_done", "just_started", "outsourced", "struggling", "competent"}
WORD = re.compile(r"[\w$£€%'’-]+")
SENTENCE = re.compile(r"(?<=[.!?])\s+")
FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'll|i'd|me|my|mine|myself|we|we're|we've|we'll|we'd|us|our|ours|ourselves)\b", re.I)
URLISH = re.compile(r"https?://\S+|www\.\S+|\b\w+\.(?:com|ai|io|net|org|co)\b|@\w+", re.I)
DASH = re.compile(r"[—–]|\s--\s")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF]")
CURLY = re.compile(r"[“”]|(?<!\w)[‘’](?!\w)")
FIGURE = re.compile(r"\$[\d,.]+|\b\d[\d,.]*\b|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|grand|million|billion|trillion)\b", re.I)
DEFAULT_OPENERS = ["here's the thing", "real talk", "honestly", "okay", "ok", "look"]
VERBISH = re.compile(
    r"\b(is|are|was|were|be|been|being|has|have|had|do|does|did|can|could|will|would|"
    r"should|may|might|must|get|gets|got|go|goes|went|make|makes|made|take|takes|took|"
    r"run|runs|ran|open|opens|opened|pick|picks|picked|send|sends|sent|say|says|said|"
    r"show|shows|showed|build|builds|built|use|uses|used|keep|keeps|kept|put|puts|"
    r"start|starts|started|stop|stops|stopped|need|needs|needed|want|wants|wanted|"
    r"comes?|came|pays?|paid|searches|search|finds?|found|writes?|wrote|reads?|"
    r"add|adds|connect|connects|paste|pastes|install|installs|sign|click|clicks|type|"
    r"types|drop|drops|upload|uploads|download|downloads|copy|copies|choose|chooses|"
    r"select|selects|hit|hits|press|presses|save|saves|check|checks|turn|turns|"
    r"you|they|it|he|she|we|i)\b", re.I)
PRONOUN_LEAD = {"it", "its", "this", "that", "these", "those", "they", "them", "their", "you", "your",
                "we", "our", "us", "he", "she", "his", "her", "i", "and", "or", "but", "so", "then",
                "there", "here", "which", "who", "what", "when", "if", "because"}
AFTER_LIST = r"(?=[.,!?;]|\s+(?:for|in|on|at|to|from|with|and|or|then|so|that|which|while|over|after|before|every|each|right|across|until|but)\b|$)"
PAIRED_TAIL = re.compile(r",\s+(?P<b>[\w$£€%'’-]+(?:\s+[\w$£€%'’-]+){0,2})\s+(?:and|or)\s+(?P<c>[\w$£€%'’-]+(?:\s+[\w$£€%'’-]+)?)" + AFTER_LIST)


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def sentences(spoken):
    """Line breaks are speech units too; sentence punctuation splits within a line."""
    return [part.strip() for line in spoken.splitlines()
            for part in SENTENCE.split(line.strip()) if part.strip()]


def extract_spoken(document):
    """Only the explicit current block, never old reviews or the whole Markdown file.

    Current material must be above a level-two Superseded/Archive heading. Multiple
    current blocks are ambiguous and rejected rather than choosing a convenient one.
    """
    current = re.split(r"(?im)^##\s+(?:Superseded|Archive|Archived)\b", document)[0]
    starts = list(re.finditer(r"(?im)^##\s+(?:Spoken script|Final script)\b[^\n]*\n", current))
    if len(starts) != 1:
        raise ValueError("exactly one current '## Spoken script' or '## Final script' block is required")
    block = current[starts[0].end():]
    block = re.split(r"(?m)^##\s|^---\s*$", block)[0]
    # A blockquote is formatting; do not discard bracket cues, URLs, or troublesome lines.
    spoken = "\n".join(re.sub(r"^>\s?", "", line.strip()) for line in block.splitlines()).strip()
    if not spoken:
        raise ValueError("current spoken block is empty")
    return spoken


def three_item_lists(spoken):
    """Conservative recital scan; clause chains and action sequences are not lists."""
    hits = []
    for sentence in sentences(spoken):
        for match in PAIRED_TAIL.finditer(sentence):
            b, c = match.group("b"), match.group("c")
            head = WORD.findall(sentence[:match.start()])
            tail = head[-1] if head else ""
            if tail and not any(VERBISH.search(x) for x in (tail, b, c)):
                hits.append({"sentence": sentence, "span": f"{tail}, {b} and {c}"})
        raw = [part.strip() for part in sentence.split(",")]
        for index in range(len(raw) - 2):
            window = raw[index:index + 3]
            items = [re.sub(r"^(and|or|but|so|then)\s+", "", p, flags=re.I) for p in window]
            tokens = [WORD.findall(p) for p in items]
            if not all(tokens):
                continue
            lengths = list(map(len, tokens))
            leads = [p[0].lower() for p in tokens]
            tail_lead = tokens[0][-2].lower() if lengths[0] > 2 else leads[0]
            lead_set = [tail_lead, leads[1], leads[2]]
            repeated = next((x for x in lead_set if x not in PRONOUN_LEAD and lead_set.count(x) >= 2), None)
            third_item = leads[2] not in PRONOUN_LEAD and (lengths[2] <= 4 or leads[2] == repeated)
            anaphora = repeated and lengths[1] <= 5 and third_item
            noun_list = (lengths[1] <= 4 and lengths[2] <= 4 and
                         not any(VERBISH.search(x) for x in (" ".join(tokens[0][-2:]), items[1], items[2])))
            if anaphora or noun_list:
                hits.append({"sentence": sentence, "span": ", ".join(window)})
    return hits


def mechanical_checks(spoken, profile=None):
    profile = profile or {}
    parts = sentences(spoken)
    if not parts:
        return {"status": "BLOCKED", "failed": ["INPUT"], "checks": {}, "reason": "empty spoken script"}
    hook = parts[0]
    max_words = profile.get("hook_max_words", 18)
    if type(max_words) is not int or max_words < 1:
        max_words = 18
    openers = profile.get("banned_openers", DEFAULT_OPENERS)
    if not isinstance(openers, list):
        openers = DEFAULT_OPENERS
    normalized_hook = hook.replace("’", "'").replace("‘", "'")
    opener_hits = [x for x in openers if isinstance(x, str) and x and
                   re.match(re.escape(x.replace("’", "'").replace("‘", "'")) + r"(?:\b|$)", normalized_hook, re.I)]
    if re.match(r"^it'?s not\b.+,?\s+it'?s\b", normalized_hook, re.I):
        opener_hits.append("formulaic 'it's not ..., it's ...' opener")
    jargon = profile.get("jargon_terms", [])
    if not isinstance(jargon, list):
        jargon = []
    jargon_hits = [x for x in jargon if isinstance(x, str) and x and
                   re.search(r"(?<!\w)" + re.escape(x) + r"(?!\w)", spoken, re.I)]
    person_hits = [m.group(0) for m in FIRST_PERSON.finditer(spoken.replace("’", "'").replace("‘", "'"))]
    lists = three_item_lists(spoken)
    style_hits = {"dashes": DASH.findall(spoken) if not profile.get("allow_dash_style", False) else [],
                  "emoji": EMOJI.findall(spoken), "curly_quotes": CURLY.findall(spoken) if not profile.get("allow_curly_quotes", False) else []}
    checks = {}
    def add(gate, label, hits):
        checks[gate] = {"label": label, "status": "REVISE" if hits else "PASS", "evidence": hits}
    add("G4", "Hook word limit", [f"{len(WORD.findall(hook))} > {max_words}"] if len(WORD.findall(hook)) > max_words else [])
    add("G5", "Configured stock opener scan", opener_hits)
    add("G8", "Full spoken-script point of view", [] if profile.get("first_person_allowed", False) else person_hits)
    add("G10", "Configured jargon scan (not a comprehension verdict)", jargon_hits)
    add("G11", "Three-item recital scan", lists)
    add("G13", "Spoken URL/domain/handle scan", URLISH.findall(spoken))
    add("G14", "Bracket/stage-cue scan", re.findall(r"[\[\]{}]", spoken))
    add("G25", "Humanizer mechanical subset only", [f"{key}: {value}" for key, value in style_hits.items() if value])
    failed = [gate for gate, row in checks.items() if row["status"] != "PASS"]
    return {"status": "REVISE" if failed else "PASS", "failed": failed, "checks": checks,
            "coverage": "8 gate IDs; G10 and G25 are subsets, not full semantic passes"}


def _validate_packet(packet, root):
    """Return integrity findings and readiness. Never mutate packet or files."""
    findings, unresolved = [], []
    root = Path(root).resolve()
    def error(where, problem):
        findings.append({"where": where, "problem": problem})
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    def strings(value, where):
        if not isinstance(value, list) or not all(text(x) for x in value):
            error(where, "must be an array of nonempty strings")
            return []
        return value
    def artifact(value, where):
        if not text(value) or "\\" in value or value.startswith(("/", "~")) or ":" in value:
            error(where, "artifact must be a relative file path")
            return False
        path = PurePosixPath(value)
        if ".." in path.parts or not path.parts:
            error(where, "artifact traversal is forbidden")
            return False
        resolved = (root / value).resolve()
        if not resolved.is_relative_to(root):
            error(where, "artifact escapes root (including symlink escape)")
            return False
        if not resolved.is_file() or resolved.stat().st_size == 0:
            error(where, "artifact must resolve to an existing nonempty file")
            return False
        return True
    def url(value, where):
        try:
            parsed = urlsplit(value) if isinstance(value, str) else None
            valid = parsed and parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        if not valid:
            error(where, "source URL must be HTTP(S), with a host and no embedded credentials")
        return bool(valid)
    def checked(value, where):
        try:
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError()
            if date.fromisoformat(value) > date.today():
                raise ValueError()
        except ValueError:
            error(where, "checked_date must be a real non-future ISO date (YYYY-MM-DD)")
    if not isinstance(packet, dict):
        return {"receipts_valid": False, "writing_ready": False, "findings": [{"where": "packet", "problem": "must be an object"}], "unresolved": []}
    if not root.is_dir():
        error("root", "artifact root must exist as a directory")
    if packet.get("version") != "v1":
        error("version", "must be v1")
    spoken = packet.get("spoken_script", "")
    if not text(spoken):
        error("spoken_script", "full current spoken script is required and must be nonempty")
        spoken = ""
    spoken_sha256 = hashlib.sha256(spoken.encode("utf-8")).hexdigest()
    if "spoken_sha256" in packet and packet["spoken_sha256"] != spoken_sha256:
        error("spoken_sha256", "supplied hash must exactly match SHA256 of current spoken_script UTF-8 bytes")
    mode = packet.get("mode")
    if mode not in {"draft", "audit", "revision"}:
        error("mode", "must be draft, audit, or revision")
    if mode == "audit" and (not text(packet.get("locked_script")) or packet["locked_script"] != spoken):
        error("locked_script", "audit mode requires exact unchanged locked_script")
    profile = packet.get("profile")
    if not isinstance(profile, dict):
        error("profile", "explicit profile object is required")
        profile = {}
    for key in ("first_person_allowed", "allow_dash_style"):
        if type(profile.get(key)) is not bool:
            error("profile." + key, "explicit boolean is required")
    if type(profile.get("hook_max_words")) is not int or profile.get("hook_max_words", 0) < 1:
        error("profile.hook_max_words", "positive integer required")
    strings(profile.get("jargon_terms"), "profile.jargon_terms")
    if "banned_openers" in profile:
        strings(profile["banned_openers"], "profile.banned_openers")
    for key in ("specialist_audience", "allow_curly_quotes"):
        if key in profile and type(profile[key]) is not bool:
            error("profile." + key, "must be an explicit boolean when supplied")
    mechanical = mechanical_checks(spoken, profile)
    unresolved.extend("mechanical:" + gate for gate in mechanical["failed"])
    sn = normalize(spoken)
    def quotes(value, where):
        out = strings(value, where)
        for quote in out:
            if normalize(quote) not in sn:
                error(where, "quoted text is absent from the current spoken script: " + quote)
        return out
    def source_rows(value, where):
        if not isinstance(value, list):
            error(where, "must be an array")
            return []
        for index, row in enumerate(value):
            at = f"{where}[{index}]"
            if not isinstance(row, dict):
                error(at, "source must be an object")
                continue
            url(row.get("url"), at + ".url")
            checked(row.get("checked_date"), at + ".checked_date")
            if not text(row.get("claim")):
                error(at + ".claim", "nonempty claim required")
        return value
    collections = {}
    for name, ids in COLLECTIONS.items():
        rows = packet.get(name)
        if not isinstance(rows, list):
            error(name, "complete array is required")
            rows = []
        actual = [row.get("id") for row in rows if isinstance(row, dict)]
        # type matters: True is not Humanizer check 1.
        if Counter((type(i).__name__, str(i)) for i in actual) != Counter((type(i).__name__, str(i)) for i in ids):
            error(name, "must contain each required ID exactly once: " + ", ".join(map(str, ids)))
        collections[name] = {}
        for index, row in enumerate(rows):
            at = f"{name}[{index}]"
            if not isinstance(row, dict):
                error(at, "review row must be an object")
                continue
            identifier = row.get("id")
            if isinstance(identifier, (str, int)):
                collections[name][identifier] = row
            status = row.get("status")
            if status not in STATUSES:
                error(at + ".status", "invalid review status")
            elif status in {"REVISE", "BLOCKED"}:
                unresolved.append(f"{name}:{identifier}")
            if name == "hook_checks" and status == "N/A":
                error(at + ".status", "H1-H4 are cumulative essential hook checks and cannot be N/A")
            if not text(row.get("reason")):
                error(at + ".reason", "nonempty evidence/reason required, including N/A")
            q = quotes(row.get("quotes"), at + ".quotes")
            if name != "humanizer":
                paths = strings(row.get("artifacts"), at + ".artifacts")
                for path in paths:
                    artifact(path, at + ".artifacts")
                source_rows(row.get("sources"), at + ".sources")
                strings(row.get("parent_ids"), at + ".parent_ids")
                if status == "PASS" and name in {"hook_checks", "desire_checks"} and not q:
                    error(at, "PASS requires a spoken anchor quote, not an invented inferred utterance")
            if status == "PASS" and name == "gates":
                if identifier not in {"G7", "G21", "G22", "G28"} and not q:
                    error(at, "PASS requires at least one exact spoken evidence quote")
                if identifier in {"G7", "G22"} and not row.get("artifacts"):
                    error(at, "PASS requires an existing artifact file; an assertion/commit marker is not evidence")
                if identifier in mechanical["failed"]:
                    error(at, "claimed PASS contradicts mechanical check; prose exceptions cannot override it")
    # Sentence-level ladder: exact count, order, and content; not stale row-count sufficiency.
    ladder = packet.get("ladder")
    if not isinstance(ladder, list):
        error("ladder", "complete sentence-level ladder is required")
        ladder = []
    parts = sentences(spoken)
    if [normalize(row.get("sentence", "")) if isinstance(row, dict) and isinstance(row.get("sentence"), str) else None for row in ladder] != [normalize(s) for s in parts]:
        error("ladder", "must cover every current spoken sentence exactly once, in order")
    for index, row in enumerate(ladder):
        if not isinstance(row, dict) or not all(text(row.get(key)) for key in ("sentence", "adds", "viewer_effect")):
            error(f"ladder[{index}]", "sentence, adds, and viewer_effect must all be nonempty")
    audience = packet.get("audience_states")
    if not isinstance(audience, list):
        error("audience_states", "complete audience-state array required")
        audience = []
    state_ids = [row.get("state") for row in audience if isinstance(row, dict)]
    if Counter(str(x) for x in state_ids) != Counter(STATES):
        error("audience_states", "each of the five states must occur exactly once")
    for index, row in enumerate(audience):
        at = f"audience_states[{index}]"
        if not isinstance(row, dict):
            error(at, "must be an object")
            continue
        if row.get("hook") not in {"STAY", "SKIP", "N/A"} or not text(row.get("reason")):
            error(at, "valid hook decision and nonempty reason required")
        q = quotes(row.get("quotes"), at + ".quotes")
        if row.get("hook") == "STAY" and not q:
            error(at, "STAY requires an exact spoken quote")
    if collections.get("gates", {}).get("G29", {}).get("status") == "PASS" and not profile.get("specialist_audience", False):
        staying = {row.get("state") for row in audience if isinstance(row, dict) and row.get("hook") == "STAY"}
        if len(staying) < 4 or not {"never_done", "just_started"}.issubset(staying):
            error("G29", "default breadth PASS requires at least four STAY states, including never_done and just_started; explicit specialist_audience profile can customize this")
    claims = packet.get("claims")
    if not isinstance(claims, list):
        error("claims", "claim/source traceability array required (empty only if there are no factual claims)")
        claims = []
    claims_quotes = []
    for index, row in enumerate(claims):
        at = f"claims[{index}]"
        if not isinstance(row, dict):
            error(at, "claim must be an object")
            continue
        if not text(row.get("claim")) or row.get("basis") not in {"primary_documentation", "user_supplied", "observed_test", "inference", "historical_metric"}:
            error(at, "nonempty claim and valid basis required")
        q = row.get("spoken_quote")
        if text(q):
            quotes([q], at + ".spoken_quote")
            claims_quotes.append(q)
        else:
            error(at + ".spoken_quote", "exact spoken quote required")
        checked(row.get("checked_date"), at + ".checked_date")
        if text(row.get("source_url")):
            url(row["source_url"], at + ".source_url")
        elif row.get("source_url") != "" or not text(row.get("evidence_artifact")):
            error(at, "source_url is required; blank is allowed only with evidence_artifact")
        if "evidence_artifact" in row:
            artifact(row["evidence_artifact"], at + ".evidence_artifact")
    for part in parts:
        figures = {match.group(0).casefold() for match in FIGURE.finditer(part)}
        covered = {match.group(0).casefold() for quote in claims_quotes
                   if normalize(part) in normalize(quote) or normalize(quote) in normalize(part)
                   for match in FIGURE.finditer(quote)}
        if figures - covered:
            error("claims", "numeric sentence lacks a resolving claim receipt for " +
                  ", ".join(sorted(figures - covered)) + ": " + part)
    history = packet.get("history")
    parent_ids = set()
    if not isinstance(history, dict):
        error("history", "history object required; absence is not permission to claim winners")
        history = {}
    for key in ("search_scope", "control_notes", "recent_coverage"):
        if not text(history.get(key)):
            error("history." + key, "nonempty scope/evidence or explicit missing-evidence note required")
    parents = history.get("parents")
    if not isinstance(parents, list):
        error("history.parents", "parent receipt array required")
        parents = []
    for index, parent in enumerate(parents):
        at = f"history.parents[{index}]"
        if not isinstance(parent, dict) or not all(text(parent.get(key)) for key in ("id", "transcript", "source", "metric", "observed_at", "window")):
            error(at, "id, transcript, source, metric, observed_at, window all required")
            continue
        if parent["id"] in parent_ids:
            error(at, "duplicate parent ID")
        parent_ids.add(parent["id"])
        if parent["source"].startswith(("http://", "https://")):
            url(parent["source"], at + ".source")
        else:
            artifact(parent["source"], at + ".source")
    gates = collections.get("gates", {})
    if history.get("mode") == "cold_start":
        for gate in ("G21", "G28"):
            if gates.get(gate, {}).get("status") != "BLOCKED":
                error("history." + gate, "cold-start measured-history gates must stay BLOCKED, never PASS/N/A")
    elif history.get("mode") == "measured":
        if len(parent_ids) < 2:
            error("history.parents", "measured mode requires at least two actual comparison receipts")
        for gate in ("G21", "G28"):
            row = gates.get(gate, {})
            if row.get("status") == "PASS" and not row.get("parent_ids"):
                error(gate, "PASS requires resolving parent IDs")
    else:
        error("history.mode", "must be measured or cold_start")
    for name, rows in collections.items():
        if name == "humanizer":
            continue
        for identifier, row in rows.items():
            ids = row.get("parent_ids")
            if isinstance(ids, list):
                for parent in ids:
                    if not isinstance(parent, str) or parent not in parent_ids:
                        error(f"{name}:{identifier}.parent_ids", "parent does not resolve to a current history receipt")
    for gate in ("G15", "G24", "G27"):
        if gates.get(gate, {}).get("status") == "PASS" and not claims and not gates[gate].get("sources"):
            error(gate, "claimed PASS needs claim/source receipts")
    parity = packet.get("parity")
    if not isinstance(parity, dict) or parity.get("status") not in STATUSES or not text(parity.get("reason")):
        error("parity", "status and explicit factual/locked-wording parity reason required")
    elif parity["status"] != "PASS":
        unresolved.append("parity")
    rehearsal = packet.get("rehearsal")
    if not isinstance(rehearsal, dict) or rehearsal.get("method") not in {"human", "synthetic", "not_run"} or not text(rehearsal.get("evidence")):
        error("rehearsal", "method and nonempty evidence (or honest missing note) required")
    else:
        seconds = rehearsal.get("seconds")
        if rehearsal["method"] == "not_run":
            if seconds is not None:
                error("rehearsal.seconds", "not_run timing must be null")
        elif type(seconds) not in {int, float} or not math.isfinite(seconds) or seconds <= 0:
            error("rehearsal.seconds", "actual positive finite timing required")
        if rehearsal["method"] == "not_run":
            unresolved.append("script_rehearsal")
    production = packet.get("production")
    if not isinstance(production, dict) or production.get("status") not in {"PENDING", "PASS", "REVISE", "BLOCKED", "N/A"}:
        error("production", "separate production status object required")
    return {"receipts_valid": not findings, "writing_ready": not findings and not unresolved,
            "findings": findings, "unresolved": sorted(set(unresolved)), "mechanical": mechanical,
            "spoken_sha256": spoken_sha256,
            "production_status": production.get("status") if isinstance(production, dict) else None,
            "production_verified": False,
            "human_delivery_verified": False,
            "human_rehearsal_reported": isinstance(rehearsal, dict) and rehearsal.get("method") == "human" and not any(f["where"].startswith("rehearsal") for f in findings),
            "limitations": "No network checks; sources, metrics, rehearsal timing, human delivery, permissions and semantic quality are reviewer-supplied. Eight mechanical gate IDs are not the full review or a guarantee of performance."}


def validate_packet(packet, root):
    """Fail closed even on malformed nested JSON types; never mutate inputs."""
    try:
        return _validate_packet(packet, root)
    except (TypeError, ValueError, OSError, RecursionError) as exc:
        return {"receipts_valid": False, "writing_ready": False,
                "findings": [{"where": "packet", "problem": "malformed packet or unreadable artifact: " + str(exc)}],
                "unresolved": [], "production_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, help="current JSON review packet")
    parser.add_argument("--root", type=Path, help="artifact root (required for packet validation)")
    parser.add_argument("--spoken-file", type=Path, help="Markdown with one current spoken section; optionally compare it to the packet")
    args = parser.parse_args(argv)
    if not args.packet and not args.spoken_file:
        parser.error("supply --packet or --spoken-file")
    if args.packet and not args.root:
        parser.error("--root is required with --packet")
    try:
        extracted = extract_spoken(args.spoken_file.read_text(encoding="utf-8")) if args.spoken_file else None
        if args.packet:
            packet = json.loads(args.packet.read_text(encoding="utf-8"))
            result = validate_packet(packet, args.root)
            if extracted is not None and (not isinstance(packet, dict) or normalize(extracted) != normalize(packet.get("spoken_script", ""))):
                result["findings"].append({"where": "spoken-file", "problem": "current spoken section does not match packet"})
                result["receipts_valid"] = result["writing_ready"] = False
            code = 0 if result["writing_ready"] else 1
        else:
            result = mechanical_checks(extracted)
            result["spoken_sha256"] = hashlib.sha256(extracted.encode("utf-8")).hexdigest()
            result["writing_ready"] = False
            result["limitations"] = "Standalone scan is only a mechanical subset; complete review packet required for writing readiness."
            code = 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, TypeError) as exc:
        result = {"receipts_valid": False, "writing_ready": False, "error": str(exc)}
        code = 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
