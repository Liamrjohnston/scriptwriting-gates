"""Synthetic receipt fixtures only; these do not certify a real script or source."""
import copy
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "scriptwriting-gates" / "scripts" / "validate.py"
spec = importlib.util.spec_from_file_location("public_validate", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def packet():
    first = "Your checkout can lose buyers before payment."
    second = "A visible delivery date removes that uncertainty."
    def row(identifier):
        return {"id": identifier, "status": "PASS", "reason": "Synthetic reviewer evidence, not verified creative quality.",
                "quotes": [first], "artifacts": [], "sources": [], "parent_ids": []}
    result = {"version": "v1", "mode": "draft", "spoken_script": first + "\n" + second,
              "profile": {"hook_max_words": 18, "first_person_allowed": False,
                          "jargon_terms": [], "allow_dash_style": False},
              "gates": [row(f"G{i}") for i in range(1, 31)],
              "hook_checks": [row(f"H{i}") for i in range(1, 5)],
              "humanizer": [{"id": i, "status": "PASS", "reason": "Synthetic review.", "quotes": []} for i in range(1, 34)],
              "desire_checks": [row(f"D{i}") for i in range(1, 8)],
              "ladder": [{"sentence": sentence, "adds": "Names the problem or its mechanism.",
                          "viewer_effect": "Synthetic assessment."} for sentence in (first, second)],
              "audience_states": [{"state": state, "hook": "STAY", "reason": "Synthetic assessment.", "quotes": [first]}
                                  for state in sorted(validator.STATES)],
              "claims": [{"claim": "A synthetic test claim.", "source_url": "", "evidence_artifact": "proof.txt",
                          "checked_date": date.today().isoformat(), "basis": "user_supplied", "spoken_quote": second}],
              "history": {"mode": "measured", "search_scope": "Authorized synthetic test corpus only.",
                          "parents": [{"id": str(i), "transcript": first, "source": "proof.txt", "metric": "Synthetic metric, not an actual winner.",
                                       "observed_at": date.today().isoformat(), "window": "Same synthetic observation window."} for i in range(2)],
                          "control_notes": "Synthetic control, no real performance inference.", "recent_coverage": "No actual publishing history queried."},
              "parity": {"status": "PASS", "reason": "Synthetic factual parity check."},
              "rehearsal": {"method": "human", "seconds": 12, "evidence": "Synthetic timing receipt for unit tests only."},
              "production": {"status": "PENDING"}}
    for identifier in ("G7", "G22"):
        result["gates"][int(identifier[1:]) - 1]["artifacts"] = ["proof.txt"]
    for identifier in ("G21", "G28"):
        result["gates"][int(identifier[1:]) - 1]["parent_ids"] = ["0"]
    return result


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "proof.txt").write_text("Synthetic nonempty evidence file.")
        self.packet = packet()

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        return validator.validate_packet(self.packet, self.root)

    def assertInvalid(self, containing=None):
        result = self.check()
        self.assertFalse(result["receipts_valid"], result)
        self.assertFalse(result["writing_ready"])
        if containing:
            self.assertIn(containing, json.dumps(result["findings"]))
        return result

    def test_complete_receipts_do_not_certify_production_or_quality(self):
        result = self.check()
        self.assertTrue(result["receipts_valid"], result["findings"])
        self.assertTrue(result["writing_ready"])
        self.assertFalse(result["production_verified"])
        self.assertFalse(result["human_delivery_verified"])
        self.assertTrue(result["human_rehearsal_reported"])
        self.assertEqual(result["production_status"], "PENDING")
        self.assertIn("reviewer-supplied", result["limitations"])

    def test_missing_and_empty_spoken_fail_closed(self):
        self.packet.pop("spoken_script")
        self.assertInvalid("spoken_script")
        self.packet["spoken_script"] = " \n "
        self.assertInvalid("spoken_script")

    def test_fake_quote_is_rejected_even_when_one_quote_resolves(self):
        self.packet["gates"][0]["quotes"].append("A fictional line that never appears.")
        self.assertInvalid("absent")

    def test_missing_duplicate_and_wrong_type_ids_are_rejected(self):
        self.packet["gates"][-1] = copy.deepcopy(self.packet["gates"][0])
        self.assertInvalid("exactly once")
        self.packet = packet()
        self.packet["humanizer"][0]["id"] = True
        self.assertInvalid("exactly once")

    def test_missing_entire_register_or_bad_status_rejected(self):
        self.packet.pop("desire_checks")
        self.assertInvalid("complete array")
        self.packet = packet()
        self.packet["hook_checks"][0]["status"] = "APPROVED"
        self.assertInvalid("invalid review status")

    def test_unresolved_gate_is_honest_valid_wip_not_ready(self):
        self.packet["gates"][0]["status"] = "REVISE"
        result = self.check()
        self.assertTrue(result["receipts_valid"], result["findings"])
        self.assertFalse(result["writing_ready"])
        self.assertIn("gates:G1", result["unresolved"])

    def test_na_requires_reason(self):
        self.packet["gates"][0].update(status="N/A", reason="")
        self.assertInvalid("reason")

    def test_cold_start_cannot_masquerade_as_measured_pass_or_na(self):
        self.packet["history"].update(mode="cold_start", parents=[])
        for gate in ("G21", "G28"):
            self.packet["gates"][int(gate[1:]) - 1]["parent_ids"] = []
        self.assertInvalid("must stay BLOCKED")
        self.packet["gates"][20]["status"] = "BLOCKED"
        self.packet["gates"][27]["status"] = "N/A"
        self.assertInvalid("must stay BLOCKED")
        self.packet["gates"][27]["status"] = "BLOCKED"
        result = self.check()
        self.assertTrue(result["receipts_valid"], result["findings"])
        self.assertFalse(result["writing_ready"])

    def test_parent_id_must_resolve_to_actual_receipt(self):
        self.packet["gates"][20]["parent_ids"] = ["nonexistent"]
        self.assertInvalid("does not resolve")
        self.packet = packet()
        self.packet["history"]["parents"].pop()
        self.assertInvalid("at least two")

    def test_artifact_paths_cannot_escape_or_use_markers(self):
        for bad in ("../proof.txt", "/etc/hosts", "~/proof.txt", "abc123 commit", "https://example.com"):
            with self.subTest(path=bad):
                self.packet = packet()
                self.packet["gates"][6]["artifacts"] = [bad]
                self.assertInvalid("artifact")

    def test_symlink_escape_and_empty_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "file.txt"
            external.write_text("private outside content")
            (self.root / "escape.txt").symlink_to(external)
            self.packet["gates"][6]["artifacts"] = ["escape.txt"]
            self.assertInvalid("symlink escape")
        (self.root / "empty.txt").touch()
        self.packet["gates"][6]["artifacts"] = ["empty.txt"]
        self.assertInvalid("nonempty file")

    def test_ladder_covers_sentences_not_only_lines_or_row_counts(self):
        self.packet["spoken_script"] = self.packet["spoken_script"].replace("\n", " ")
        self.assertTrue(self.check()["receipts_valid"])
        self.packet["ladder"] = [self.packet["ladder"][0], copy.deepcopy(self.packet["ladder"][0])]
        self.assertInvalid("every current spoken sentence")

    def test_claimed_pass_cannot_override_mechanical_failure(self):
        self.packet["profile"]["hook_max_words"] = 2
        self.assertInvalid("contradicts mechanical")
        self.packet["gates"][3]["status"] = "N/A"
        result = self.check()
        self.assertFalse(result["writing_ready"])
        self.assertIn("mechanical:G4", result["unresolved"])

    def test_inline_exception_cannot_bypass_mechanics(self):
        text = "I changed the deal.\n<!-- gate-exception: G8 | User: keep my wording -->"
        result = validator.mechanical_checks(text)
        self.assertIn("G8", result["failed"])

    def test_first_person_late_in_script_and_common_variants_detected(self):
        prefix = "Your offer works. Your buyer sees it. Your payment arrives. "
        for variant in ("I", "I've", "I'd", "we'll", "we'd", "ours", "ourselves", "We’re"):
            with self.subTest(variant=variant):
                result = validator.mechanical_checks(prefix + variant + " made the change.")
                self.assertIn("G8", result["failed"])
                self.assertTrue(result["checks"]["G8"]["evidence"])

    def test_current_script_hash_is_exact_and_emitted(self):
        expected = hashlib.sha256(self.packet["spoken_script"].encode("utf-8")).hexdigest()
        self.assertEqual(self.check()["spoken_sha256"], expected)
        self.packet["spoken_sha256"] = expected
        self.assertTrue(self.check()["receipts_valid"])
        self.packet["spoken_sha256"] = expected.upper()
        self.assertInvalid("supplied hash must exactly match")
        self.packet["spoken_sha256"] = "0" * 64
        self.assertInvalid("spoken_sha256")

    def test_formulaic_and_stock_openers_are_apostrophe_normalized(self):
        for spoken in ("Look at your next offer.", "Here’s the thing about your offer.",
                       "It’s not about price, it’s about delivery.", "It's not another discount, it's a clear offer."):
            with self.subTest(spoken=spoken):
                self.assertIn("G5", validator.mechanical_checks(spoken)["failed"])
        self.assertNotIn("G5", validator.mechanical_checks("Most buyers can see your offer.")["failed"])
        self.assertNotIn("G5", validator.mechanical_checks("This delivery date is clear.")["failed"])

    def test_explicit_profile_can_control_style_without_fake_quote_exception(self):
        text = "I fixed your offer — you can see the change."
        strict = validator.mechanical_checks(text)
        self.assertIn("G8", strict["failed"])
        self.assertIn("G25", strict["failed"])
        configured = validator.mechanical_checks(text, {"first_person_allowed": True, "allow_dash_style": True})
        self.assertNotIn("G8", configured["failed"])
        self.assertNotIn("G25", configured["failed"])

    def test_all_essential_hook_checks_na_cannot_yield_ready(self):
        for row in self.packet["hook_checks"]:
            row["status"] = "N/A"
        self.assertInvalid("cumulative essential hook checks")

    def test_curly_quote_style_requires_explicit_boolean_customization(self):
        spoken = 'Your answer is “ready”.'
        self.assertIn("G25", validator.mechanical_checks(spoken)["failed"])
        self.assertNotIn("G25", validator.mechanical_checks(spoken, {"allow_curly_quotes": True})["failed"])
        self.packet["profile"]["allow_curly_quotes"] = "yes"
        self.assertInvalid("profile.allow_curly_quotes")
        self.packet["profile"]["allow_curly_quotes"] = False
        self.assertTrue(self.check()["receipts_valid"])

    def test_curly_apostrophe_is_not_a_curly_quotation_mark(self):
        self.assertNotIn("G25", validator.mechanical_checks("You’re getting your answer.")["failed"])
        self.assertIn("G25", validator.mechanical_checks('Your answer is “ready”.')["failed"])

    def test_three_item_recitals_are_detected(self):
        for text in ("You do not need a camera, studio, or team.",
                     "Your report counts views, comments and shares for seven days.",
                     "You control the face, the hair, the wardrobe."):
            with self.subTest(text=text):
                self.assertIn("G11", validator.mechanical_checks(text)["failed"])

    def test_clause_action_pair_and_appositive_are_not_recitals(self):
        for text in ("Your customer pays, you ship it, and they get the receipt.",
                     "Connect the app, add your product and sign in.",
                     "Your free tool, Example, searches the catalog.",
                     "Wrong label, wrong shape, and you cannot use the shot.",
                     "Your offer covers sales and service."):
            with self.subTest(text=text):
                self.assertNotIn("G11", validator.mechanical_checks(text)["failed"])

    def test_latest_block_only_and_missing_or_ambiguous_block_rejected(self):
        doc = "## Spoken script\nYour offer is clear.\n\n## Full review\nFake evidence.\n\n## Superseded\n## Spoken script\nI said the old thing."
        self.assertEqual(validator.extract_spoken(doc), "Your offer is clear.")
        for bad in ("## Review\nOnly review text.", "## Spoken script\n\n## Review\nnone", "## Spoken script\nOne.\n## Final script\nTwo."):
            with self.subTest(document=bad):
                with self.assertRaises(ValueError):
                    validator.extract_spoken(bad)
        self.assertIn("[show offer]", validator.extract_spoken("## Spoken script\nYour offer is clear.\n[show offer]"))

    def test_audit_is_immutable_and_requires_exact_lock(self):
        before = copy.deepcopy(self.packet)
        self.packet["mode"] = "audit"
        self.packet["locked_script"] = self.packet["spoken_script"]
        stored = copy.deepcopy(self.packet)
        self.assertTrue(self.check()["receipts_valid"])
        self.assertEqual(self.packet, stored)
        self.packet["locked_script"] += " "
        self.assertInvalid("exact unchanged")
        self.assertEqual(before["spoken_script"], self.packet["spoken_script"])

    def test_measured_synthetic_rehearsal_can_pass_writing_not_human_delivery(self):
        self.packet["rehearsal"]["method"] = "synthetic"
        result = self.check()
        self.assertTrue(result["receipts_valid"])
        self.assertTrue(result["writing_ready"])
        self.assertEqual(result["production_status"], "PENDING")
        self.assertFalse(result["production_verified"])
        self.assertFalse(result["human_delivery_verified"])
        self.assertFalse(result["human_rehearsal_reported"])
        self.packet["rehearsal"].update(method="human", seconds=float("nan"))
        self.assertInvalid("finite")
        self.assertFalse(self.check()["human_delivery_verified"])
        self.assertFalse(self.check()["human_rehearsal_reported"])

    def test_not_run_rehearsal_blocks_writing(self):
        self.packet["rehearsal"].update(method="not_run", seconds=None)
        result = self.check()
        self.assertTrue(result["receipts_valid"])
        self.assertFalse(result["writing_ready"])
        self.assertIn("script_rehearsal", result["unresolved"])

    def test_g29_default_requires_breadth_without_hiding_na_quota(self):
        for row in self.packet["audience_states"]:
            if row["state"] == "never_done":
                row["hook"] = "N/A"
        self.assertInvalid("default breadth PASS")
        self.packet["profile"]["specialist_audience"] = True
        self.assertTrue(self.check()["receipts_valid"])
        self.packet["profile"].pop("specialist_audience")
        self.packet["gates"][28]["status"] = "N/A"
        self.assertTrue(self.check()["receipts_valid"])
        self.packet["audience_states"].pop()
        self.assertInvalid("five states")

    def test_g29_four_states_must_include_both_beginner_states(self):
        for row in self.packet["audience_states"]:
            if row["state"] in {"outsourced", "struggling"}:
                row["hook"] = "SKIP"
        self.assertInvalid("at least four")

    def test_number_words_require_claim_coverage(self):
        sentence = "Your plan covers two locations with eleven appointments."
        self.packet["spoken_script"] += "\n" + sentence
        self.packet["ladder"].append({"sentence": sentence, "adds": "Synthetic capacity.", "viewer_effect": "Synthetic."})
        self.packet["claims"][0]["spoken_quote"] = "two locations"
        self.assertInvalid("eleven")
        self.packet["claims"][0]["spoken_quote"] = sentence
        self.assertTrue(self.check()["receipts_valid"])

    def test_source_date_and_url_structurally_checked(self):
        self.packet["claims"][0].update(source_url="https://" + "secret" + "@" + "example.com", checked_date="2999-01-01")
        self.assertInvalid("no embedded credentials")
        self.assertInvalid("non-future")

    def test_numeric_claim_must_point_to_current_spoken_figure(self):
        self.packet["spoken_script"] += "\nYour next payment is 300 dollars."
        self.packet["ladder"].append({"sentence": "Your next payment is 300 dollars.", "adds": "Synthetic amount.", "viewer_effect": "Synthetic."})
        self.assertInvalid("numeric sentence lacks")

    def test_multiple_figures_cannot_hide_behind_one_partial_claim(self):
        sentence = "Your payment falls from 300 to 100 dollars."
        self.packet["spoken_script"] += "\n" + sentence
        self.packet["ladder"].append({"sentence": sentence, "adds": "Synthetic amount.", "viewer_effect": "Synthetic."})
        self.packet["claims"][0]["spoken_quote"] = "300"
        self.assertInvalid("100")

    def test_malformed_nested_types_fail_closed_without_crashing(self):
        for field in ("mode", "profile", "gates", "history", "parity", "rehearsal", "claims"):
            with self.subTest(field=field):
                self.packet = packet()
                self.packet[field] = [1, 2, 3]
                self.assertFalse(self.check()["writing_ready"])
        self.packet = packet()
        self.packet["gates"][0]["status"] = ["PASS"]
        self.assertInvalid("malformed packet")

    def test_cli_read_only_and_json_output(self):
        path = self.root / "packet.json"
        path.write_text(json.dumps(self.packet))
        before = path.read_bytes()
        run = subprocess.run([sys.executable, str(SCRIPT), "--packet", str(path), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        self.assertTrue(json.loads(run.stdout)["writing_ready"])
        self.assertEqual(path.read_bytes(), before)
        empty = self.root / "missing.md"
        empty.write_text("## Review\nNo speech.")
        run = subprocess.run([sys.executable, str(SCRIPT), "--spoken-file", str(empty)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(json.loads(run.stdout)["writing_ready"])

    def test_cli_compares_only_current_script(self):
        path = self.root / "packet.json"
        path.write_text(json.dumps(self.packet))
        spoken_file = self.root / "script.md"
        spoken_file.write_text("## Spoken script\nA different current script.\n## Superseded\n## Spoken script\n" + self.packet["spoken_script"])
        run = subprocess.run([sys.executable, str(SCRIPT), "--packet", str(path), "--root", str(self.root), "--spoken-file", str(spoken_file)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("does not match", run.stdout)


if __name__ == "__main__":
    unittest.main()
